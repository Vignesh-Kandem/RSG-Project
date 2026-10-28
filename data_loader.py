"""
Data Loader module for AI BI Assistant.
Handles CSV ingestion with data quality validation and reporting.

Business Rules:
    - Revenue = Quantity * Unit_price - Discount_amount
    - Discount_amount is treated as an absolute value (not percentage)
    - Returned transactions are loaded but flagged (is_valid=0)
    - Missing unit_price rows are loaded but flagged (is_valid=0)
    - Zero-quantity rows are loaded and flagged (revenue=0)
    - Duplicate transaction_ids are rejected (UNIQUE constraint)
    - Date format expected: DD-MM-YYYY
"""
import pandas as pd
import sqlite3
import os
import logging
from typing import Optional, Dict, Any, List, Tuple

from database import get_connection, init_db, DB_PATH

logger = logging.getLogger(__name__)

# Path to the source CSV (case-resilient for Linux / Render deployments)
def _resolve_csv_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filename = "ai_bi_assistant_sales_data - GET.csv"
    for folder in ["Input", "input"]:
        candidate = os.path.join(base_dir, folder, filename)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(base_dir, "Input", filename)

CSV_PATH = _resolve_csv_path()


def validate_row(row: pd.Series) -> Tuple[bool, str, str]:
    """
    Validate a single row and return (is_valid, quality_flag, action_taken).
    
    Returns:
        is_valid: Whether this row should be included in revenue calculations
        quality_flag: Description of the data quality issue (empty if none)
        action_taken: What was done about the issue
    """
    issues = []
    actions = []
    is_valid = True

    # Check for returned status
    if row.get("Status", "").strip().lower() == "returned":
        issues.append("Returned transaction")
        actions.append("Excluded from revenue calculations")
        is_valid = False

    # Check for missing unit price
    if pd.isna(row.get("Unit_price")):
        issues.append("Missing unit price")
        actions.append("Excluded from revenue calculations")
        is_valid = False

    # Check for zero quantity
    if row.get("Quantity", 0) == 0:
        issues.append("Zero quantity")
        actions.append("Included with zero revenue, flagged for review")

    # Check for negative quantity
    if row.get("Quantity", 0) < 0:
        issues.append("Negative quantity")
        actions.append("Excluded from revenue calculations")
        is_valid = False

    quality_flag = "; ".join(issues) if issues else None
    action_taken = "; ".join(actions) if actions else "Loaded normally"

    return is_valid, quality_flag, action_taken


def calculate_revenue(row: pd.Series, is_valid: bool) -> Optional[float]:
    """
    Calculate revenue for a transaction.
    Revenue = Quantity * Unit_price - Discount_amount
    Returns None if the row is not valid for revenue calculation.
    """
    if not is_valid:
        return None

    quantity = row.get("Quantity", 0)
    unit_price = row.get("Unit_price", 0)
    discount = row.get("Discount_amount", 0)

    if pd.isna(unit_price):
        return None

    revenue = (quantity * unit_price) - discount
    return max(revenue, 0)  # Revenue should not be negative


def load_csv_to_db(
    csv_path: Optional[str] = None,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Load CSV data into SQLite database with data quality validation.
    
    This operation is idempotent: duplicate transaction_ids are skipped,
    not duplicated.
    
    Returns:
        Dictionary with ingestion statistics and quality report.
    """
    csv_file = csv_path or CSV_PATH
    database = db_path or DB_PATH

    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"CSV file not found: {csv_file}")

    # Initialize database
    init_db(database)

    # Read CSV
    df = pd.read_csv(csv_file)
    logger.info(f"Read {len(df)} rows from {csv_file}")

    # Parse dates
    df["Order_date"] = df["Order_date"].astype(str).str.strip()

    # Track statistics
    stats = {
        "total_rows": len(df),
        "valid_rows": 0,
        "rejected_rows": 0,
        "skipped_duplicates": 0,
        "quality_issues": [],
        "quality_summary": {}
    }

    with get_connection(database) as conn:
        for idx, row in df.iterrows():
            txn_id = str(row.get("Transaction_Id", "")).strip()

            # Skip empty transaction IDs
            if not txn_id:
                stats["rejected_rows"] += 1
                stats["quality_issues"].append({
                    "transaction_id": f"Row {idx}",
                    "issue": "Missing Transaction_Id",
                    "action": "Rejected"
                })
                continue

            # Check for existing record (idempotent ingestion)
            existing = conn.execute(
                "SELECT 1 FROM sales_transactions WHERE transaction_id = ?",
                (txn_id,)
            ).fetchone()

            if existing:
                stats["skipped_duplicates"] += 1
                continue

            # Validate row
            is_valid, quality_flag, action_taken = validate_row(row)

            # Calculate revenue
            revenue = calculate_revenue(row, is_valid)

            # Parse unit_price (handle NaN)
            unit_price = row.get("Unit_price")
            if pd.isna(unit_price):
                unit_price = None

            # Insert row
            try:
                conn.execute(
                    """
                    INSERT INTO sales_transactions
                    (transaction_id, order_date, product, category, region,
                     sales_channel, quantity, unit_price, discount_amount,
                     status, revenue, is_valid, quality_flag)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        txn_id,
                        row["Order_date"],
                        str(row.get("Product", "")).strip(),
                        str(row.get("Category", "")).strip(),
                        str(row.get("Region", "")).strip(),
                        str(row.get("Sales_channel", "")).strip(),
                        int(row.get("Quantity", 0)),
                        unit_price,
                        float(row.get("Discount_amount", 0)),
                        str(row.get("Status", "")).strip(),
                        revenue,
                        1 if is_valid else 0,
                        quality_flag
                    )
                )
                stats["valid_rows"] += 1

                # Log quality issues
                if quality_flag:
                    conn.execute(
                        """
                        INSERT INTO data_quality_log
                        (transaction_id, issue_type, description, action_taken)
                        VALUES (?, ?, ?, ?)
                        """,
                        (txn_id, "DATA_QUALITY", quality_flag, action_taken)
                    )
                    stats["quality_issues"].append({
                        "transaction_id": txn_id,
                        "issue": quality_flag,
                        "action": action_taken
                    })

            except sqlite3.IntegrityError as e:
                stats["rejected_rows"] += 1
                logger.warning(f"Row {txn_id} rejected: {e}")

        # Log ingestion
        conn.execute(
            """
            INSERT INTO ingestion_log (filename, total_rows, valid_rows, rejected_rows)
            VALUES (?, ?, ?, ?)
            """,
            (
                os.path.basename(csv_file),
                stats["total_rows"],
                stats["valid_rows"],
                stats["rejected_rows"]
            )
        )

    # Build quality summary
    stats["quality_summary"] = get_quality_summary(database)

    logger.info(
        f"Ingestion complete: {stats['valid_rows']} loaded, "
        f"{stats['rejected_rows']} rejected, "
        f"{stats['skipped_duplicates']} duplicates skipped"
    )

    return stats


def get_quality_summary(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Get a summary of data quality for reporting."""
    database = db_path or DB_PATH

    with get_connection(database) as conn:
        total = conn.execute(
            "SELECT COUNT(*) as cnt FROM sales_transactions"
        ).fetchone()["cnt"]

        valid = conn.execute(
            "SELECT COUNT(*) as cnt FROM sales_transactions WHERE is_valid = 1"
        ).fetchone()["cnt"]

        invalid = conn.execute(
            "SELECT COUNT(*) as cnt FROM sales_transactions WHERE is_valid = 0"
        ).fetchone()["cnt"]

        returned = conn.execute(
            "SELECT COUNT(*) as cnt FROM sales_transactions WHERE status = 'Returned'"
        ).fetchone()["cnt"]

        missing_price = conn.execute(
            "SELECT COUNT(*) as cnt FROM sales_transactions WHERE unit_price IS NULL"
        ).fetchone()["cnt"]

        zero_qty = conn.execute(
            "SELECT COUNT(*) as cnt FROM sales_transactions WHERE quantity = 0"
        ).fetchone()["cnt"]

        discounted = conn.execute(
            "SELECT COUNT(*) as cnt FROM sales_transactions WHERE discount_amount > 0"
        ).fetchone()["cnt"]

        quality_issues = conn.execute(
            "SELECT transaction_id, issue_type, description, action_taken "
            "FROM data_quality_log ORDER BY id"
        ).fetchall()

    return {
        "total_records": total,
        "valid_for_revenue": valid,
        "excluded_from_revenue": invalid,
        "returned_transactions": returned,
        "missing_unit_price": missing_price,
        "zero_quantity_records": zero_qty,
        "discounted_transactions": discounted,
        "issues": [dict(row) for row in quality_issues]
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = load_csv_to_db()
    print(f"\n=== Ingestion Results ===")
    print(f"Total rows: {result['total_rows']}")
    print(f"Loaded: {result['valid_rows']}")
    print(f"Rejected: {result['rejected_rows']}")
    print(f"Skipped (duplicates): {result['skipped_duplicates']}")
    print(f"\nQuality Issues:")
    for issue in result["quality_issues"]:
        print(f"  {issue['transaction_id']}: {issue['issue']} -> {issue['action']}")

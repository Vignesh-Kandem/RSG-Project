"""
Analytics module for AI BI Assistant.
Contains all business logic for answering the five required questions.

All calculations use deterministic SQL queries against the SQLite database.
Revenue = Quantity * Unit_price - Discount_amount (only for valid, completed transactions).

Supported Questions:
    1. Total Revenue
    2. Highest Revenue Product
    3. Monthly Revenue Trend
    4. Highest Sales Region
    5. Month-to-Month Revenue Comparison
    
Additional Analytics:
    - Top products by quantity sold
    - Sales channel breakdown
    - Category breakdown
    - Discount analysis
"""
import re
import logging
from typing import Optional, Dict, Any, List

from database import execute_safe_query, DB_PATH

logger = logging.getLogger(__name__)


def get_total_revenue(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Q1: What is the total revenue?
    Sums revenue for all valid (completed, non-returned) transactions.
    """
    result = execute_safe_query(
        """
        SELECT 
            COALESCE(SUM(revenue), 0) as total_revenue,
            COUNT(*) as transaction_count,
            COALESCE(SUM(discount_amount), 0) as total_discount
        FROM sales_transactions
        WHERE is_valid = 1
        """,
        db_path=db_path
    )

    row = result[0] if result else {"total_revenue": 0, "transaction_count": 0, "total_discount": 0}

    # Get gross revenue for context
    gross = execute_safe_query(
        """
        SELECT COALESCE(SUM(quantity * unit_price), 0) as gross_revenue
        FROM sales_transactions
        WHERE is_valid = 1
        """,
        db_path=db_path
    )
    gross_revenue = gross[0]["gross_revenue"] if gross else 0

    return {
        "answer": f"The total revenue is ₹{row['total_revenue']:,.2f}",
        "total_revenue": row["total_revenue"],
        "gross_revenue": gross_revenue,
        "total_discount": row["total_discount"],
        "transaction_count": row["transaction_count"],
        "details": {
            "formula": "Revenue = Quantity × Unit_price − Discount_amount",
            "scope": "Only completed transactions with valid unit prices",
            "excluded": "Returned transactions and records with missing prices"
        }
    }


def get_highest_revenue_product(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Q2: Which product generated the highest revenue?
    Groups by product and sums revenue.
    """
    result = execute_safe_query(
        """
        SELECT 
            product,
            COALESCE(SUM(revenue), 0) as total_revenue,
            SUM(quantity) as total_quantity,
            COUNT(*) as transaction_count,
            COALESCE(SUM(discount_amount), 0) as total_discount
        FROM sales_transactions
        WHERE is_valid = 1
        GROUP BY product
        ORDER BY total_revenue DESC
        """,
        db_path=db_path
    )

    if not result:
        return {
            "answer": "No valid transactions found.",
            "products": [],
            "top_product": None
        }

    top = result[0]

    # Check for ties
    tied = [r for r in result if r["total_revenue"] == top["total_revenue"]]
    if len(tied) > 1:
        names = ", ".join(r["product"] for r in tied)
        answer = (
            f"There is a tie for highest revenue: {names}, "
            f"each generating ₹{top['total_revenue']:,.2f}"
        )
    else:
        answer = (
            f"'{top['product']}' generated the highest revenue of "
            f"₹{top['total_revenue']:,.2f} from {top['transaction_count']} transactions"
        )

    return {
        "answer": answer,
        "top_product": top["product"],
        "top_revenue": top["total_revenue"],
        "products": [dict(r) for r in result],
        "tied": len(tied) > 1
    }


def get_monthly_revenue_trend(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Q3: What is the monthly revenue trend?
    Groups revenue by month and calculates MoM changes.
    """
    # Parse dates as DD-MM-YYYY and extract year-month
    result = execute_safe_query(
        """
        SELECT 
            SUBSTR(order_date, 4, 2) || '-' || SUBSTR(order_date, 7, 4) as month_year,
            SUBSTR(order_date, 7, 4) || '-' || SUBSTR(order_date, 4, 2) as sort_key,
            COALESCE(SUM(revenue), 0) as monthly_revenue,
            COUNT(*) as transaction_count,
            SUM(quantity) as total_quantity
        FROM sales_transactions
        WHERE is_valid = 1
        GROUP BY sort_key
        ORDER BY sort_key ASC
        """,
        db_path=db_path
    )

    if not result:
        return {
            "answer": "No valid transactions found.",
            "monthly_data": [],
            "trend": "no_data"
        }

    # Calculate month-over-month changes
    monthly_data = []
    for i, row in enumerate(result):
        entry = dict(row)
        if i > 0:
            prev = result[i - 1]["monthly_revenue"]
            curr = row["monthly_revenue"]
            if prev > 0:
                change_pct = ((curr - prev) / prev) * 100
            else:
                change_pct = 0
            entry["mom_change"] = curr - prev
            entry["mom_change_pct"] = round(change_pct, 2)
        else:
            entry["mom_change"] = 0
            entry["mom_change_pct"] = 0
        monthly_data.append(entry)

    # Determine overall trend
    revenues = [r["monthly_revenue"] for r in result]
    if len(revenues) >= 2:
        if revenues[-1] > revenues[0]:
            trend = "upward"
        elif revenues[-1] < revenues[0]:
            trend = "downward"
        else:
            trend = "flat"
    else:
        trend = "insufficient_data"

    # Format month names for display
    month_names = {
        "01": "January", "02": "February", "03": "March",
        "04": "April", "05": "May", "06": "June",
        "07": "July", "08": "August", "09": "September",
        "10": "October", "11": "November", "12": "December"
    }

    summary_parts = []
    for entry in monthly_data:
        month_num = entry["sort_key"].split("-")[1]
        month_name = month_names.get(month_num, month_num)
        summary_parts.append(
            f"{month_name} 2026: ₹{entry['monthly_revenue']:,.2f}"
        )

    answer = (
        f"Monthly revenue trend ({trend} overall):\n" +
        "\n".join(f"  • {s}" for s in summary_parts)
    )

    return {
        "answer": answer,
        "monthly_data": monthly_data,
        "trend": trend,
        "month_names": month_names
    }


def get_highest_sales_region(db_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Q4: Which region generated the highest sales?
    Groups by region and sums revenue.
    """
    result = execute_safe_query(
        """
        SELECT 
            region,
            COALESCE(SUM(revenue), 0) as total_revenue,
            SUM(quantity) as total_quantity,
            COUNT(*) as transaction_count,
            COALESCE(SUM(discount_amount), 0) as total_discount
        FROM sales_transactions
        WHERE is_valid = 1
        GROUP BY region
        ORDER BY total_revenue DESC
        """,
        db_path=db_path
    )

    if not result:
        return {
            "answer": "No valid transactions found.",
            "regions": [],
            "top_region": None
        }

    top = result[0]

    # Check for ties
    tied = [r for r in result if r["total_revenue"] == top["total_revenue"]]
    if len(tied) > 1:
        names = ", ".join(r["region"] for r in tied)
        answer = (
            f"There is a tie for highest sales region: {names}, "
            f"each generating ₹{top['total_revenue']:,.2f}"
        )
    else:
        answer = (
            f"The '{top['region']}' region generated the highest sales of "
            f"₹{top['total_revenue']:,.2f} from {top['transaction_count']} transactions "
            f"({top['total_quantity']} units sold)"
        )

    return {
        "answer": answer,
        "top_region": top["region"],
        "top_revenue": top["total_revenue"],
        "regions": [dict(r) for r in result],
        "tied": len(tied) > 1
    }


def get_revenue_comparison(
    month1: str,
    month2: str,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Q5: How did revenue change between two months?
    Compares revenue between two specified months.
    
    Args:
        month1: First month in MM format (e.g., '01' for January)
        month2: Second month in MM format (e.g., '02' for February)
    """
    month_names = {
        "01": "January", "02": "February", "03": "March",
        "04": "April", "05": "May", "06": "June",
        "07": "July", "08": "August", "09": "September",
        "10": "October", "11": "November", "12": "December"
    }

    # Validate months
    if month1 not in month_names or month2 not in month_names:
        return {
            "answer": f"Invalid month specified. Please use values 01-12.",
            "error": True
        }

    result = execute_safe_query(
        """
        SELECT 
            SUBSTR(order_date, 4, 2) as month_num,
            COALESCE(SUM(revenue), 0) as total_revenue,
            COUNT(*) as transaction_count,
            SUM(quantity) as total_quantity
        FROM sales_transactions
        WHERE is_valid = 1 
          AND SUBSTR(order_date, 4, 2) IN (?, ?)
        GROUP BY month_num
        ORDER BY month_num
        """,
        (month1, month2),
        db_path=db_path
    )

    # Build a lookup
    month_data = {r["month_num"]: dict(r) for r in result}

    rev1 = month_data.get(month1, {}).get("total_revenue", 0)
    rev2 = month_data.get(month2, {}).get("total_revenue", 0)

    name1 = month_names[month1]
    name2 = month_names[month2]

    if month1 not in month_data:
        return {
            "answer": f"No data available for {name1}.",
            "month1": {"name": name1, "revenue": 0},
            "month2": {"name": name2, "revenue": rev2},
            "error": False,
            "no_data_month": month1
        }

    if month2 not in month_data:
        return {
            "answer": f"No data available for {name2}.",
            "month1": {"name": name1, "revenue": rev1},
            "month2": {"name": name2, "revenue": 0},
            "error": False,
            "no_data_month": month2
        }

    change = rev2 - rev1
    if rev1 > 0:
        change_pct = ((rev2 - rev1) / rev1) * 100
    else:
        change_pct = 0

    if change > 0:
        direction = "increased"
    elif change < 0:
        direction = "decreased"
    else:
        direction = "remained the same"

    answer = (
        f"Revenue {direction} from {name1} (₹{rev1:,.2f}) "
        f"to {name2} (₹{rev2:,.2f}). "
        f"Change: ₹{change:,.2f} ({change_pct:+.2f}%)"
    )

    return {
        "answer": answer,
        "month1": {
            "name": name1,
            "revenue": rev1,
            "transactions": month_data.get(month1, {}).get("transaction_count", 0),
            "quantity": month_data.get(month1, {}).get("total_quantity", 0)
        },
        "month2": {
            "name": name2,
            "revenue": rev2,
            "transactions": month_data.get(month2, {}).get("transaction_count", 0),
            "quantity": month_data.get(month2, {}).get("total_quantity", 0)
        },
        "change": change,
        "change_pct": round(change_pct, 2),
        "direction": direction,
        "error": False
    }


# ─── Additional Analytics ───────────────────────────────────────────────

def get_category_breakdown(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Revenue breakdown by product category."""
    result = execute_safe_query(
        """
        SELECT 
            category,
            COALESCE(SUM(revenue), 0) as total_revenue,
            SUM(quantity) as total_quantity,
            COUNT(*) as transaction_count
        FROM sales_transactions
        WHERE is_valid = 1
        GROUP BY category
        ORDER BY total_revenue DESC
        """,
        db_path=db_path
    )
    return {
        "answer": "Revenue breakdown by category",
        "categories": [dict(r) for r in result]
    }


def get_sales_channel_breakdown(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Revenue breakdown by sales channel (Online vs Retail)."""
    result = execute_safe_query(
        """
        SELECT 
            sales_channel,
            COALESCE(SUM(revenue), 0) as total_revenue,
            SUM(quantity) as total_quantity,
            COUNT(*) as transaction_count
        FROM sales_transactions
        WHERE is_valid = 1
        GROUP BY sales_channel
        ORDER BY total_revenue DESC
        """,
        db_path=db_path
    )
    return {
        "answer": "Revenue breakdown by sales channel",
        "channels": [dict(r) for r in result]
    }


def get_top_transactions(
    limit: int = 10,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Get top transactions by revenue."""
    result = execute_safe_query(
        """
        SELECT 
            transaction_id, order_date, product, category,
            region, sales_channel, quantity, unit_price,
            discount_amount, revenue
        FROM sales_transactions
        WHERE is_valid = 1
        ORDER BY revenue DESC
        LIMIT ?
        """,
        (limit,),
        db_path=db_path
    )
    return {
        "answer": f"Top {limit} transactions by revenue",
        "transactions": [dict(r) for r in result]
    }


def get_discount_analysis(db_path: Optional[str] = None) -> Dict[str, Any]:
    """Analysis of discounted transactions."""
    result = execute_safe_query(
        """
        SELECT 
            transaction_id, order_date, product, quantity,
            unit_price, discount_amount, revenue,
            ROUND(discount_amount * 100.0 / (quantity * unit_price), 2) as discount_pct
        FROM sales_transactions
        WHERE is_valid = 1 AND discount_amount > 0
        ORDER BY discount_amount DESC
        """,
        db_path=db_path
    )
    
    total_discount = sum(r["discount_amount"] for r in result)
    
    return {
        "answer": f"Found {len(result)} discounted transactions totaling ₹{total_discount:,.2f}",
        "discounted_transactions": [dict(r) for r in result],
        "total_discount": total_discount,
        "count": len(result)
    }


def get_all_transactions(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all transactions for evidence display."""
    result = execute_safe_query(
        """
        SELECT 
            transaction_id, order_date, product, category,
            region, sales_channel, quantity, unit_price,
            discount_amount, status, revenue, is_valid, quality_flag
        FROM sales_transactions
        ORDER BY order_date
        """,
        db_path=db_path
    )
    return [dict(r) for r in result]

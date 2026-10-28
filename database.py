"""
Database module for AI BI Assistant.
Manages SQLite database creation, schema, and safe query execution.
"""
import sqlite3
import os
import logging
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sales.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sales_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT UNIQUE NOT NULL,
    order_date TEXT NOT NULL,
    product TEXT NOT NULL,
    category TEXT NOT NULL,
    region TEXT NOT NULL,
    sales_channel TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL,
    discount_amount REAL NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    revenue REAL,
    is_valid INTEGER NOT NULL DEFAULT 1,
    quality_flag TEXT DEFAULT NULL
);

CREATE TABLE IF NOT EXISTS data_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    description TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ingestion_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    total_rows INTEGER NOT NULL,
    valid_rows INTEGER NOT NULL,
    rejected_rows INTEGER NOT NULL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


@contextmanager
def get_connection(db_path: Optional[str] = None):
    """Context manager for database connections."""
    path = db_path or DB_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Optional[str] = None) -> None:
    """Initialize database with schema."""
    with get_connection(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
        logger.info("Database initialized successfully.")


def execute_safe_query(
    query: str,
    params: Optional[Tuple] = None,
    db_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Execute a read-only parameterized query safely.
    Rejects any query containing write operations.
    """
    # Security: Only allow SELECT statements
    normalized = query.strip().upper()
    forbidden_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
        "TRUNCATE", "REPLACE", "EXEC", "EXECUTE", "GRANT", "REVOKE",
        "ATTACH", "DETACH", "PRAGMA", "VACUUM"
    ]

    for keyword in forbidden_keywords:
        # Check for keyword as a word boundary (not part of column names)
        if keyword in normalized.split():
            raise ValueError(
                f"Query contains forbidden keyword '{keyword}'. "
                "Only SELECT queries are allowed."
            )

    if not normalized.startswith("SELECT"):
        raise ValueError("Only SELECT queries are allowed.")

    with get_connection(db_path) as conn:
        cursor = conn.execute(query, params or ())
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]


def get_table_info(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get schema information for documentation."""
    query = "SELECT name, type, sql FROM sqlite_master WHERE type='table'"
    return execute_safe_query(query, db_path=db_path)


def get_row_count(db_path: Optional[str] = None) -> int:
    """Get total row count in sales_transactions."""
    result = execute_safe_query(
        "SELECT COUNT(*) as cnt FROM sales_transactions",
        db_path=db_path
    )
    return result[0]["cnt"] if result else 0

"""
Shared test fixtures for AI BI Assistant.
Provides isolated test database and sample data for all test modules.
"""
import os
import sys
import pytest
import tempfile
import sqlite3

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_db, get_connection


@pytest.fixture
def test_db(tmp_path):
    """Create an isolated temporary database for testing."""
    db_path = str(tmp_path / "test_sales.db")
    init_db(db_path)
    return db_path


@pytest.fixture
def populated_db(test_db):
    """Create a test database populated with known sample data."""
    with get_connection(test_db) as conn:
        # Insert known test data matching the real CSV structure
        test_rows = [
            # Normal completed transactions
            ("TXN_T001", "03-01-2026", "Laptop Stand", "Accessories", "North",
             "Online", 10, 1200, 0, "Completed", 12000, 1, None),
            ("TXN_T002", "05-01-2026", "Wireless Mouse", "Accessories", "South",
             "Retail", 25, 650, 0, "Completed", 16250, 1, None),
            ("TXN_T003", "08-01-2026", "Office Chair", "Furniture", "West",
             "Online", 4, 7800, 0, "Completed", 31200, 1, None),
            # Discounted transaction
            ("TXN_T004", "12-01-2026", "Monitor", "Electronics", "East",
             "Retail", 6, 9500, 500, "Completed", 56500, 1, None),
            # February transactions
            ("TXN_T005", "02-02-2026", "Laptop Stand", "Accessories", "East",
             "Retail", 14, 1200, 0, "Completed", 16800, 1, None),
            ("TXN_T006", "07-02-2026", "Desk", "Furniture", "South",
             "Online", 5, 12500, 0, "Completed", 62500, 1, None),
            # March transaction  
            ("TXN_T007", "15-03-2026", "Monitor", "Electronics", "North",
             "Online", 3, 9500, 0, "Completed", 28500, 1, None),
            # Returned transaction (is_valid = 0)
            ("TXN_T008", "26-04-2026", "Monitor", "Electronics", "West",
             "Retail", 2, 9500, 0, "Returned", None, 0, "Returned transaction"),
            # Zero quantity (valid but zero revenue)
            ("TXN_T009", "28-04-2026", "Keyboard", "Accessories", "East",
             "Online", 0, 900, 0, "Completed", 0, 1, "Zero quantity"),
            # Missing unit price (is_valid = 0)
            ("TXN_T010", "28-06-2026", "Laptop Stand", "Accessories", "East",
             "Online", 5, None, 0, "Completed", None, 0, "Missing unit price"),
        ]

        conn.executemany(
            """
            INSERT INTO sales_transactions
            (transaction_id, order_date, product, category, region,
             sales_channel, quantity, unit_price, discount_amount,
             status, revenue, is_valid, quality_flag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            test_rows
        )

    return test_db


@pytest.fixture
def empty_db(test_db):
    """Return an empty initialized database."""
    return test_db


@pytest.fixture
def csv_path():
    """Return path to the real CSV file."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "input",
        "ai_bi_assistant_sales_data - GET.csv"
    )
    return path


@pytest.fixture
def sample_csv(tmp_path):
    """Create a sample CSV for testing data loading."""
    csv_content = """Transaction_Id,Order_date,Product,Category,Region,Sales_channel,Quantity,Unit_price,Discount_amount,Status
TXN_S001,03-01-2026,Laptop Stand,Accessories,North,Online,10,1200,0,Completed
TXN_S002,05-01-2026,Wireless Mouse,Accessories,South,Retail,25,650,0,Completed
TXN_S003,08-01-2026,Monitor,Electronics,West,Online,0,9500,0,Completed
TXN_S004,12-01-2026,Monitor,Electronics,East,Retail,6,9500,500,Completed
TXN_S005,26-04-2026,Monitor,Electronics,West,Retail,2,9500,0,Returned
TXN_S006,28-06-2026,Laptop Stand,Accessories,East,Online,5,,0,Completed
"""
    csv_file = tmp_path / "test_sales.csv"
    csv_file.write_text(csv_content)
    return str(csv_file)

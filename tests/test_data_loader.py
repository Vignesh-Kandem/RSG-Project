"""
Tests for the data loader module.
Tests CSV ingestion, validation, and idempotency.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import load_csv_to_db, get_quality_summary, validate_row, calculate_revenue
from database import get_connection, init_db, execute_safe_query
import pandas as pd


class TestDataValidation:
    """Tests for row-level validation logic."""

    def test_valid_completed_row(self):
        """Normal completed row should be valid."""
        row = pd.Series({
            "Status": "Completed",
            "Unit_price": 1200,
            "Quantity": 10
        })
        is_valid, flag, action = validate_row(row)
        assert is_valid is True
        assert flag is None

    def test_returned_row_invalid(self):
        """Returned row should be flagged as invalid."""
        row = pd.Series({
            "Status": "Returned",
            "Unit_price": 9500,
            "Quantity": 2
        })
        is_valid, flag, action = validate_row(row)
        assert is_valid is False
        assert "Returned" in flag

    def test_missing_price_invalid(self):
        """Missing unit_price row should be flagged as invalid."""
        row = pd.Series({
            "Status": "Completed",
            "Unit_price": float("nan"),
            "Quantity": 5
        })
        is_valid, flag, action = validate_row(row)
        assert is_valid is False
        assert "Missing" in flag

    def test_zero_quantity_valid_with_flag(self):
        """Zero quantity should be valid but flagged."""
        row = pd.Series({
            "Status": "Completed",
            "Unit_price": 900,
            "Quantity": 0
        })
        is_valid, flag, action = validate_row(row)
        assert is_valid is True  # Still valid, just zero revenue
        assert "Zero quantity" in flag

    def test_negative_quantity_invalid(self):
        """Negative quantity should be flagged as invalid."""
        row = pd.Series({
            "Status": "Completed",
            "Unit_price": 900,
            "Quantity": -3
        })
        is_valid, flag, action = validate_row(row)
        assert is_valid is False
        assert "Negative" in flag


class TestRevenueCalculation:
    """Tests for revenue calculation logic."""

    def test_normal_revenue(self):
        """Normal revenue = Qty * Price - Discount."""
        row = pd.Series({"Quantity": 10, "Unit_price": 1200, "Discount_amount": 0})
        assert calculate_revenue(row, True) == 12000.0

    def test_revenue_with_discount(self):
        """Discount should be subtracted from gross revenue."""
        row = pd.Series({"Quantity": 6, "Unit_price": 9500, "Discount_amount": 500})
        assert calculate_revenue(row, True) == 56500.0

    def test_zero_quantity_revenue(self):
        """Zero quantity should result in zero revenue."""
        row = pd.Series({"Quantity": 0, "Unit_price": 900, "Discount_amount": 0})
        assert calculate_revenue(row, True) == 0.0

    def test_invalid_row_no_revenue(self):
        """Invalid rows should return None for revenue."""
        row = pd.Series({"Quantity": 2, "Unit_price": 9500, "Discount_amount": 0})
        assert calculate_revenue(row, False) is None

    def test_missing_price_no_revenue(self):
        """Missing price should return None even if valid flag is True."""
        row = pd.Series({"Quantity": 5, "Unit_price": float("nan"), "Discount_amount": 0})
        assert calculate_revenue(row, True) is None


class TestCSVIngestion:
    """Tests for CSV loading into database."""

    def test_load_sample_csv(self, test_db, sample_csv):
        """Loading a sample CSV should succeed."""
        result = load_csv_to_db(sample_csv, test_db)
        assert result["total_rows"] == 6
        assert result["valid_rows"] == 6  # All rows loaded (some with is_valid=0)

    def test_idempotent_loading(self, test_db, sample_csv):
        """Loading the same CSV twice should not duplicate records."""
        result1 = load_csv_to_db(sample_csv, test_db)
        result2 = load_csv_to_db(sample_csv, test_db)

        assert result2["skipped_duplicates"] == 6  # All should be skipped
        assert result2["valid_rows"] == 0  # None newly loaded

        # Verify total count in DB
        rows = execute_safe_query(
            "SELECT COUNT(*) as cnt FROM sales_transactions",
            db_path=test_db
        )
        assert rows[0]["cnt"] == 6

    def test_quality_issues_logged(self, test_db, sample_csv):
        """Quality issues should be recorded in the log."""
        load_csv_to_db(sample_csv, test_db)

        # Check quality log
        issues = execute_safe_query(
            "SELECT * FROM data_quality_log",
            db_path=test_db
        )
        # Should log: zero qty (TXN_S003), returned (TXN_S005), missing price (TXN_S006)
        assert len(issues) >= 3

    def test_returned_excluded_from_revenue(self, test_db, sample_csv):
        """Returned transactions should have is_valid=0."""
        load_csv_to_db(sample_csv, test_db)

        returned = execute_safe_query(
            "SELECT * FROM sales_transactions WHERE status = 'Returned'",
            db_path=test_db
        )
        assert len(returned) == 1
        assert returned[0]["is_valid"] == 0

    def test_missing_price_excluded(self, test_db, sample_csv):
        """Missing price transactions should have is_valid=0."""
        load_csv_to_db(sample_csv, test_db)

        missing = execute_safe_query(
            "SELECT * FROM sales_transactions WHERE unit_price IS NULL",
            db_path=test_db
        )
        assert len(missing) == 1
        assert missing[0]["is_valid"] == 0

    def test_nonexistent_csv_raises_error(self, test_db):
        """Loading a nonexistent CSV should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_csv_to_db("nonexistent.csv", test_db)

    def test_real_csv_loads_correctly(self, test_db, csv_path):
        """Real CSV from input/ should load successfully."""
        if not os.path.exists(csv_path):
            pytest.skip("Real CSV not available")

        result = load_csv_to_db(csv_path, test_db)
        assert result["total_rows"] == 51
        assert result["valid_rows"] == 51  # All rows loaded (some flagged)

        # Verify quality issues
        assert len(result["quality_issues"]) >= 2  # At least returned + missing price


class TestQualitySummary:
    """Tests for data quality summary."""

    def test_quality_summary_after_load(self, test_db, sample_csv):
        """Quality summary should reflect loaded data."""
        load_csv_to_db(sample_csv, test_db)
        summary = get_quality_summary(test_db)

        assert summary["total_records"] == 6
        assert summary["returned_transactions"] == 1
        assert summary["missing_unit_price"] == 1
        assert summary["zero_quantity_records"] == 1

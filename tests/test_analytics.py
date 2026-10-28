"""
Tests for the analytics module.
Tests all 5 required business questions plus edge cases.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analytics import (
    get_total_revenue,
    get_highest_revenue_product,
    get_monthly_revenue_trend,
    get_highest_sales_region,
    get_revenue_comparison,
    get_category_breakdown,
    get_sales_channel_breakdown,
    get_discount_analysis,
)


class TestTotalRevenue:
    """Tests for Q1: What is the total revenue?"""

    def test_total_revenue_correct_value(self, populated_db):
        """Revenue should sum correctly from known test data."""
        result = get_total_revenue(populated_db)
        # Expected: 12000 + 16250 + 31200 + 56500 + 16800 + 62500 + 28500 + 0 = 223750
        # (TXN_T008 Returned is_valid=0, TXN_T010 missing price is_valid=0)
        assert result["total_revenue"] == 223750.0

    def test_total_revenue_excludes_returned(self, populated_db):
        """Returned transactions should not be counted in revenue."""
        result = get_total_revenue(populated_db)
        # TXN_T008 is returned, should not contribute
        assert result["total_revenue"] == 223750.0

    def test_total_revenue_excludes_missing_price(self, populated_db):
        """Transactions with missing unit_price should be excluded."""
        result = get_total_revenue(populated_db)
        # TXN_T010 has no price, should not contribute
        assert result["total_revenue"] == 223750.0

    def test_total_revenue_includes_zero_quantity(self, populated_db):
        """Zero-quantity transactions contribute 0 to revenue."""
        result = get_total_revenue(populated_db)
        # TXN_T009 has qty=0, contributes 0 revenue
        # Total should still include this transaction in the count
        assert result["transaction_count"] == 8  # 8 valid rows

    def test_total_revenue_accounts_for_discount(self, populated_db):
        """Discounts should be subtracted from revenue."""
        result = get_total_revenue(populated_db)
        assert result["total_discount"] == 500.0  # TXN_T004 has 500 discount

    def test_total_revenue_empty_db(self, empty_db):
        """Empty database should return zero revenue."""
        result = get_total_revenue(empty_db)
        assert result["total_revenue"] == 0
        assert result["transaction_count"] == 0

    def test_total_revenue_has_answer_string(self, populated_db):
        """Result should include a formatted answer string."""
        result = get_total_revenue(populated_db)
        assert "answer" in result
        assert "223,750.00" in result["answer"]


class TestHighestRevenueProduct:
    """Tests for Q2: Which product generated the highest revenue?"""

    def test_highest_product(self, populated_db):
        """Should correctly identify the highest revenue product."""
        result = get_highest_revenue_product(populated_db)
        # Desk: 62500, Monitor: 56500+28500=85000 (only valid ones)
        # Wait: TXN_T004 Monitor 56500 + TXN_T007 Monitor 28500 = 85000
        assert result["top_product"] == "Monitor"
        assert result["top_revenue"] == 85000.0

    def test_all_products_present(self, populated_db):
        """All products with valid transactions should appear."""
        result = get_highest_revenue_product(populated_db)
        product_names = [p["product"] for p in result["products"]]
        assert "Laptop Stand" in product_names
        assert "Monitor" in product_names
        assert "Desk" in product_names

    def test_empty_db_no_products(self, empty_db):
        """Empty database should return no top product."""
        result = get_highest_revenue_product(empty_db)
        assert result["top_product"] is None

    def test_includes_all_product_stats(self, populated_db):
        """Each product should have revenue, quantity, and transaction count."""
        result = get_highest_revenue_product(populated_db)
        for product in result["products"]:
            assert "total_revenue" in product
            assert "total_quantity" in product
            assert "transaction_count" in product


class TestMonthlyRevenueTrend:
    """Tests for Q3: What is the monthly revenue trend?"""

    def test_correct_month_count(self, populated_db):
        """Should have data for the months represented in test data."""
        result = get_monthly_revenue_trend(populated_db)
        # Jan, Feb, Mar have data (April has only returned/zero-qty transactions)
        monthly_data = result["monthly_data"]
        assert len(monthly_data) >= 3

    def test_january_revenue(self, populated_db):
        """January revenue should be correct."""
        result = get_monthly_revenue_trend(populated_db)
        jan = [m for m in result["monthly_data"] if "01" in m["sort_key"]]
        if jan:
            # TXN_T001: 12000 + TXN_T002: 16250 + TXN_T003: 31200 + TXN_T004: 56500 = 115950
            assert jan[0]["monthly_revenue"] == 115950.0

    def test_mom_change_calculated(self, populated_db):
        """Month-over-month change should be calculated."""
        result = get_monthly_revenue_trend(populated_db)
        monthly_data = result["monthly_data"]
        if len(monthly_data) >= 2:
            assert "mom_change" in monthly_data[1]
            assert "mom_change_pct" in monthly_data[1]

    def test_trend_direction(self, populated_db):
        """Overall trend should be determined."""
        result = get_monthly_revenue_trend(populated_db)
        assert result["trend"] in ["upward", "downward", "flat", "insufficient_data"]

    def test_empty_db_no_trend(self, empty_db):
        """Empty database should return no data."""
        result = get_monthly_revenue_trend(empty_db)
        assert result["monthly_data"] == []


class TestHighestSalesRegion:
    """Tests for Q4: Which region generated the highest sales?"""

    def test_correct_top_region(self, populated_db):
        """Should identify the region with the highest revenue."""
        result = get_highest_sales_region(populated_db)
        # South: 16250 + 62500 = 78750
        # East: 56500 + 16800 + 0 = 73300
        # North: 12000 + 28500 = 40500
        # West: 31200
        assert result["top_region"] == "South"
        assert result["top_revenue"] == 78750.0

    def test_all_regions_present(self, populated_db):
        """All regions should be reported."""
        result = get_highest_sales_region(populated_db)
        regions = [r["region"] for r in result["regions"]]
        assert set(regions) == {"North", "South", "East", "West"}

    def test_empty_db(self, empty_db):
        """Empty database returns no top region."""
        result = get_highest_sales_region(empty_db)
        assert result["top_region"] is None


class TestRevenueComparison:
    """Tests for Q5: How did revenue change between two months?"""

    def test_jan_feb_comparison(self, populated_db):
        """Should correctly compare January and February revenue."""
        result = get_revenue_comparison("01", "02", populated_db)
        # Jan: 115950, Feb: 79300
        assert result["month1"]["name"] == "January"
        assert result["month2"]["name"] == "February"
        assert result["month1"]["revenue"] == 115950.0
        assert result["month2"]["revenue"] == 79300.0
        assert result["direction"] == "decreased"
        assert result["change"] == 79300.0 - 115950.0

    def test_change_percentage(self, populated_db):
        """Change percentage should be calculated correctly."""
        result = get_revenue_comparison("01", "02", populated_db)
        expected_pct = ((79300.0 - 115950.0) / 115950.0) * 100
        assert abs(result["change_pct"] - round(expected_pct, 2)) < 0.1

    def test_month_with_no_data(self, populated_db):
        """Comparison with a month that has no data should be handled."""
        result = get_revenue_comparison("01", "12", populated_db)
        # December has no data
        assert "no data" in result["answer"].lower() or result["month2"]["revenue"] == 0

    def test_invalid_month(self, populated_db):
        """Invalid month should return an error."""
        result = get_revenue_comparison("13", "01", populated_db)
        assert result.get("error") is True

    def test_same_month_comparison(self, populated_db):
        """Comparing a month with itself should show no change."""
        result = get_revenue_comparison("01", "01", populated_db)
        assert result["change"] == 0
        assert result["direction"] == "remained the same"


class TestCategoryBreakdown:
    """Tests for category analysis."""

    def test_categories_present(self, populated_db):
        """All categories should appear."""
        result = get_category_breakdown(populated_db)
        categories = [c["category"] for c in result["categories"]]
        assert "Accessories" in categories
        assert "Furniture" in categories
        assert "Electronics" in categories


class TestDiscountAnalysis:
    """Tests for discount analysis."""

    def test_discounted_transactions(self, populated_db):
        """Should find the discounted transactions."""
        result = get_discount_analysis(populated_db)
        assert result["count"] == 1  # Only TXN_T004 has a discount
        assert result["total_discount"] == 500.0

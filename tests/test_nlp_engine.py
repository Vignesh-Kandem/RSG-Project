"""
Tests for the NLP engine module.
Tests question classification, month extraction, and routing.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nlp_engine import (
    classify_question,
    extract_months,
    process_question,
    normalize_text,
    get_supported_questions,
)


class TestNormalizeText:
    """Tests for text normalization."""

    def test_lowercase(self):
        assert normalize_text("HELLO WORLD") == "hello world"

    def test_strip_whitespace(self):
        assert normalize_text("  hello  ") == "hello"

    def test_remove_punctuation(self):
        result = normalize_text("What is the total revenue?")
        assert "?" not in result

    def test_collapse_whitespace(self):
        assert normalize_text("hello   world") == "hello world"


class TestExtractMonths:
    """Tests for month extraction from user questions."""

    def test_extract_two_months(self):
        months = extract_months("Compare January and February")
        assert "01" in months
        assert "02" in months

    def test_extract_abbreviated_months(self):
        months = extract_months("Compare Jan and Mar")
        assert "01" in months
        assert "03" in months

    def test_no_months(self):
        months = extract_months("What is the total revenue?")
        assert len(months) == 0

    def test_single_month(self):
        months = extract_months("Revenue for April")
        assert months == ["04"]

    def test_month_case_insensitive(self):
        months = extract_months("JANUARY to JUNE")
        assert "01" in months
        assert "06" in months


class TestClassifyQuestion:
    """Tests for question classification."""

    def test_total_revenue(self):
        qtype, confidence = classify_question("What is the total revenue?")
        assert qtype == "total_revenue"
        assert confidence > 0

    def test_highest_product(self):
        qtype, _ = classify_question("Which product generated the highest revenue?")
        assert qtype == "highest_revenue_product"

    def test_monthly_trend(self):
        qtype, _ = classify_question("What is the monthly revenue trend?")
        assert qtype == "monthly_trend"

    def test_highest_region(self):
        qtype, _ = classify_question("Which region generated the highest sales?")
        assert qtype == "highest_sales_region"

    def test_revenue_comparison(self):
        qtype, _ = classify_question(
            "How did revenue change between January and February?"
        )
        assert qtype == "revenue_comparison"

    def test_unknown_question(self):
        qtype, confidence = classify_question("What is the meaning of life?")
        assert qtype == "unknown"

    def test_empty_question_classified(self):
        """Empty question should be classified as unknown."""
        qtype, confidence = classify_question("")
        assert qtype == "unknown"

    def test_category_question(self):
        qtype, _ = classify_question("Show revenue by category")
        assert qtype == "category_breakdown"

    def test_discount_question(self):
        qtype, _ = classify_question("Show discount analysis")
        assert qtype == "discount_analysis"

    def test_channel_question(self):
        qtype, _ = classify_question("Compare online vs retail sales")
        assert qtype == "sales_channel"


class TestProcessQuestion:
    """Tests for end-to-end question processing."""

    def test_valid_question_returns_answer(self, populated_db):
        """A valid question should return a structured answer."""
        result = process_question("What is the total revenue?", populated_db)
        assert "answer" in result
        assert result["question_type"] == "total_revenue"
        assert result["error"] is False

    def test_unknown_question_returns_error(self, populated_db):
        """An unknown question should return an error with suggestions."""
        result = process_question("What is the meaning of life?", populated_db)
        assert result["error"] is True
        assert result["question_type"] == "unknown"

    def test_empty_question(self, populated_db):
        """Empty question should return an error."""
        result = process_question("", populated_db)
        assert result["error"] is True
        assert result["question_type"] == "invalid"

    def test_none_question(self, populated_db):
        """None question should return an error."""
        result = process_question(None, populated_db)
        assert result["error"] is True

    def test_comparison_with_months(self, populated_db):
        """Comparison question with months should extract and use them."""
        result = process_question(
            "How did revenue change between January and February?",
            populated_db
        )
        assert result["question_type"] == "revenue_comparison"
        assert result["error"] is False

    def test_all_five_questions_work(self, populated_db):
        """All 5 required questions should produce valid answers."""
        questions = [
            "What is the total revenue?",
            "Which product generated the highest revenue?",
            "What is the monthly revenue trend?",
            "Which region generated the highest sales?",
            "How did revenue change between January and February?",
        ]
        for q in questions:
            result = process_question(q, populated_db)
            assert result["error"] is False, f"Question failed: {q}"
            assert "answer" in result, f"No answer for: {q}"


class TestSupportedQuestions:
    """Tests for supported questions listing."""

    def test_supported_questions_list(self):
        """Should return a non-empty list of supported types."""
        supported = get_supported_questions()
        assert len(supported) >= 5  # At least 5 question types
        for sq in supported:
            assert "type" in sq
            assert "description" in sq
            assert "examples" in sq
            assert len(sq["examples"]) > 0

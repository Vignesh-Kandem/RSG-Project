"""
Tests for the FastAPI backend endpoints.
Tests /health, /ask, /data-quality, /supported, /transactions.
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from database import init_db, get_connection
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Create a test client with an isolated database."""
    test_db = str(tmp_path / "test_api.db")
    
    # Monkeypatch DB_PATH in all modules
    import database
    import data_loader
    import analytics
    import nlp_engine
    
    monkeypatch.setattr(database, "DB_PATH", test_db)
    monkeypatch.setattr(data_loader, "DB_PATH", test_db)
    
    # Initialize and populate test database
    init_db(test_db)
    
    with get_connection(test_db) as conn:
        test_rows = [
            ("TXN_A001", "03-01-2026", "Laptop Stand", "Accessories", "North",
             "Online", 10, 1200, 0, "Completed", 12000, 1, None),
            ("TXN_A002", "05-01-2026", "Monitor", "Electronics", "South",
             "Retail", 6, 9500, 500, "Completed", 56500, 1, None),
            ("TXN_A003", "02-02-2026", "Desk", "Furniture", "West",
             "Online", 3, 12500, 0, "Completed", 37500, 1, None),
            ("TXN_A004", "26-04-2026", "Monitor", "Electronics", "West",
             "Retail", 2, 9500, 0, "Returned", None, 0, "Returned transaction"),
        ]
        conn.executemany(
            """INSERT INTO sales_transactions
            (transaction_id, order_date, product, category, region,
             sales_channel, quantity, unit_price, discount_amount,
             status, revenue, is_valid, quality_flag)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            test_rows
        )

    return TestClient(app)


class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client):
        response = client.get("/health")
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "record_count" in data
        assert "version" in data

    def test_health_shows_records(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["record_count"] > 0


class TestAskEndpoint:
    """Tests for POST /ask."""

    def test_valid_question(self, client):
        response = client.post("/ask", json={"question": "What is the total revenue?"})
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "question_type" in data
        assert data["error"] is False

    def test_product_question(self, client):
        response = client.post(
            "/ask",
            json={"question": "Which product generated the highest revenue?"}
        )
        assert response.status_code == 200
        assert response.json()["error"] is False

    def test_monthly_trend_question(self, client):
        response = client.post(
            "/ask",
            json={"question": "What is the monthly revenue trend?"}
        )
        assert response.status_code == 200
        assert response.json()["error"] is False

    def test_region_question(self, client):
        response = client.post(
            "/ask",
            json={"question": "Which region generated the highest sales?"}
        )
        assert response.status_code == 200
        assert response.json()["error"] is False

    def test_comparison_question(self, client):
        response = client.post(
            "/ask",
            json={"question": "How did revenue change between January and February?"}
        )
        assert response.status_code == 200
        assert response.json()["error"] is False

    def test_unsupported_question(self, client):
        response = client.post(
            "/ask",
            json={"question": "What is the meaning of life?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["error"] is True
        assert data["question_type"] == "unknown"

    def test_empty_question_validation(self, client):
        response = client.post("/ask", json={"question": ""})
        assert response.status_code == 422  # Validation error

    def test_missing_question_field(self, client):
        response = client.post("/ask", json={})
        assert response.status_code == 422

    def test_too_short_question(self, client):
        response = client.post("/ask", json={"question": "hi"})
        assert response.status_code == 422


class TestDataQualityEndpoint:
    """Tests for GET /data-quality."""

    def test_quality_returns_200(self, client):
        response = client.get("/data-quality")
        assert response.status_code == 200

    def test_quality_response_structure(self, client):
        response = client.get("/data-quality")
        data = response.json()
        assert "total_records" in data
        assert "valid_for_revenue" in data
        assert "excluded_from_revenue" in data


class TestSupportedEndpoint:
    """Tests for GET /supported."""

    def test_supported_returns_200(self, client):
        response = client.get("/supported")
        assert response.status_code == 200

    def test_supported_has_questions(self, client):
        response = client.get("/supported")
        data = response.json()
        assert "supported_questions" in data
        assert len(data["supported_questions"]) >= 5


class TestTransactionsEndpoint:
    """Tests for GET /transactions."""

    def test_transactions_returns_200(self, client):
        response = client.get("/transactions")
        assert response.status_code == 200

    def test_transactions_has_data(self, client):
        response = client.get("/transactions")
        data = response.json()
        assert "transactions" in data
        assert data["count"] > 0

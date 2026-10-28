"""
Live verification script for AI BI Assistant.
Starts the FastAPI server, tests all endpoints with live HTTP requests, and reports results.
"""
import time
import threading
import requests
import uvicorn
from main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="warning")

def verify():
    # Start server in thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    time.sleep(2)  # Wait for startup

    base_url = "http://127.0.0.1:8005"
    print("=== LIVE SERVER VERIFICATION ===")

    # 1. Health check
    r = requests.get(f"{base_url}/health")
    print(f"GET /health: {r.status_code} -> {r.json()}")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"

    # 2. Supported questions
    r = requests.get(f"{base_url}/supported")
    print(f"GET /supported: {r.status_code} -> {r.json()['total_types']} types")
    assert r.status_code == 200

    # 3. Data quality summary
    r = requests.get(f"{base_url}/data-quality")
    print(f"GET /data-quality: {r.status_code} -> {r.json()['total_records']} total records, {r.json()['valid_for_revenue']} valid")
    assert r.status_code == 200

    # 4. Ask Q1 - Total Revenue
    r = requests.post(f"{base_url}/ask", json={"question": "What is the total revenue?"})
    print(f"POST /ask (Total Revenue): {r.status_code} -> {r.json()['answer']}")
    assert r.status_code == 200
    assert "1,439,200.00" in r.json()["answer"]

    # 5. Ask Q2 - Highest Product
    r = requests.post(f"{base_url}/ask", json={"question": "Which product generated the highest revenue?"})
    print(f"POST /ask (Highest Product): {r.status_code} -> {r.json()['answer']}")
    assert r.status_code == 200
    assert "Monitor" in r.json()["answer"]

    # 6. Ask Q3 - Monthly Trend
    r = requests.post(f"{base_url}/ask", json={"question": "What is the monthly revenue trend?"})
    print(f"POST /ask (Monthly Trend): {r.status_code} -> {r.json()['data']['trend']} trend")
    assert r.status_code == 200

    # 7. Ask Q4 - Highest Region
    r = requests.post(f"{base_url}/ask", json={"question": "Which region generated the highest sales?"})
    print(f"POST /ask (Highest Region): {r.status_code} -> {r.json()['answer']}")
    assert r.status_code == 200
    assert "South" in r.json()["answer"]

    # 8. Ask Q5 - Revenue Comparison
    r = requests.post(f"{base_url}/ask", json={"question": "How did revenue change between January and February?"})
    print(f"POST /ask (Comparison): {r.status_code} -> {r.json()['answer']}")
    assert r.status_code == 200
    assert "increased" in r.json()["answer"]

    # 9. Unsupported question
    r = requests.post(f"{base_url}/ask", json={"question": "What is the stock price of Apple?"})
    print(f"POST /ask (Unsupported): {r.status_code} -> error={r.json()['error']}")
    assert r.status_code == 200
    assert r.json()["error"] is True

    print("\nALL LIVE ENDPOINT VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    verify()


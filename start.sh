#!/usr/bin/env bash
# Startup script for Render deployment
set -e

export PYTHONIOENCODING=utf-8

# 1. Run Data Ingestion into SQLite
echo "==> Ingesting sales transaction data..."
python data_loader.py

# 2. Start FastAPI Backend in the background on localhost:8000
echo "==> Starting FastAPI backend on http://127.0.0.1:8000 ..."
uvicorn main:app --host 127.0.0.1 --port 8000 &

# Brief pause to ensure FastAPI is up
sleep 3

# 3. Start Streamlit Frontend on the Render-assigned public $PORT
echo "==> Starting Streamlit frontend on port ${PORT:-8501} ..."
exec streamlit run app.py \
    --server.port "${PORT:-8501}" \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false

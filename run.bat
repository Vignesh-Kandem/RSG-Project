@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
echo =======================================================
echo   AI Business Intelligence Assistant - RSG Assessment
echo =======================================================

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please create it first:
    echo   python -m venv .venv
    echo   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

echo [1/3] Checking / Ingesting sales data...
.\.venv\Scripts\python.exe data_loader.py

echo.
echo [2/3] Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "AI BI Assistant - Backend (FastAPI)" cmd /k ".\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 > nul

echo.
echo [3/3] Starting Streamlit Frontend on http://127.0.0.1:8501 ...
start "AI BI Assistant - Frontend (Streamlit)" cmd /k ".\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501"

echo.
echo =======================================================
echo Both services are launching in separate windows!
echo - Backend API Docs: http://127.0.0.1:8000/docs
echo - Frontend UI:      http://127.0.0.1:8501
echo =======================================================
pause

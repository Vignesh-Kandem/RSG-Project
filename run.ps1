# AI Business Intelligence Assistant - PowerShell Startup Script
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "  AI Business Intelligence Assistant - RSG Assessment" -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it first:"
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

Write-Host "`n[1/3] Ingesting sales data into SQLite..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe data_loader.py

Write-Host "`n[2/3] Launching FastAPI Backend (http://127.0.0.1:8000)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle = 'Backend - FastAPI'; `$env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 3

Write-Host "`n[3/3] Launching Streamlit Frontend (http://127.0.0.1:8501)..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle = 'Frontend - Streamlit'; `$env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe -m streamlit run app.py --server.port 8501"

Write-Host "`n=======================================================" -ForegroundColor Green
Write-Host "  Applications started in separate PowerShell windows!" -ForegroundColor Green
Write-Host "  - Backend Swagger Docs: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host "  - Streamlit Dashboard:  http://127.0.0.1:8501" -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Green


"""
FastAPI Backend for AI BI Assistant.
Provides REST API endpoints for question answering and data quality reporting.

Endpoints:
    GET  /health          - Health check
    POST /ask             - Process a business question
    GET  /data-quality    - Data quality summary
    GET  /supported       - List supported question types
    GET  /transactions    - Get all transactions (evidence)
"""
import os
import sys
import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from database import init_db, get_row_count, DB_PATH
from data_loader import load_csv_to_db, get_quality_summary
from nlp_engine import process_question, get_supported_questions
from analytics import get_all_transactions

# ─── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ─── Lifespan Context Manager ───────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and load data on application startup."""
    logger.info("Starting AI BI Assistant API...")

    # Initialize database
    init_db()

    # Load data if database is empty
    row_count = get_row_count()
    if row_count == 0:
        logger.info("Database is empty. Loading CSV data...")
        try:
            result = load_csv_to_db()
            logger.info(
                f"Data loaded: {result['valid_rows']} rows, "
                f"{result['rejected_rows']} rejected, "
                f"{len(result['quality_issues'])} quality issues"
            )
        except FileNotFoundError:
            logger.error(
                "CSV file not found. Please ensure the CSV is in the input/ directory."
            )
        except Exception as e:
            logger.error(f"Error loading data: {e}")
    else:
        logger.info(f"Database already contains {row_count} records.")

    yield
    logger.info("Shutting down AI BI Assistant API...")


# ─── FastAPI Application ────────────────────────────────────────────────
app = FastAPI(
    title="AI Business Intelligence Assistant",
    description=(
        "A mini AI-powered business intelligence assistant that answers "
        "natural language questions about sales transaction data. "
        "Built for the RSG Graduate Engineer Trainee assessment."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware (allow Streamlit frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request/Response Models ────────────────────────────────────────────
class QuestionRequest(BaseModel):
    """Request body for the /ask endpoint."""
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Natural language business question"
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Question cannot be empty.")
        if len(v) < 3:
            raise ValueError("Question is too short. Please ask a complete question.")
        return v


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    record_count: int
    version: str


class AnswerResponse(BaseModel):
    """Structured response for a business question."""
    question: str
    question_type: str
    question_description: Optional[str] = None
    confidence: float
    answer: str
    error: bool = False
    data: Optional[dict] = None


# ─── Endpoints ──────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint.
    Returns application status, database connectivity, and record count.
    """
    try:
        row_count = get_row_count()
        db_status = "connected"
    except Exception as e:
        row_count = 0
        db_status = f"error: {str(e)}"

    return HealthResponse(
        status="healthy",
        database=db_status,
        record_count=row_count,
        version="1.0.0"
    )


@app.post("/ask", tags=["Business Intelligence"])
async def ask_question(request: QuestionRequest):
    """
    Process a natural language business question.
    
    Accepts a question in plain English and returns a structured answer
    with supporting data. The question is classified and routed to the
    appropriate analytics function.
    
    Supported question types:
    - Total Revenue
    - Highest Revenue Product
    - Monthly Revenue Trend
    - Highest Sales Region
    - Revenue Comparison Between Months
    - Category Breakdown
    - Sales Channel Analysis
    - Top Transactions
    - Discount Analysis
    """
    # Validate database has data
    row_count = get_row_count()
    if row_count == 0:
        raise HTTPException(
            status_code=503,
            detail="Database is empty. Data has not been loaded yet."
        )

    # Process the question
    result = process_question(request.question)

    # Separate answer from supporting data
    answer_text = result.pop("answer", "No answer available.")
    question_type = result.pop("question_type", "unknown")
    question_desc = result.pop("question_description", None)
    confidence = result.pop("confidence", 0.0)
    error = result.pop("error", False)
    question = result.pop("question", request.question)

    return {
        "question": question,
        "question_type": question_type,
        "question_description": question_desc,
        "confidence": confidence,
        "answer": answer_text,
        "error": error,
        "data": result
    }


@app.get("/data-quality", tags=["Data Quality"])
async def data_quality():
    """
    Get data quality summary.
    
    Returns information about data quality issues found during ingestion,
    including missing values, returned transactions, and validation flags.
    """
    try:
        summary = get_quality_summary()
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/supported", tags=["System"])
async def supported_questions():
    """
    List all supported question types with examples.
    
    Returns a list of question types that the assistant can answer,
    along with example phrasings for each type.
    """
    return {
        "supported_questions": get_supported_questions(),
        "total_types": len(get_supported_questions())
    }


@app.get("/transactions", tags=["Data"])
async def all_transactions():
    """
    Get all transactions for evidence display.
    
    Returns the complete list of loaded transactions with calculated
    revenue and quality flags.
    """
    try:
        transactions = get_all_transactions()
        return {
            "transactions": transactions,
            "count": len(transactions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Main Entry Point ───────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )

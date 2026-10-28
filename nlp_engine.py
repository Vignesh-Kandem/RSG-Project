"""
NLP Engine for AI BI Assistant.
Rule-based natural language processing to map user questions to analytics functions.

This module uses deterministic pattern matching to interpret user questions.
No external LLM API is required. The approach:
    1. Normalize the input text
    2. Match against known question patterns using keyword scoring
    3. Extract parameters (e.g., month names) from the question
    4. Route to the appropriate analytics function
    5. Return structured results

AI Integration Design:
    - Current: Rule-based keyword matching (no API keys needed)
    - Future: Can be replaced with LLM-based NLU for better coverage
    - Safety: No text-to-SQL — all queries are pre-defined and parameterized
    - Validation: Only supported question types are answered
"""
import re
import logging
from typing import Optional, Dict, Any, Tuple, List

from analytics import (
    get_total_revenue,
    get_highest_revenue_product,
    get_monthly_revenue_trend,
    get_highest_sales_region,
    get_revenue_comparison,
    get_category_breakdown,
    get_sales_channel_breakdown,
    get_top_transactions,
    get_discount_analysis,
)

logger = logging.getLogger(__name__)

# Month name to number mapping
MONTH_MAP = {
    "january": "01", "jan": "01", "1": "01",
    "february": "02", "feb": "02", "2": "02",
    "march": "03", "mar": "03", "3": "03",
    "april": "04", "apr": "04", "4": "04",
    "may": "05", "5": "05",
    "june": "06", "jun": "06", "6": "06",
    "july": "07", "jul": "07", "7": "07",
    "august": "08", "aug": "08", "8": "08",
    "september": "09", "sep": "09", "sept": "09", "9": "09",
    "october": "10", "oct": "10", "10": "10",
    "november": "11", "nov": "11", "11": "11",
    "december": "12", "dec": "12", "12": "12",
}

# Question type definitions with keyword patterns
QUESTION_TYPES = {
    "total_revenue": {
        "keywords": ["total revenue", "overall revenue", "total sales", "total earning",
                      "how much revenue", "sum of revenue", "aggregate revenue",
                      "what is the revenue", "gross revenue", "net revenue",
                      "entire revenue", "all revenue"],
        "weight_keywords": ["total", "overall", "sum", "aggregate", "entire", "all"],
        "description": "Total Revenue",
        "examples": ["What is the total revenue?", "How much revenue was generated?"]
    },
    "highest_revenue_product": {
        "keywords": ["highest revenue product", "top product", "best selling product",
                      "most revenue product", "which product", "product highest",
                      "best product", "top selling", "most profitable product",
                      "product with highest"],
        "weight_keywords": ["product", "which product"],
        "description": "Highest Revenue Product",
        "examples": ["Which product generated the highest revenue?",
                      "What is the top selling product?"]
    },
    "monthly_trend": {
        "keywords": ["monthly revenue", "revenue trend", "monthly trend",
                      "month by month", "monthly sales", "revenue over time",
                      "monthly breakdown", "month over month", "revenue each month",
                      "monthly pattern"],
        "weight_keywords": ["monthly", "trend", "month by month", "over time"],
        "description": "Monthly Revenue Trend",
        "examples": ["What is the monthly revenue trend?",
                      "Show me revenue month by month"]
    },
    "highest_sales_region": {
        "keywords": ["highest sales region", "top region", "best region",
                      "most sales region", "which region", "region highest",
                      "regional sales", "best performing region",
                      "region with highest", "top performing region"],
        "weight_keywords": ["region", "which region"],
        "description": "Highest Sales Region",
        "examples": ["Which region generated the highest sales?",
                      "What is the top performing region?"]
    },
    "revenue_comparison": {
        "keywords": ["revenue change", "compare months", "month comparison",
                      "revenue between", "how did revenue change",
                      "compare revenue", "difference between months",
                      "month to month", "revenue changed", "revenue growth",
                      "compare", "vs", "versus"],
        "weight_keywords": ["between", "compare", "change", "vs", "versus"],
        "description": "Revenue Comparison Between Months",
        "examples": [
            "How did revenue change between January and February?",
            "Compare revenue for March vs April"
        ]
    },
    "category_breakdown": {
        "keywords": ["category breakdown", "by category", "category revenue",
                      "product category", "categories", "category wise",
                      "category analysis", "which category"],
        "weight_keywords": ["category", "categories"],
        "description": "Category Breakdown",
        "examples": ["Show revenue by category", "Which category performs best?"]
    },
    "sales_channel": {
        "keywords": ["sales channel", "online vs retail", "channel breakdown",
                      "online retail", "channel wise", "channel analysis",
                      "online sales", "retail sales"],
        "weight_keywords": ["channel", "online", "retail"],
        "description": "Sales Channel Breakdown",
        "examples": ["Show sales by channel", "Compare online vs retail"]
    },
    "top_transactions": {
        "keywords": ["top transactions", "biggest transactions", "largest orders",
                      "highest value transactions", "biggest orders",
                      "largest transactions"],
        "weight_keywords": ["transactions", "orders"],
        "description": "Top Transactions",
        "examples": ["Show top 10 transactions", "What are the biggest orders?"]
    },
    "discount_analysis": {
        "keywords": ["discount", "discounts", "discount analysis",
                      "discounted transactions", "discount amount", "how much discount"],
        "weight_keywords": ["discount"],
        "description": "Discount Analysis",
        "examples": ["Show discount analysis", "Which transactions had discounts?"]
    }
}


def normalize_text(text: str) -> str:
    """Normalize user input for matching."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text)       # Collapse whitespace
    return text


def extract_months(text: str) -> List[str]:
    """
    Extract month references from the question text,
    preserving the exact order of appearance in the user query.
    """
    normalized = normalize_text(text)

    # Sort month names by length (longest first) to match e.g. "january" before "jan"
    sorted_month_names = sorted(MONTH_MAP.keys(), key=len, reverse=True)

    matched_spans = []
    occupied_indices = set()

    for month_name in sorted_month_names:
        pattern = r'\b' + re.escape(month_name) + r'\b'
        for m in re.finditer(pattern, normalized):
            start, end = m.span()
            if not any(i in occupied_indices for i in range(start, end)):
                matched_spans.append((start, end, MONTH_MAP[month_name]))
                occupied_indices.update(range(start, end))

    # Sort by order of appearance in text
    matched_spans.sort(key=lambda x: x[0])

    found_months = []
    for _, _, month_num in matched_spans:
        if month_num not in found_months:
            found_months.append(month_num)

    return found_months


STOP_WORDS = {
    "what", "is", "the", "a", "an", "of", "and", "or", "in", "for", "to",
    "how", "did", "from", "with", "much", "was", "are", "be", "me", "show",
    "tell", "give", "get", "which"
}


def classify_question(text: str) -> Tuple[str, float]:
    """
    Classify a user question into a known question type.
    
    Returns:
        Tuple of (question_type, confidence_score)
        Returns ("unknown", 0.0) if no match is found.
    """
    normalized = normalize_text(text)
    scores = {}

    for qtype, config in QUESTION_TYPES.items():
        score = 0.0

        # Check full phrase matches
        for keyword in config["keywords"]:
            if keyword in normalized:
                score += 3.0

        # Check weight keywords (domain indicators)
        for keyword in config["weight_keywords"]:
            if keyword in normalized:
                score += 1.5

        # Check individual meaningful word matches (excluding stop words)
        words = set(normalized.split()) - STOP_WORDS
        for keyword in config["keywords"]:
            keyword_words = set(keyword.split()) - STOP_WORDS
            overlap = words & keyword_words
            score += len(overlap) * 0.5

        scores[qtype] = score

    if not scores:
        return "unknown", 0.0

    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Require minimum confidence score
    if best_score < 2.5:
        return "unknown", 0.0

    # Normalize score to 0-1 range
    confidence = min(best_score / 10.0, 1.0)

    return best_type, confidence


def process_question(
    question: str,
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Process a natural language question and return a structured answer.
    
    This is the main entry point for the NLP engine.
    
    Args:
        question: Natural language question from the user
        db_path: Optional database path override
        
    Returns:
        Dictionary with answer, question_type, confidence, and supporting data
    """
    if not question or not question.strip():
        return {
            "question": question,
            "question_type": "invalid",
            "confidence": 0.0,
            "answer": "Please enter a valid question.",
            "error": True,
            "supported_questions": get_supported_questions()
        }

    # Classify the question
    question_type, confidence = classify_question(question)
    logger.info(f"Classified '{question}' as '{question_type}' (confidence: {confidence:.2f})")

    if question_type == "unknown":
        return {
            "question": question,
            "question_type": "unknown",
            "confidence": confidence,
            "answer": (
                "I'm sorry, I couldn't understand that question. "
                "Please try one of the supported questions below."
            ),
            "error": True,
            "supported_questions": get_supported_questions()
        }

    # Route to appropriate analytics function
    try:
        if question_type == "total_revenue":
            result = get_total_revenue(db_path)

        elif question_type == "highest_revenue_product":
            result = get_highest_revenue_product(db_path)

        elif question_type == "monthly_trend":
            result = get_monthly_revenue_trend(db_path)

        elif question_type == "highest_sales_region":
            result = get_highest_sales_region(db_path)

        elif question_type == "revenue_comparison":
            months = extract_months(question)
            if len(months) >= 2:
                result = get_revenue_comparison(months[0], months[1], db_path)
            elif len(months) == 1:
                # Default: compare with next month
                m = int(months[0])
                next_m = f"{m + 1:02d}" if m < 12 else "01"
                result = get_revenue_comparison(months[0], next_m, db_path)
            else:
                # Default comparison: most recent two months with data
                result = get_revenue_comparison("05", "06", db_path)
                result["note"] = (
                    "No specific months mentioned. Showing May vs June. "
                    "Try: 'Compare revenue between January and March'"
                )

        elif question_type == "category_breakdown":
            result = get_category_breakdown(db_path)

        elif question_type == "sales_channel":
            result = get_sales_channel_breakdown(db_path)

        elif question_type == "top_transactions":
            result = get_top_transactions(db_path=db_path)

        elif question_type == "discount_analysis":
            result = get_discount_analysis(db_path)

        else:
            result = {
                "answer": "This question type is recognized but not yet implemented.",
                "error": True
            }

        result["question"] = question
        result["question_type"] = question_type
        result["question_description"] = QUESTION_TYPES[question_type]["description"]
        result["confidence"] = confidence
        result["error"] = result.get("error", False)

        return result

    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        return {
            "question": question,
            "question_type": question_type,
            "confidence": confidence,
            "answer": f"An error occurred while processing your question: {str(e)}",
            "error": True
        }


def get_supported_questions() -> List[Dict[str, Any]]:
    """Get list of supported question types with examples."""
    return [
        {
            "type": qtype,
            "description": config["description"],
            "examples": config["examples"]
        }
        for qtype, config in QUESTION_TYPES.items()
    ]

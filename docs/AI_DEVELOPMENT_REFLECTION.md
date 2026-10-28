# AI-Assisted Development Reflection Report

**Candidate Role:** Graduate Engineer Trainee (Software Development)  
**Project:** AI-Assisted Business Intelligence Assistant  
**Date:** October 2026  

---

## 1. Which AI Tools Were Used

During this assessment, the following AI tools and engineering environments were leveraged:
- **Claude / Cursor / Gemini / Copilot (AI Coding Assistants)**: Used for scaffolding modular application design, drafting initial Pydantic schema models, formulating parameterized SQLite aggregation queries, and structuring comprehensive Pytest test suites.
- **Python AST & Rule-Based Parsers**: Used for deterministic query mapping and guardrail validation.
- **Generative AI Knowledge Bases**: Consulted for architectural design patterns relating to Vectorless RAG, Agentic AI multi-step decision workflows, and defensive API validation.

---

## 2. How AI Was Used During Development

AI assistance was applied iteratively following engineering best practices:

1. **Requirements Deconstruction & Contract Design**:
   - The assignment specifications and job description were decomposed into concrete functional requirements: data ingestion, query validation, API layer, analytics calculations, Streamlit UI, and testing.
   - Pydantic schemas were designed upfront to establish strict contracts between the FastAPI backend and Streamlit frontend.

2. **Automated Exploratory Data Analysis (EDA)**:
   - Used AI to script exploratory data analysis (`analyze_csv.py`), uncovering 3 critical anomalies (Returned row `TXN0033`, Zero-quantity row `TXN0034`, Missing price row `TXN0051`) and verifying discount distributions.
   - Rather than accepting default AI assumptions, the anomalies were translated into an explicit data quality audit log.

3. **Deterministic Query Engineering**:
   - Designed pure, parameterized SQLite queries for the 5 core business questions.
   - Prevented text-to-SQL hallucination or SQL injection by using a rule-based NLP intent classification engine rather than unconstrained LLM prompt execution.

4. **Test Suite Generation**:
   - AI helped scaffold edge-case test fixtures in `conftest.py` with mock datasets to test return handling, missing price exclusions, ranking ties, and month-over-month comparisons without touching production databases.

---

## 3. Problems Encountered

1. **Naive LLM / Text-to-SQL Risks**:
   - Initial AI suggestions proposed using an unconstrained LLM prompt to generate raw SQL from user questions.
   - *Problem*: In a production or enterprise context, unconstrained text-to-SQL poses severe risks: SQL injection, syntax hallucination, non-deterministic aggregation, or unintentional `DROP`/`UPDATE` operations.

2. **Discount Ambiguity**:
   - CSV columns included `Discount_amount` with values like `500`, `1000`, `2500`.
   - *Problem*: A standard LLM without domain knowledge might interpret `500` as a percentage error or arbitrary code rather than an absolute currency deduction in ₹.

3. **Date Format & Ordering Anomalies**:
   - Dates in the CSV follow the Indian/British format (`DD-MM-YYYY`), whereas default SQLite date functions (`strftime('%Y-%m')`) expect ISO-8601 (`YYYY-MM-DD`).
   - *Problem*: Direct date string comparisons in SQL would sort alphabetically by day (`01-02-2026` before `02-01-2026`), corrupting monthly trend aggregations.

4. **Missing Values & Imputation Hazards**:
   - `TXN0051` had `NaN` for `Unit_price`.
   - *Problem*: Automated AI data pipelines often suggest `df.fillna(0)` or imputing the mean/mode. In financial accounting, silently imputing price masks upstream invoicing errors and leads to misleading revenue reporting.

---

## 4. How They Were Debugged & Resolved

1. **Replacing Raw Text-to-SQL with Deterministic Intent Classification**:
   - Implemented `nlp_engine.py` with a keyword scoring matrix and temporal entity extraction.
   - Guarded database interaction with `execute_safe_query()`, enforcing keyword boundary checks and rejecting all write operations (`INSERT`, `UPDATE`, `DELETE`, `DROP`).

2. **Empirical Verification of Discounts**:
   - Analyzed discount distribution using Pandas. Confirmed all discounts are multiples of ₹500 and correspond to high-value orders (e.g. ₹500 off a ₹57,000 order).
   - Standardized formula: `Net Revenue = (Quantity * Unit_price) - Discount_amount`.

3. **String Substring Date Extraction in SQLite**:
   - Implemented `SUBSTR(order_date, 7, 4) || '-' || SUBSTR(order_date, 4, 2)` as a synthetic sort key (`YYYY-MM`), ensuring proper chronological ordering across months.

4. **Transparent Rejection & Quality Logging**:
   - Created `is_valid` flag and `data_quality_log` table. `TXN0051` is retained in the database for auditing but excluded from revenue sums (`revenue = NULL, is_valid = 0`), reporting the exact reason back to the user via `/data-quality`.

---

## 5. What Would Be Improved With Another Day of Work

With an additional day of development, the following enhancements would be prioritized:

1. **Agentic AI & Vectorless RAG Integration**:
   - Integrate **LangChain** or **Google Antigravity SDK** agent with tools for schema inspection, query execution, and conversational memory.
   - Implement **Vectorless RAG**: inject database schema metadata, column statistics, and data dictionaries directly into the system prompt context.

2. **Dynamic Charting & Visual Dashboarding**:
   - Add interactive Plotly / Vega-Lite visualizers in the Streamlit frontend with drill-down filters (filtering by region, sales channel, date range).
   - Export functionality (PDF executive summary or CSV export of evidence tables).

3. **Multi-turn Dialogue & Conversational Memory**:
   - Maintain conversation state (e.g., user asks "Which product had highest revenue?", followed by "How much did it sell in the North region?").

4. **Continuous Integration & Automated Ingestion Pipeline**:
   - Add GitHub Actions CI workflow to run pytest, flake8, and black on every commit.
   - Implement file watcher / webhook endpoint to trigger automatic ingestion when a new batch CSV is uploaded.

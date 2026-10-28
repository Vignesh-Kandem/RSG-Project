# Data Quality Assessment & Business Logic Rules

## 1. Executive Summary

A comprehensive data quality audit was conducted on the sales transaction dataset (`ai_bi_assistant_sales_data - GET.csv`). The dataset contains **51 transaction records** spanning 6 months from **January 3, 2026 to June 28, 2026**.

Overall data hygiene is good, but three specific data anomalies were identified that directly impact revenue calculations. Explicit, defensible business rules were established to handle each anomaly consistently across all backend queries.

---

## 2. Dataset Overview

| Metric | Value | Details |
|---|---|---|
| **Total Rows** | 51 | Transaction IDs `TXN0001` through `TXN0051` |
| **Columns** | 10 | `Transaction_Id`, `Order_date`, `Product`, `Category`, `Region`, `Sales_channel`, `Quantity`, `Unit_price`, `Discount_amount`, `Status` |
| **Date Range** | Jan 3, 2026 – Jun 28, 2026 | Exactly 6 full calendar months |
| **Unique Products** | 7 | Laptop Stand, Wireless Mouse, Office Chair, Monitor, Keyboard, Desk, USB-C Hub |
| **Categories** | 3 | Accessories, Furniture, Electronics |
| **Regions** | 4 | North, South, East, West |
| **Sales Channels** | 2 | Online (28 transactions), Retail (23 transactions) |
| **Status Breakdown** | 50 Completed, 1 Returned | 98.0% completion rate |

---

## 3. Discovered Anomalies & Resolution Policies

### Anomaly 1: Returned Transaction
- **Record**: `TXN0033` (Order Date: 26-04-2026, Product: Monitor, Quantity: 2, Unit_Price: ₹9,500, Status: `Returned`)
- **Impact**: Gross value would have been ₹19,000.
- **Business Rule**: Returned transactions **must not be recognized as revenue**. The row is ingested into the database with `is_valid = 0` and logged in `data_quality_log`. It remains accessible for operational analytics (e.g. return rate analysis) but is excluded from all revenue totals and KPI cards (`WHERE is_valid = 1`).

### Anomaly 2: Missing Unit Price
- **Record**: `TXN0051` (Order Date: 28-06-2026, Product: Laptop Stand, Quantity: 5, Unit_Price: `NaN`, Status: `Completed`)
- **Impact**: Revenue cannot be calculated deterministically without a known price.
- **Business Rule**: Never silently impute price or convert `NaN` to `0` without formal business authorization. The record is flagged with `is_valid = 0`, `revenue = NULL`, and logged as `Missing unit price`. (Note: while other Laptop Stand records list ₹1,200, automated imputation risks masking upstream pricing or system errors).

### Anomaly 3: Zero Quantity Transaction
- **Record**: `TXN0034` (Order Date: 28-04-2026, Product: Keyboard, Quantity: 0, Unit_Price: ₹900, Status: `Completed`)
- **Impact**: Zero units sold.
- **Business Rule**: Preserved in the database with `is_valid = 1` and `revenue = 0.0`. It counts towards transaction volume but contributes ₹0 to monetary revenue. Flagged with quality note `Zero quantity` for operational audit.

### Anomaly 4: Discount Interpretation
- **Data Distribution**: Discounts occur in 4 transactions (`TXN0004`: ₹500, `TXN0012`: ₹1,000, `TXN0022`: ₹2,500, `TXN0028`: ₹500). All discount values are integer increments (500, 1000, 2500).
- **Business Rule**: `Discount_amount` represents a **flat monetary deduction (in ₹)**, not a percentage rate.
  $$\text{Net Revenue} = \max((\text{Quantity} \times \text{Unit\_Price}) - \text{Discount\_Amount}, 0)$$
  Discounts are strictly deducted from the gross line item value.

---

## 4. Business Logic Rules Summary Table

| Category | Policy / Decision | Implementation |
|---|---|---|
| **Revenue Formula** | Net Revenue = $(\text{Quantity} \times \text{Unit\_Price}) - \text{Discount}$ | Evaluated at row ingestion and stored in `revenue` column |
| **Returns** | Excluded from revenue aggregation | `WHERE is_valid = 1` filters out `Status = 'Returned'` |
| **Missing Price** | Excluded from revenue calculation | Stored with `revenue = NULL, is_valid = 0` |
| **Zero Quantity** | Recorded with ₹0 revenue | Valid transaction, zero financial contribution |
| **Duplicates** | Idempotent insertion | `UNIQUE(transaction_id)` constraint; existing records skipped |
| **Date Parsing** | Standardized `DD-MM-YYYY` | `SUBSTR(order_date, 4, 2)` extracts 2-digit month consistently |
| **Ranking Ties** | Explicitly reported in response | `analytics.py` checks for multiple items with max value |
| **Empty Results** | Graceful fallback response | Returns structured zero values instead of HTTP 500 error |

---

## 5. Audit Logging Architecture

Every quality issue detected during data ingestion is persisted in the `data_quality_log` SQLite table:

```sql
CREATE TABLE data_quality_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    description TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

This guarantees complete traceability and provides transparency to business stakeholders via the `GET /data-quality` API and the Streamlit UI Data Quality tab.

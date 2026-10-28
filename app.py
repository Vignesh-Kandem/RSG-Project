"""
Streamlit Frontend for AI BI Assistant.
Professional, responsive interface for business intelligence queries.
"""
import streamlit as st
import requests
import pandas as pd
import json
from typing import Optional, Dict, Any

# ─── Configuration ──────────────────────────────────────────────────────
API_BASE_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="AI Business Intelligence Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Main container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* KPI Card styling */
    .kpi-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        margin-bottom: 1rem;
    }
    .kpi-card h3 {
        margin: 0;
        font-size: 0.9rem;
        opacity: 0.9;
        font-weight: 500;
    }
    .kpi-card h2 {
        margin: 0.5rem 0 0 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    .kpi-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
    }
    .kpi-orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        box-shadow: 0 4px 15px rgba(245, 87, 108, 0.3);
    }
    .kpi-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        box-shadow: 0 4px 15px rgba(79, 172, 254, 0.3);
    }
    
    /* Answer box */
    .answer-box {
        background: #f0f7ff;
        border-left: 5px solid #667eea;
        padding: 1.2rem 1.5rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
        font-size: 1.05rem;
        line-height: 1.6;
    }
    
    /* Question chips */
    .question-chip {
        display: inline-block;
        padding: 0.4rem 0.8rem;
        background: #e8eef7;
        border-radius: 20px;
        font-size: 0.85rem;
        margin: 0.2rem;
        color: #333;
    }
    
    /* Header styling */
    .main-header {
        text-align: center;
        padding: 1rem 0 2rem 0;
    }
    .main-header h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 800;
        margin-bottom: 0.5rem;
    }
    .main-header p {
        color: #666;
        font-size: 1.05rem;
    }
    
    /* Quality badge */
    .quality-good { color: #11998e; font-weight: 600; }
    .quality-warning { color: #f5a623; font-weight: 600; }
    .quality-error { color: #f5576c; font-weight: 600; }
    
    /* Sidebar styling */
    .sidebar-section {
        background: #f8f9fc;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)


# ─── Helper Functions ───────────────────────────────────────────────────

def check_api_health() -> Optional[Dict]:
    """Check if the backend API is healthy."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            return response.json()
    except requests.ConnectionError:
        return None
    except Exception:
        return None
    return None


def ask_api(question: str) -> Optional[Dict]:
    """Send a question to the API and return the response."""
    try:
        response = requests.post(
            f"{API_BASE_URL}/ask",
            json={"question": question},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code} - {response.text}")
            return None
    except requests.ConnectionError:
        st.error("❌ Cannot connect to the backend API. Please ensure it is running on port 8000.")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


def get_data_quality() -> Optional[Dict]:
    """Fetch data quality summary from the API."""
    try:
        response = requests.get(f"{API_BASE_URL}/data-quality", timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def format_currency(value: float) -> str:
    """Format a number as Indian currency."""
    if value is None:
        return "N/A"
    return f"₹{value:,.2f}"


def render_kpi_card(title: str, value: str, css_class: str = ""):
    """Render a styled KPI card."""
    st.markdown(f"""
    <div class="kpi-card {css_class}">
        <h3>{title}</h3>
        <h2>{value}</h2>
    </div>
    """, unsafe_allow_html=True)


# ─── Main Application ──────────────────────────────────────────────────

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📊 AI Business Intelligence Assistant</h1>
        <p>Ask natural language questions about sales data and get instant insights</p>
    </div>
    """, unsafe_allow_html=True)

    # ─── Sidebar ────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔌 System Status")

        health = check_api_health()
        if health:
            st.success(f"✅ API Connected — {health['record_count']} records loaded")
        else:
            st.error("❌ API Offline — Start the backend with: `python main.py`")
            st.info("Run in a separate terminal:\n```\npython main.py\n```")
            st.stop()

        st.markdown("---")

        # Data Quality Section
        st.markdown("### 📋 Data Quality")
        quality = get_data_quality()
        if quality:
            st.metric("Total Records", quality.get("total_records", 0))
            st.metric("Valid for Revenue", quality.get("valid_for_revenue", 0))
            st.metric("Excluded", quality.get("excluded_from_revenue", 0))

            issues_count = quality.get("excluded_from_revenue", 0)
            if issues_count == 0:
                st.markdown('<span class="quality-good">✓ No quality issues</span>',
                            unsafe_allow_html=True)
            else:
                st.markdown(
                    f'<span class="quality-warning">⚠ {issues_count} record(s) excluded</span>',
                    unsafe_allow_html=True
                )

            with st.expander("Quality Details"):
                if quality.get("returned_transactions", 0) > 0:
                    st.write(f"🔄 Returned: {quality['returned_transactions']}")
                if quality.get("missing_unit_price", 0) > 0:
                    st.write(f"❓ Missing Price: {quality['missing_unit_price']}")
                if quality.get("zero_quantity_records", 0) > 0:
                    st.write(f"0️⃣ Zero Quantity: {quality['zero_quantity_records']}")
                if quality.get("discounted_transactions", 0) > 0:
                    st.write(f"🏷️ Discounted: {quality['discounted_transactions']}")

                if quality.get("issues"):
                    st.markdown("**Issue Log:**")
                    for issue in quality["issues"]:
                        st.write(
                            f"- **{issue['transaction_id']}**: "
                            f"{issue['description']} → {issue['action_taken']}"
                        )

        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown(
            "Built for the **RSG GET Assessment**. "
            "Uses rule-based NLP to interpret questions and "
            "SQLite for data storage."
        )
        st.markdown(
            "**Revenue Formula:** `Qty × Price − Discount`"
        )

    # ─── Main Content ───────────────────────────────────────────────

    # Example Questions
    st.markdown("### 💡 Try an Example Question")

    example_questions = [
        "What is the total revenue?",
        "Which product generated the highest revenue?",
        "What is the monthly revenue trend?",
        "Which region generated the highest sales?",
        "How did revenue change between January and February?",
        "Show revenue by category",
        "Compare online vs retail sales",
        "Show discount analysis",
        "What are the top transactions?",
    ]

    # Create columns for example question buttons
    cols = st.columns(3)
    selected_example = None
    for i, q in enumerate(example_questions):
        with cols[i % 3]:
            if st.button(q, key=f"example_{i}", use_container_width=True):
                selected_example = q

    st.markdown("---")

    # Question Input
    st.markdown("### 🔍 Ask a Question")

    question = st.text_input(
        "Type your business question below:",
        value=selected_example or "",
        placeholder="e.g., What is the total revenue?",
        key="question_input"
    )

    ask_button = st.button("🚀 Get Answer", type="primary", use_container_width=True)

    # Process question
    if ask_button and question:
        with st.spinner("Analyzing your question..."):
            result = ask_api(question)

        if result:
            # ─── Answer Display ─────────────────────────────────
            st.markdown("---")

            # Question type and confidence
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f"**Question Type:** {result.get('question_description', result.get('question_type', 'Unknown'))}"
                )
            with col2:
                confidence = result.get("confidence", 0)
                conf_pct = f"{confidence * 100:.0f}%"
                st.markdown(f"**Confidence:** {conf_pct}")

            # Main answer
            if result.get("error"):
                st.warning(result.get("answer", "Unable to process question."))

                # Show supported questions
                if result.get("data", {}).get("supported_questions"):
                    st.markdown("**Supported questions:**")
                    for sq in result["data"]["supported_questions"]:
                        for ex in sq.get("examples", []):
                            st.markdown(f"- {ex}")
            else:
                st.markdown(
                    f'<div class="answer-box">{result["answer"]}</div>',
                    unsafe_allow_html=True
                )

                data = result.get("data", {})
                q_type = result.get("question_type", "")

                # ─── Render visualizations based on question type ──

                if q_type == "total_revenue":
                    render_total_revenue(data)

                elif q_type == "highest_revenue_product":
                    render_product_revenue(data)

                elif q_type == "monthly_trend":
                    render_monthly_trend(data)

                elif q_type == "highest_sales_region":
                    render_region_sales(data)

                elif q_type == "revenue_comparison":
                    render_revenue_comparison(data)

                elif q_type == "category_breakdown":
                    render_category_breakdown(data)

                elif q_type == "sales_channel":
                    render_sales_channel(data)

                elif q_type == "top_transactions":
                    render_top_transactions(data)

                elif q_type == "discount_analysis":
                    render_discount_analysis(data)

    elif ask_button and not question:
        st.warning("Please enter a question first.")


# ─── Visualization Functions ────────────────────────────────────────────

def render_total_revenue(data: Dict):
    """Render total revenue with KPI cards."""
    cols = st.columns(3)
    with cols[0]:
        render_kpi_card("Total Revenue", format_currency(data.get("total_revenue", 0)))
    with cols[1]:
        render_kpi_card("Gross Revenue", format_currency(data.get("gross_revenue", 0)), "kpi-green")
    with cols[2]:
        render_kpi_card("Total Discount", format_currency(data.get("total_discount", 0)), "kpi-orange")

    st.metric("Valid Transactions", data.get("transaction_count", 0))

    with st.expander("📝 Calculation Details"):
        details = data.get("details", {})
        st.write(f"**Formula:** {details.get('formula', 'N/A')}")
        st.write(f"**Scope:** {details.get('scope', 'N/A')}")
        st.write(f"**Excluded:** {details.get('excluded', 'N/A')}")


def render_product_revenue(data: Dict):
    """Render product revenue breakdown with chart."""
    products = data.get("products", [])
    if not products:
        return

    # KPI
    cols = st.columns(3)
    with cols[0]:
        render_kpi_card("Top Product", data.get("top_product", "N/A"))
    with cols[1]:
        render_kpi_card("Top Revenue", format_currency(data.get("top_revenue", 0)), "kpi-green")
    with cols[2]:
        render_kpi_card("Products Analyzed", str(len(products)), "kpi-blue")

    # Chart
    df = pd.DataFrame(products)
    df = df.sort_values("total_revenue", ascending=True)
    st.bar_chart(df.set_index("product")["total_revenue"])

    # Table
    with st.expander("📊 Detailed Product Data"):
        display_df = pd.DataFrame(products)
        display_df["total_revenue"] = display_df["total_revenue"].apply(
            lambda x: f"₹{x:,.2f}"
        )
        display_df.columns = ["Product", "Revenue", "Quantity", "Transactions", "Discount"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_monthly_trend(data: Dict):
    """Render monthly revenue trend with line chart."""
    monthly_data = data.get("monthly_data", [])
    if not monthly_data:
        return

    month_names = data.get("month_names", {})

    # Chart data
    chart_data = []
    for entry in monthly_data:
        month_num = entry["sort_key"].split("-")[1]
        month_name = month_names.get(month_num, month_num)
        chart_data.append({
            "Month": month_name,
            "Revenue": entry["monthly_revenue"]
        })

    df = pd.DataFrame(chart_data)
    st.line_chart(df.set_index("Month")["Revenue"])

    # MoM change table
    with st.expander("📊 Monthly Details"):
        detail_data = []
        for entry in monthly_data:
            month_num = entry["sort_key"].split("-")[1]
            month_name = month_names.get(month_num, month_num)
            detail_data.append({
                "Month": month_name,
                "Revenue": f"₹{entry['monthly_revenue']:,.2f}",
                "Transactions": entry["transaction_count"],
                "Units Sold": entry["total_quantity"],
                "MoM Change": f"₹{entry.get('mom_change', 0):,.2f}",
                "MoM %": f"{entry.get('mom_change_pct', 0):+.2f}%"
            })
        st.dataframe(pd.DataFrame(detail_data), use_container_width=True, hide_index=True)


def render_region_sales(data: Dict):
    """Render regional sales breakdown."""
    regions = data.get("regions", [])
    if not regions:
        return

    # KPIs
    cols = st.columns(4)
    for i, region in enumerate(regions):
        with cols[i % 4]:
            css = ["", "kpi-green", "kpi-blue", "kpi-orange"][i % 4]
            render_kpi_card(
                f"📍 {region['region']}",
                format_currency(region["total_revenue"]),
                css
            )

    # Chart
    df = pd.DataFrame(regions)
    st.bar_chart(df.set_index("region")["total_revenue"])

    # Table
    with st.expander("📊 Regional Details"):
        display_df = pd.DataFrame(regions)
        display_df["total_revenue"] = display_df["total_revenue"].apply(
            lambda x: f"₹{x:,.2f}"
        )
        display_df.columns = ["Region", "Revenue", "Quantity", "Transactions", "Discount"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_revenue_comparison(data: Dict):
    """Render month-to-month revenue comparison."""
    month1 = data.get("month1", {})
    month2 = data.get("month2", {})

    if not month1 or not month2:
        return

    # KPIs
    cols = st.columns(3)
    with cols[0]:
        render_kpi_card(
            f"📅 {month1.get('name', 'Month 1')}",
            format_currency(month1.get("revenue", 0))
        )
    with cols[1]:
        render_kpi_card(
            f"📅 {month2.get('name', 'Month 2')}",
            format_currency(month2.get("revenue", 0)),
            "kpi-green"
        )
    with cols[2]:
        change = data.get("change", 0)
        pct = data.get("change_pct", 0)
        direction = data.get("direction", "unchanged")
        emoji = "📈" if change > 0 else ("📉" if change < 0 else "➡️")
        render_kpi_card(
            f"{emoji} Change ({pct:+.1f}%)",
            format_currency(change),
            "kpi-blue" if change >= 0 else "kpi-orange"
        )

    # Comparison chart
    chart_data = pd.DataFrame({
        "Month": [month1.get("name", "M1"), month2.get("name", "M2")],
        "Revenue": [month1.get("revenue", 0), month2.get("revenue", 0)]
    })
    st.bar_chart(chart_data.set_index("Month")["Revenue"])

    if data.get("note"):
        st.info(f"ℹ️ {data['note']}")


def render_category_breakdown(data: Dict):
    """Render category breakdown."""
    categories = data.get("categories", [])
    if not categories:
        return

    df = pd.DataFrame(categories)
    st.bar_chart(df.set_index("category")["total_revenue"])

    with st.expander("📊 Category Details"):
        display_df = pd.DataFrame(categories)
        display_df["total_revenue"] = display_df["total_revenue"].apply(
            lambda x: f"₹{x:,.2f}"
        )
        display_df.columns = ["Category", "Revenue", "Quantity", "Transactions"]
        st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_sales_channel(data: Dict):
    """Render sales channel comparison."""
    channels = data.get("channels", [])
    if not channels:
        return

    cols = st.columns(len(channels))
    for i, ch in enumerate(channels):
        with cols[i]:
            css = ["", "kpi-green"][i % 2]
            render_kpi_card(f"🛒 {ch['sales_channel']}", format_currency(ch["total_revenue"]), css)

    df = pd.DataFrame(channels)
    st.bar_chart(df.set_index("sales_channel")["total_revenue"])


def render_top_transactions(data: Dict):
    """Render top transactions table."""
    transactions = data.get("transactions", [])
    if not transactions:
        return

    df = pd.DataFrame(transactions)
    df["revenue"] = df["revenue"].apply(lambda x: f"₹{x:,.2f}" if x else "N/A")
    df["unit_price"] = df["unit_price"].apply(lambda x: f"₹{x:,.2f}" if x else "N/A")
    df["discount_amount"] = df["discount_amount"].apply(lambda x: f"₹{x:,.2f}" if x else "₹0")
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_discount_analysis(data: Dict):
    """Render discount analysis."""
    transactions = data.get("discounted_transactions", [])

    cols = st.columns(2)
    with cols[0]:
        render_kpi_card("Discounted Transactions", str(data.get("count", 0)))
    with cols[1]:
        render_kpi_card("Total Discount", format_currency(data.get("total_discount", 0)), "kpi-orange")

    if transactions:
        df = pd.DataFrame(transactions)
        display_cols = ["transaction_id", "product", "quantity", "unit_price",
                        "discount_amount", "revenue", "discount_pct"]
        df_display = df[display_cols].copy()
        df_display["unit_price"] = df_display["unit_price"].apply(lambda x: f"₹{x:,.2f}")
        df_display["discount_amount"] = df_display["discount_amount"].apply(lambda x: f"₹{x:,.2f}")
        df_display["revenue"] = df_display["revenue"].apply(lambda x: f"₹{x:,.2f}")
        df_display["discount_pct"] = df_display["discount_pct"].apply(lambda x: f"{x:.1f}%")
        df_display.columns = ["Transaction", "Product", "Qty", "Unit Price",
                              "Discount", "Revenue", "Discount %"]
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ─── Run ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()

import streamlit as st
from components.forms import render_operational_forms

# 1. Page Configuration
st.set_page_config(
    page_title="Enterprise Employee Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Header
st.title("🏢 Enterprise Employee Analytics & DW System")
st.caption("Centralized Operational Management & Analytical Data Warehousing Platform")

# 3. Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a View:",
    ["📊 Executive Analytics (OLAP)", "📝 Operational Management (OLTP)", "⚙️ System Status"]
)

# 4. View Router
if page == "📊 Executive Analytics (OLAP)":
    st.header("Executive Analytics Dashboard")
    st.info("Interactive visual reports powered by the Dimensional Data Warehouse will load here.")

elif page == "📝 Operational Management (OLTP)":
    # Call the form render function from components/forms.py
    render_operational_forms()

else:
    st.header("System & Infrastructure Status")
    st.success("Frontend active. Awaiting MySQL database connection...")
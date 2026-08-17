import sys
import os 

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

import streamlit as st
from components.forms import render_operational_forms
from components.charts import render_analytics_dashboard

# 1. Page Configuration
st.set_page_config(
    page_title="Enterprise Employee Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Main Title Header
st.title("🏢 Enterprise Employee Analytics & DW System")
st.caption("Centralized Operational Management & Analytical Data Warehousing Platform")

# 3. Sidebar Navigation Menu
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Select a View:",
    ["📊 Executive Analytics (OLAP)", "📝 Operational Management (OLTP)", "⚙️ System Status"]
)

# 4. View Router
if page == "📊 Executive Analytics (OLAP)":
    render_analytics_dashboard()

elif page == "📝 Operational Management (OLTP)":
    render_operational_forms()

else:
    st.header("⚙️ System & Infrastructure Status")
    st.success("Frontend UI active.")
    
    st.markdown("### Architecture Layer Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Layer 1: OLTP Database", "MySQL Schema", "Normalised ERD")
    col2.metric("Layer 2: OLAP Warehouse", "Star Schema", "SCD Type 2 Active")
    col3.metric("Layer 3: UI & Analytics", "Streamlit + Plotly", "Cloud Ready")
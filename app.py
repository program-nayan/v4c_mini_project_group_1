import sys
import os

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from backend.logger import get_logger
import streamlit as st
from components.forms import render_operational_forms
from components.charts import render_analytics_dashboard
from components.chatbot import render_sql_chatbot

logger = get_logger(__name__)
logger.info("Launching Enterprise HR Analytics Application UI")

# 1. Page Configuration
st.set_page_config(
    page_title="Enterprise Employee Analytics",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Main Header
st.title("🏢 Enterprise HR Analytics & DW Platform")
st.caption("Unified Operational Management (OLTP), Data Warehousing (OLAP) & AI Query Engine")
st.divider()

# 3. Sidebar Navigation Menu
st.sidebar.title("🧭 Navigation")
st.sidebar.caption("Enterprise Portal Control")

page = st.sidebar.radio(
    "Select Module:",
    [
        "📊 Executive Analytics (OLAP)", 
        "📝 Operational Management (OLTP)", 
        "💬 AI Data Analyst"
    ]
)

st.sidebar.divider()
st.sidebar.caption("System Status: **Active** 🟢")
st.sidebar.info("💡 **Default Engine:** OLAP Star Schema Enabled")

logger.info("Navigating to module: %s", page)

# 4. Module Router
if page == "📊 Executive Analytics (OLAP)":
    render_analytics_dashboard()

elif page == "📝 Operational Management (OLTP)":
    render_operational_forms()

elif page == "💬 AI Data Analyst":
    render_sql_chatbot()
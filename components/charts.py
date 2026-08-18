import streamlit as st
import pandas as pd
import plotly.express as px
from backend.logger import get_logger
from backend.analytics_manager import AnalyticsManager

logger = get_logger(__name__)

# Cache dataset fetches for 5 minutes (300 seconds) to prevent DB hammering on UI interactions
@st.cache_data(ttl=300)
def fetch_analytics_data():
    """Fetches and caches all analytics datasets from MySQL in a single batch execution."""
    logger.info("Executing batch analytics data fetch from OLAP Data Warehouse (caching for 300s)")
    analytics = AnalyticsManager()
    
    kpis = analytics.get_combined_kpis()
    df_top_performers = pd.DataFrame(analytics.top_performers_by_department(top_n=3))
    df_attrition_dept = pd.DataFrame(analytics.attrition_rate_by_department())
    df_income_role = pd.DataFrame(analytics.avg_income_by_role())
    df_risk_flags = pd.DataFrame(analytics.attrition_risk_flags(low_satisfaction_threshold=2))
    
    logger.info("Successfully fetched and cached all analytics datasets")
    return kpis, df_top_performers, df_attrition_dept, df_income_role, df_risk_flags


def render_analytics_dashboard():
    """Renders OLAP Executive Dashboards backed by cached AnalyticsManager data."""
    logger.info("Rendering Executive Analytics Dashboard")
    st.caption("Live Data Warehouse Analytics (Cached & Optimized Execution)")

    # 1. Fetch Cached Metrics & Datasets
    try:
        kpis, df_top_performers, df_attrition_dept, df_income_role, df_risk_flags = fetch_analytics_data()
        db_live = True
    except Exception as e:
        logger.error("Analytics DW query failed. Operating in offline/fallback mode. Error: %s", e, exc_info=True)
        st.warning(f"⚠️ Analytics DW query failed. Verify MySQL connection settings: {e}")
        db_live = False

    # ---------------------------------------------------------
    # 1. TOP KPI SUMMARY CARDS
    # ---------------------------------------------------------
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    if db_live and kpis:
        kpi1.metric("Active Employees", f"{kpis['active_count']:,}")
        kpi2.metric("Avg Performance Rating", f"{kpis['avg_rating']:.2f} / 4.0")
        kpi3.metric("Avg Monthly Income", f"${kpis['avg_income']:,.2f}")
        kpi4.metric("Avg Job Satisfaction", f"{kpis['avg_satisfaction']:.2f} / 4.0")
    else:
        kpi1.metric("Active Employees", "Offline")
        kpi2.metric("Avg Performance Rating", "Offline")
        kpi3.metric("Avg Monthly Income", "Offline")
        kpi4.metric("Avg Job Satisfaction", "Offline")

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. ANALYTICS TABS
    # ---------------------------------------------------------
    tab_performers, tab_attrition, tab_compensation = st.tabs([
        "🏆 Top Performers (DW Window Function)", 
        "⚠️ Attrition Risk & Department Rate", 
        "💼 Compensation by Job Role"
    ])

    # ---------------------------------------------------------
    # TAB 1: TOP PERFORMERS (SQL WINDOW FUNCTION)
    # ---------------------------------------------------------
    with tab_performers:
        st.subheader("Top 5 Ranked Employees by Department")
        st.caption("SQL Execution: ROW_NUMBER() OVER (PARTITION BY department_name ORDER BY performance_rating DESC, salary_hike DESC)")
        
        if db_live and not df_top_performers.empty:
            # Combine name and rank into a categorical label for the Y-axis
            df_top_performers["emp_label"] = (
                "#" + df_top_performers["rnk"].astype(str) + " " + 
                df_top_performers["full_name"] + " (" + df_top_performers["department_name"] + ")"
            )
            
            fig_rank = px.bar(
                df_top_performers,
                x="percent_salary_hike",
                y="emp_label",
                color="department_name",
                text="performance_rating",
                orientation="h",
                title="Top Ranked Employees (Salary Hike % & Performance)",
                labels={
                    "percent_salary_hike": "Salary Hike (%)",
                    "emp_label": "Rank & Employee Name",
                    "department_name": "Department"
                }
            )
            fig_rank.update_traces(texttemplate='Rating: %{text}/4', textposition='outside')
            fig_rank.update_layout(yaxis={'categoryorder': 'total ascending'}, height=450)
            st.plotly_chart(fig_rank, use_container_width=True)
            
            st.markdown("##### Window Query Output")
            st.dataframe(df_top_performers[["rnk", "department_name", "full_name", "employee_id", "performance_rating", "percent_salary_hike"]], use_container_width=True)
        else:
            st.info("No live DW data available.")

    # ---------------------------------------------------------
    # TAB 2: ATTRITION & SATISFACTION RISK
    # ---------------------------------------------------------
    with tab_attrition:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Attrition Rate by Department (%)")
            if db_live and not df_attrition_dept.empty:
                fig_attr = px.pie(
                    df_attrition_dept, 
                    names="department_name", 
                    values="attrition_rate_pct",
                    title="Attrition Rate Share (%)"
                )
                st.plotly_chart(fig_attr, use_container_width=True)
            else:
                st.info("No attrition data available.")

        with col2:
            st.subheader("Low Job Satisfaction Risk Flags")
            if db_live and not df_risk_flags.empty:
                st.caption("Filtered for Job Satisfaction <= 2")
                st.dataframe(df_risk_flags, use_container_width=True)
            else:
                st.info("No satisfaction risk flags detected.")

    # ---------------------------------------------------------
    # TAB 3: COMPENSATION BY JOB ROLE
    # ---------------------------------------------------------
    with tab_compensation:
        st.subheader("Average Monthly Income by Job Role")
        if db_live and not df_income_role.empty:
            fig_income = px.bar(
                df_income_role,
                x="job_role",
                y="avg_income",
                color="job_role",
                title="Average Monthly Compensation ($)",
                labels={"avg_income": "Avg Monthly Income ($)", "job_role": "Job Role"}
            )
            st.plotly_chart(fig_income, use_container_width=True)
        else:
            st.info("No compensation data available.")
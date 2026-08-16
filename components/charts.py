import streamlit as st
import pandas as pd
import plotly.express as px
from backend.analytics_manager import AnalyticsManager

def render_analytics_dashboard():
    """Renders OLAP Executive Dashboards backed by AnalyticsManager."""
    
    st.caption("Live Data Warehouse Analytics (AnalyticsManager Execution)")

    # 1. Fetch Metrics & Datasets from Data Warehouse Layer
    try:
        analytics = AnalyticsManager()
        
        active_count = analytics.count_active_dim_employees()
        avg_rating = analytics.avg_performance_rating()
        avg_income = analytics.avg_monthly_income_current()
        avg_satisfaction = analytics.avg_job_satisfaction()
        
        df_top_performers = pd.DataFrame(analytics.top_performers_by_department(top_n=3))
        df_attrition_dept = pd.DataFrame(analytics.attrition_rate_by_department())
        df_income_role = pd.DataFrame(analytics.avg_income_by_role())
        df_risk_flags = pd.DataFrame(analytics.attrition_risk_flags(low_satisfaction_threshold=2))
        
        db_live = True
    except Exception as e:
        st.warning(f"⚠️ Analytics DW query failed. Verify MySQL connection settings: {e}")
        db_live = False

    # ---------------------------------------------------------
    # 1. TOP KPI SUMMARY CARDS
    # ---------------------------------------------------------
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    if db_live:
        kpi1.metric("Active DW Employees", f"{active_count:,}" if active_count else "0")
        kpi2.metric("Avg Performance Rating", f"{avg_rating:.2f} / 4.0" if avg_rating else "N/A")
        kpi3.metric("Avg Monthly Income", f"${avg_income:,.2f}" if avg_income else "N/A")
        kpi4.metric("Avg Job Satisfaction", f"{avg_satisfaction:.2f} / 4.0" if avg_satisfaction else "N/A")
    else:
        kpi1.metric("Active DW Employees", "Offline")
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
    # TAB 1: TOP PERFORMERS (DENSE_RANK Window Query)
    # ---------------------------------------------------------
    with tab_performers:
        st.subheader("Top-Ranked Employees by Department")
        st.caption("SQL Execution: DENSE_RANK() OVER (PARTITION BY department_name ORDER BY performance_rating DESC)")
        
        if db_live and not df_top_performers.empty:
            fig_rank = px.bar(
                df_top_performers,
                x="performance_rating",
                y="employee_id",
                color="department_name",
                text="rnk",
                orientation="h",
                title="Top Performers Rank per Department",
                labels={"performance_rating": "Performance Rating", "employee_id": "Employee ID", "rnk": "Rank"}
            )
            fig_rank.update_traces(texttemplate='Rank #%{text}', textposition='outside')
            st.plotly_chart(fig_rank, use_container_width=True)
            
            st.markdown("##### Query Result Set")
            st.dataframe(df_top_performers, use_container_width=True)
        else:
            st.info("No live DW data available or database connection inactive.")

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
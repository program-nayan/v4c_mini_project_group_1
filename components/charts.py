import streamlit as st
import pandas as pd
import plotly.express as px
from backend.analytics_manager import AnalyticsManager


@st.cache_data(ttl=300)
def fetch_analytics_data():
    """Fetches and caches all analytics datasets from MySQL in a single batch execution."""
    analytics = AnalyticsManager()
    
    kpis = analytics.get_combined_kpis()
    df_top_performers = pd.DataFrame(analytics.top_performers_by_department(top_n=5))
    df_attrition_dept = pd.DataFrame(analytics.attrition_rate_by_department())
    df_income_role = pd.DataFrame(analytics.avg_income_by_role())
    df_risk_flags = pd.DataFrame(analytics.attrition_risk_flags(low_satisfaction_threshold=2))
    df_yearly_trends = pd.DataFrame(analytics.yearly_trends())
    
    return kpis, df_top_performers, df_attrition_dept, df_income_role, df_risk_flags, df_yearly_trends


def render_analytics_dashboard():
    """Renders OLAP Executive Dashboards backed by cached AnalyticsManager data."""
    
    st.caption("Live Data Warehouse Analytics (Cached & Optimized Execution)")

    # 1. Fetch Cached Metrics & Datasets
    try:
        (
            kpis, 
            df_top_performers, 
            df_attrition_dept, 
            df_income_role, 
            df_risk_flags, 
            df_yearly_trends
        ) = fetch_analytics_data()
        db_live = True
    except Exception as e:
        st.warning(f"⚠️ Analytics DW query failed. Verify MySQL connection settings: {e}")
        db_live = False

    # ---------------------------------------------------------
    # 1. TOP KPI SUMMARY CARDS
    # ---------------------------------------------------------
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    if db_live and kpis:
        kpi1.metric("Active DW Employees", f"{kpis['active_count']:,}")
        kpi2.metric("Avg Performance Rating", f"{kpis['avg_rating']:.2f} / 4.0")
        kpi3.metric("Avg Monthly Income", f"${kpis['avg_income']:,.2f}")
        kpi4.metric("Avg Job Satisfaction", f"{kpis['avg_satisfaction']:.2f} / 4.0")
    else:
        kpi1.metric("Active DW Employees", "Offline")
        kpi2.metric("Avg Performance Rating", "Offline")
        kpi3.metric("Avg Monthly Income", "Offline")
        kpi4.metric("Avg Job Satisfaction", "Offline")

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. ANALYTICS TABS
    # ---------------------------------------------------------
    tab_performers, tab_attrition, tab_compensation, tab_yoy = st.tabs([
        "🏆 Top Performers", 
        "⚠️ Attrition & Risk", 
        "💼 Compensation by Role",
        "📈 YoY Trends"
    ])

    # ---------------------------------------------------------
    # TAB 1: TOP PERFORMERS (SQL WINDOW FUNCTION)
    # ---------------------------------------------------------
    with tab_performers:
        st.subheader("Top-Ranked Employees by Department")
        st.caption("SQL Execution: ROW_NUMBER() OVER (PARTITION BY department_name ORDER BY performance_rating DESC)")
        
        if db_live and not df_top_performers.empty:
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
            st.dataframe(
                df_top_performers[["rnk", "department_name", "full_name", "employee_id", "performance_rating", "percent_salary_hike"]], 
                use_container_width=True
            )
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

    # ---------------------------------------------------------
    # TAB 4: YEAR-OVER-YEAR (YoY) TRENDS
    # ---------------------------------------------------------
    with tab_yoy:
        st.subheader("Year-over-Year Performance & Compensation Trends")
        st.caption("Aggregated historical trends calculated from Fact_PerformanceReviews & Dim_Date")

        if db_live and not df_yearly_trends.empty:
            df_yearly_trends["year_str"] = df_yearly_trends["year"].astype(str)

            col1, col2 = st.columns(2)

            with col1:
                fig_ratings = px.line(
                    df_yearly_trends,
                    x="year_str",
                    y=["avg_rating", "avg_satisfaction"],
                    markers=True,
                    title="Avg Performance Rating & Satisfaction Score Over Time",
                    labels={"year_str": "Year", "value": "Score (out of 4.0)", "variable": "Metric"}
                )
                fig_ratings.update_layout(legend=dict(title="Metrics"))
                st.plotly_chart(fig_ratings, use_container_width=True)

            with col2:
                fig_income_trend = px.line(
                    df_yearly_trends,
                    x="year_str",
                    y="avg_income",
                    markers=True,
                    title="Average Monthly Compensation ($) Over Time",
                    labels={"year_str": "Year", "avg_income": "Avg Monthly Income ($)"}
                )
                st.plotly_chart(fig_income_trend, use_container_width=True)

            col3, col4 = st.columns(2)

            with col3:
                fig_hike_trend = px.line(
                    df_yearly_trends,
                    x="year_str",
                    y="avg_salary_hike",
                    markers=True,
                    title="Average Salary Hike (%) Over Time",
                    labels={"year_str": "Year", "avg_salary_hike": "Salary Hike (%)"}
                )
                st.plotly_chart(fig_hike_trend, use_container_width=True)

            with col4:
                fig_reviews_vol = px.bar(
                    df_yearly_trends,
                    x="year_str",
                    y="review_count",
                    title="Total Annual Performance Reviews Completed",
                    labels={"year_str": "Year", "review_count": "Review Count"}
                )
                st.plotly_chart(fig_reviews_vol, use_container_width=True)

            st.markdown("##### Detailed Yearly Aggregation Table")
            st.dataframe(df_yearly_trends.drop(columns=["year_str"]), use_container_width=True)
        else:
            st.info("No yearly trend data available.")
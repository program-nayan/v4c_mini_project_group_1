import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

def render_analytics_dashboard():
    """Renders OLAP Executive Analytical Dashboards driven by Star Schema queries."""
    
    st.caption("OLAP Star Schema Analytics (Fact_PerformanceReviews & Dimensions)")

    # ---------------------------------------------------------
    # 1. TOP KPI SUMMARY CARDS
    # ---------------------------------------------------------
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Active Dimension Employees", "102,450", delta="+2,450 YoY")
    kpi2.metric("Avg Performance Rating", "3.42 / 4.0", delta="+0.15 YoY")
    kpi3.metric("Avg Monthly Income", "$6,850", delta="+$420 Hike")
    kpi4.metric("Avg Job Satisfaction", "3.18 / 4.0", delta="-0.05")

    st.markdown("---")

    # ---------------------------------------------------------
    # 2. SUB-NAVIGATION TABS FOR ANALYTICS
    # ---------------------------------------------------------
    tab_yoy, tab_window, tab_satisfaction = st.tabs([
        "📈 YoY Performance Trends", 
        "🏆 Top Performers (Window Functions)", 
        "📊 Satisfaction & Bottleneck Analysis"
    ])

    # ---------------------------------------------------------
    # TAB 1: YEAR-OVER-YEAR PERFORMANCE TRENDS
    # ---------------------------------------------------------
    with tab_yoy:
        st.subheader("Year-over-Year (YoY) Performance & Income Trends")
        st.caption("Source: Fact_PerformanceReviews JOIN Dim_Date JOIN Dim_Department")
        
        # Mocking DW Query Result (Fact joined with Dim_Date & Dim_Department)
        yoy_data = pd.DataFrame({
            "year": [2023, 2023, 2023, 2024, 2024, 2024, 2025, 2025, 2025, 2026, 2026, 2026],
            "department_name": ["Sales", "R&D", "HR"] * 4,
            "avg_performance": [3.1, 3.4, 3.0, 3.25, 3.55, 3.1, 3.3, 3.6, 3.2, 3.45, 3.7, 3.35],
            "avg_monthly_income": [5800, 7200, 5400, 6100, 7600, 5700, 6500, 8100, 6000, 6900, 8500, 6300]
        })

        col1, col2 = st.columns(2)
        
        with col1:
            # Line Chart: Avg Performance Rating over Years by Department
            fig_perf = px.line(
                yoy_data, 
                x="year", 
                y="avg_performance", 
                color="department_name",
                markers=True,
                title="YoY Average Performance Rating by Department",
                labels={"avg_performance": "Avg Rating (1-4)", "year": "Year", "department_name": "Department"}
            )
            fig_perf.update_yaxes(range=[2.5, 4.0])
            st.plotly_chart(fig_perf, use_container_width=True)

        with col2:
            # Bar Chart: Avg Monthly Income Trend by Department
            fig_income = px.bar(
                yoy_data, 
                x="year", 
                y="avg_monthly_income", 
                color="department_name",
                barmode="group",
                title="YoY Average Monthly Income Trend ($)",
                labels={"avg_monthly_income": "Monthly Income ($)", "year": "Year", "department_name": "Department"}
            )
            st.plotly_chart(fig_income, use_container_width=True)

    # ---------------------------------------------------------
    # TAB 2: TOP PERFORMERS (SQL DENSE_RANK WINDOW FUNCTION)
    # ---------------------------------------------------------
    with tab_window:
        st.subheader("Top-Ranked Employees per Department")
        st.caption("Demonstrating SQL Window Function: DENSE_RANK() OVER (PARTITION BY dept_key ORDER BY performance_rating DESC)")
        
        # Mocking SQL Window Function Query Output
        top_performers_df = pd.DataFrame({
            "dept_rank": [1, 2, 3, 1, 2, 3, 1, 2, 3],
            "department_name": ["R&D", "R&D", "R&D", "Sales", "Sales", "Sales", "HR", "HR", "HR"],
            "full_name": ["Alice Walker", "Dr. Robert Bruce", "Carol Danvers", "David Miller", "Emma Watson", "Frank Castle", "Grace Hopper", "Hank Pym", "Ivy Pepper"],
            "job_role": ["Lead Data Scientist", "Sr Research Scientist", "Software Engineer", "Sr Sales Exec", "Account Manager", "Sales Rep", "HR Director", "Talent Specialist", "HR Generalist"],
            "performance_rating": [4, 4, 4, 4, 4, 3, 4, 4, 3],
            "percent_salary_hike": [18.5, 17.2, 16.0, 19.0, 15.5, 14.0, 17.5, 16.2, 13.8],
            "monthly_income": [12500, 11800, 9200, 10500, 8400, 6700, 9800, 7500, 5900]
        })

        dept_filter = st.selectbox("Filter by Department:", ["All"] + list(top_performers_df["department_name"].unique()))
        
        filtered_df = top_performers_df if dept_filter == "All" else top_performers_df[top_performers_df["department_name"] == dept_filter]

        # Horizontal Bar Chart visualizing top ranks
        fig_rank = px.bar(
            filtered_df,
            x="percent_salary_hike",
            y="full_name",
            color="department_name",
            text="dept_rank",
            orientation="h",
            title="Top Performers & Salary Hike Percentage",
            labels={"percent_salary_hike": "Salary Hike (%)", "full_name": "Employee Name", "dept_rank": "Dept Rank"}
        )
        fig_rank.update_traces(texttemplate='Rank #%{text}', textposition='outside')
        st.plotly_chart(fig_rank, use_container_width=True)

        # Tabular Display mimicking direct SQL query results
        st.markdown("##### Direct Query Result (Window Function Output)")
        st.dataframe(filtered_df, use_container_width=True)

    # ---------------------------------------------------------
    # TAB 3: SATISFACTION & BOTTLENECK ANALYSIS
    # ---------------------------------------------------------
    with tab_satisfaction:
        st.subheader("Departmental Satisfaction & Work Environment Analysis")
        st.caption("Source: Fact_PerformanceReviews JOIN Dim_Department JOIN Dim_Project")

        # Mocking Fact Table Aggregations
        satisfaction_df = pd.DataFrame({
            "department_name": ["Sales", "R&D", "HR", "Marketing", "Finance"],
            "environment_satisfaction": [2.8, 3.6, 3.2, 3.4, 3.1],
            "job_satisfaction": [2.9, 3.7, 3.0, 3.5, 3.3],
            "relationship_satisfaction": [3.1, 3.4, 3.8, 3.2, 3.0],
            "job_involvement": [3.2, 3.8, 3.1, 3.3, 3.4]
        })

        # Multi-bar Chart comparing satisfaction dimensions
        fig_sat = go.Figure()
        fig_sat.add_trace(go.Bar(x=satisfaction_df["department_name"], y=satisfaction_df["environment_satisfaction"], name="Env Satisfaction"))
        fig_sat.add_trace(go.Bar(x=satisfaction_df["department_name"], y=satisfaction_df["job_satisfaction"], name="Job Satisfaction"))
        fig_sat.add_trace(go.Bar(x=satisfaction_df["department_name"], y=satisfaction_df["relationship_satisfaction"], name="Rel Satisfaction"))
        fig_sat.add_trace(go.Bar(x=satisfaction_df["department_name"], y=satisfaction_df["job_involvement"], name="Job Involvement"))
        
        fig_sat.update_layout(
            title="Average Satisfaction Scores Across Dimensions (Scale 1-4)",
            barmode="group",
            xaxis_title="Department",
            yaxis_title="Avg Score",
            yaxis=dict(range=[1, 4])
        )
        
        st.plotly_chart(fig_sat, use_container_width=True)
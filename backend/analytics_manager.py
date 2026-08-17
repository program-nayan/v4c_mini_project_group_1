from backend.db_manager import DatabaseConnection
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_OLTP_NAME, DB_OLAP_NAME


class AnalyticsManager:
    """Handles reporting queries against OLAP (with attrition fallback to OLTP)."""

    def __init__(self, host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
                 oltp_database=DB_OLTP_NAME, olap_database=DB_OLAP_NAME):
        self.oltp_db = DatabaseConnection(database=oltp_database, host=host, user=user, password=password)
        self.olap_db = DatabaseConnection(database=olap_database, host=host, user=user, password=password)

    def get_combined_kpis(self):
        """Fetches summary metrics from Dim_Employee and Fact_PerformanceReviews."""
        emp_stats = self.olap_db.execute_query("""
            SELECT 
                COUNT(*) AS active_count,
                ROUND(AVG(monthly_income), 2) AS avg_income
            FROM Dim_Employee 
            WHERE is_current = 1
        """)
        
        fact_stats = self.olap_db.execute_query("""
            SELECT 
                ROUND(AVG(performance_rating), 2) AS avg_rating,
                ROUND(AVG(job_satisfaction), 2) AS avg_satisfaction
            FROM Fact_PerformanceReviews
        """)
        
        return {
            "active_count": emp_stats[0]["active_count"] if emp_stats and emp_stats[0]["active_count"] else 0,
            "avg_income": float(emp_stats[0]["avg_income"]) if emp_stats and emp_stats[0]["avg_income"] else 0.0,
            "avg_rating": float(fact_stats[0]["avg_rating"]) if fact_stats and fact_stats[0]["avg_rating"] else 0.0,
            "avg_satisfaction": float(fact_stats[0]["avg_satisfaction"]) if fact_stats and fact_stats[0]["avg_satisfaction"] else 0.0,
        }

    def attrition_rate_by_department(self):
        """Reads from OLTP because Dim_Employee does not currently store attrition."""
        query = """
            SELECT d.department_name,
                   ROUND(100.0 * SUM(CASE WHEN e.attrition = 'Yes' THEN 1 ELSE 0 END)
                         / COUNT(*), 2) AS attrition_rate_pct
            FROM EMPLOYEES e
            JOIN DEPARTMENTS d ON e.department_id = d.department_id
            GROUP BY d.department_name
        """
        return self.oltp_db.execute_query(query)

    def avg_income_by_role(self):
        """Calculates average monthly income per role directly from Dim_Employee."""
        query = """
            SELECT 
                e.job_role, 
                ROUND(AVG(e.monthly_income), 2) AS avg_income
            FROM Dim_Employee e
            WHERE e.is_current = 1
            GROUP BY e.job_role
            ORDER BY avg_income DESC
        """
        return self.olap_db.execute_query(query)

    def attrition_risk_flags(self, low_satisfaction_threshold=2):
        """Identifies low satisfaction reviews directly from OLAP Star Schema."""
        query = """
            SELECT 
                e.employee_id, 
                d.department_name, 
                e.job_role,
                f.job_satisfaction, 
                dt.full_date AS review_date
            FROM Fact_PerformanceReviews f
            JOIN Dim_Employee e ON f.emp_key = e.emp_key
            JOIN Dim_Department d ON f.dept_key = d.dept_key
            JOIN Dim_Date dt ON f.review_date_key = dt.date_key
            WHERE f.job_satisfaction <= %s AND e.is_current = 1
            ORDER BY f.job_satisfaction ASC, dt.full_date DESC
            LIMIT 50
        """
        return self.olap_db.execute_query(query, (low_satisfaction_threshold,))

    def top_performers_by_department(self, top_n=5):
        """Fetches top N individual employees per department using ROW_NUMBER tie-breakers."""
        query = """
            SELECT department_name, full_name, employee_id, performance_rating, percent_salary_hike, rnk FROM (
                SELECT 
                    d.department_name,
                    e.full_name,
                    e.employee_id, 
                    f.performance_rating,
                    f.percent_salary_hike,
                    ROW_NUMBER() OVER (
                        PARTITION BY d.department_name 
                        ORDER BY f.performance_rating DESC, f.percent_salary_hike DESC, f.monthly_income DESC
                    ) AS rnk
                FROM Fact_PerformanceReviews f
                JOIN Dim_Department d ON f.dept_key = d.dept_key
                JOIN Dim_Employee e ON f.emp_key = e.emp_key
                WHERE e.is_current = 1
            ) ranked
            WHERE rnk <= %s
            ORDER BY department_name, rnk ASC
        """
        return self.olap_db.execute_query(query, (top_n,))

    def count_active_dim_employees(self):
        rows = self.olap_db.execute_query(
            "SELECT COUNT(*) AS active_count FROM Dim_Employee WHERE is_current = 1"
        )
        return rows[0]["active_count"] if rows else 0

    def avg_performance_rating(self):
        rows = self.olap_db.execute_query(
            "SELECT ROUND(AVG(performance_rating), 2) AS avg_rating FROM Fact_PerformanceReviews"
        )
        return float(rows[0]["avg_rating"]) if rows and rows[0]["avg_rating"] else 0.0

    def avg_monthly_income_current(self):
        rows = self.olap_db.execute_query(
            "SELECT ROUND(AVG(monthly_income), 2) AS avg_income FROM Dim_Employee WHERE is_current = 1"
        )
        return float(rows[0]["avg_income"]) if rows and rows[0]["avg_income"] else 0.0

    def avg_job_satisfaction(self):
        rows = self.olap_db.execute_query(
            "SELECT ROUND(AVG(job_satisfaction), 2) AS avg_satisfaction FROM Fact_PerformanceReviews"
        )
        return float(rows[0]["avg_satisfaction"]) if rows and rows[0]["avg_satisfaction"] else 0.0
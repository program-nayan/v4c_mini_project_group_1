from db_manager import DatabaseConnection
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_OLTP_NAME, DB_OLAP_NAME


class AnalyticsManager:
    def __init__(self, host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
                 oltp_database=DB_OLTP_NAME, olap_database=DB_OLAP_NAME):
        self.oltp_db = DatabaseConnection(database=oltp_database, host=host, user=user, password=password)
        self.olap_db = DatabaseConnection(database=olap_database, host=host, user=user, password=password)

    def attrition_rate_by_department(self):
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
        query = """
            SELECT j.job_role, ROUND(AVG(e.monthly_income), 2) AS avg_income
            FROM EMPLOYEES e
            JOIN JOBS j ON e.job_id = j.job_id
            GROUP BY j.job_role
        """
        return self.oltp_db.execute_query(query)

    def attrition_risk_flags(self, low_satisfaction_threshold=2):
        query = """
            SELECT e.employee_id, d.department_name, j.job_role,
                   pr.job_satisfaction, pr.review_date
            FROM EMPLOYEES e
            JOIN DEPARTMENTS d ON e.department_id = d.department_id
            JOIN JOBS j ON e.job_id = j.job_id
            JOIN PERFORMANCE_REVIEWS pr ON pr.employee_id = e.employee_id
            WHERE pr.job_satisfaction <= %s
              AND pr.review_date = (
                  SELECT MAX(pr2.review_date) FROM PERFORMANCE_REVIEWS pr2
                  WHERE pr2.employee_id = e.employee_id
              )
        """
        return self.oltp_db.execute_query(query, (low_satisfaction_threshold,))

    def top_performers_by_department(self, top_n=3):
        query = """
            SELECT department_name, employee_id, performance_rating FROM (
                SELECT d.department_name, e.employee_id, f.performance_rating,
                       DENSE_RANK() OVER (
                           PARTITION BY d.department_name ORDER BY f.performance_rating DESC
                       ) AS rnk
                FROM Fact_PerformanceReviews f
                JOIN Dim_Department d ON f.dept_key = d.dept_key
                JOIN Dim_Employee e ON f.emp_key = e.emp_key
            ) ranked
            WHERE rnk <= %s
        """
        return self.olap_db.execute_query(query, (top_n,))

    def count_active_dim_employees(self):
        rows = self.olap_db.execute_query(
            "SELECT COUNT(*) AS active_count FROM Dim_Employee WHERE is_current = 1"
        )
        return rows[0]["active_count"]

    def avg_performance_rating(self):
        rows = self.olap_db.execute_query(
            "SELECT ROUND(AVG(performance_rating), 2) AS avg_rating FROM Fact_PerformanceReviews"
        )
        return rows[0]["avg_rating"]

    def avg_monthly_income_current(self):
        rows = self.olap_db.execute_query(
            "SELECT ROUND(AVG(monthly_income), 2) AS avg_income FROM Dim_Employee WHERE is_current = 1"
        )
        return rows[0]["avg_income"]

    def avg_job_satisfaction(self):
        rows = self.olap_db.execute_query(
            "SELECT ROUND(AVG(job_satisfaction), 2) AS avg_satisfaction FROM Fact_PerformanceReviews"
        )
        return rows[0]["avg_satisfaction"]
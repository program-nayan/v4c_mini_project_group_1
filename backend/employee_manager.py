from db_manager import DatabaseConnection
from entities import Employee
from exceptions import RecordNotFoundError
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_OLTP_NAME

_EMPLOYEE_SELECT = """
    SELECT e.employee_id, e.first_name, e.last_name, e.email,
           e.monthly_income, e.attrition, e.hire_date,
           d.department_name, j.job_role
    FROM EMPLOYEES e
    JOIN DEPARTMENTS d ON e.department_id = d.department_id
    JOIN JOBS j ON e.job_id = j.job_id
"""


class EmployeeManager:
    def __init__(self, host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_OLTP_NAME):
        self.db = DatabaseConnection(database=database, host=host, user=user, password=password)

    def get_employee(self, employee_id):
        rows = self.db.execute_query(_EMPLOYEE_SELECT + " WHERE e.employee_id = %s", (employee_id,))
        return self._row_to_employee(rows[0]) if rows else None

    def list_employees(self, department_name=None):
        if department_name:
            rows = self.db.execute_query(_EMPLOYEE_SELECT + " WHERE d.department_name = %s", (department_name,))
        else:
            rows = self.db.execute_query(_EMPLOYEE_SELECT)
        return [self._row_to_employee(r) for r in rows]

    def list_departments(self):
        return self.db.execute_query("SELECT department_id, department_name FROM DEPARTMENTS")

    def list_jobs(self):
        return self.db.execute_query("SELECT job_id, job_role, job_level FROM JOBS")

    def _next_employee_id(self):
        rows = self.db.execute_query("SELECT MAX(employee_id) AS max_id FROM EMPLOYEES")
        return (rows[0]["max_id"] or 0) + 1

    def onboard_employee(self, first_name, last_name, email, department_id, job_id,
                         monthly_income, hire_date, phone_number=None, age=None,
                         gender=None, marital_status=None, education=None,
                         education_field=None, manager_id=None, distance_from_home=None,
                         total_working_years=None):
        new_id = self._next_employee_id()
        self.db.execute_query(
            "INSERT INTO EMPLOYEES (employee_id, first_name, last_name, email, "
            "phone_number, age, gender, marital_status, education, education_field, "
            "hire_date, department_id, job_id, manager_id, monthly_income, "
            "distance_from_home, total_working_years, attrition) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'No')",
            (new_id, first_name, last_name, email, phone_number, age, gender,
             marital_status, education, education_field, hire_date, department_id,
             job_id, manager_id, monthly_income, distance_from_home, total_working_years),
            fetch=False
        )
        return self.get_employee(new_id)

    def assign_to_project(self, employee_id: int, project_id: int, role: str, allocation: int):
        """Assigns an employee to a project in the OLTP database."""
        emp_check = self.db.execute_query("SELECT employee_id FROM EMPLOYEES WHERE employee_id = %s", (employee_id,))
        if not emp_check:
            raise RecordNotFoundError(f"Employee ID {employee_id} does not exist.")

        # Updated column name to 'role_in_project' matching ERD schema
        query = """
            INSERT INTO PROJECT_ASSIGNMENTS (employee_id, project_id, role_in_project, allocation_percentage, assigned_date)
            VALUES (%s, %s, %s, %s, CURDATE())
            ON DUPLICATE KEY UPDATE 
                role_in_project = VALUES(role_in_project), 
                allocation_percentage = VALUES(allocation_percentage);
        """
        self.db.execute_query(query, (employee_id, project_id, role, allocation), fetch=False)
        return True

    def update_employee_role(self, employee_id: int, new_department_id: int, new_job_id: int, new_monthly_income: float):
        """Updates employee in OLTP and executes the SCD Type 2 stored procedure in OLAP."""
        emp_check = self.db.execute_query("SELECT employee_id FROM EMPLOYEES WHERE employee_id = %s", (employee_id,))
        if not emp_check:
            raise RecordNotFoundError(f"Employee ID {employee_id} does not exist.")

        # Update OLTP Record
        self.db.execute_query(
            "UPDATE EMPLOYEES SET department_id = %s, job_id = %s, monthly_income = %s WHERE employee_id = %s",
            (new_department_id, new_job_id, new_monthly_income, employee_id),
            fetch=False
        )

        # Lookup Job Role & Level text for OLAP SCD2 procedure
        job_info = self.db.execute_query("SELECT job_role, job_level FROM JOBS WHERE job_id = %s", (new_job_id,))
        job_role = job_info[0]["job_role"] if job_info else "Updated Role"
        job_level = job_info[0]["job_level"] if job_info else 1

        # Trigger SCD Type 2 tracking in OLAP Data Warehouse with all 6 required parameters
        try:
            self.db.execute_query(
                "CALL hr_olap_db.sp_UpdateEmployeeSCD2(%s, %s, %s, %s, %s, %s)",
                (employee_id, new_department_id, job_role, job_level, new_monthly_income, "Department/Role Update"),
                fetch=False
            )
        except Exception as e:
            print(f"SCD2 Stored Procedure Execution Notice: {e}")

        return True

    def submit_performance_review(self, employee_id: int, rating: int):
        """Logs review into OLTP and syncs to OLAP Fact_PerformanceReviews table."""
        emp_rows = self.db.execute_query("SELECT employee_id, department_id FROM EMPLOYEES WHERE employee_id = %s", (employee_id,))
        if not emp_rows:
            raise RecordNotFoundError(f"Employee ID {employee_id} does not exist.")

        dept_id = emp_rows[0]["department_id"]

        # Insert into OLTP
        self.db.execute_query(
            "INSERT INTO PERFORMANCE_REVIEWS (employee_id, review_date, performance_rating) VALUES (%s, CURDATE(), %s)",
            (employee_id, rating),
            fetch=False
        )

        # Sync to OLAP Fact table
        olap_query = """
            INSERT INTO hr_olap_db.Fact_PerformanceReviews (emp_key, dept_key, review_date_key, performance_rating)
            SELECT e.emp_key, d.dept_key, DATE_FORMAT(CURDATE(), '%%Y%%m%%d'), %s
            FROM hr_olap_db.Dim_Employee e
            JOIN hr_olap_db.Dim_Department d ON d.department_id = %s
            WHERE e.employee_id = %s AND e.is_current = 1
            LIMIT 1
        """
        try:
            self.db.execute_query(olap_query, (rating, dept_id, employee_id), fetch=False)
        except Exception as e:
            print(f"OLAP Sync Notice: {e}")

        return True

    def give_raise(self, employee_id, percent):
        emp = self.get_employee(employee_id)
        if emp is None:
            raise RecordNotFoundError(f"No employee with id {employee_id}")
        emp.give_raise(percent)
        self.db.execute_query(
            "UPDATE EMPLOYEES SET monthly_income = %s WHERE employee_id = %s",
            (emp.monthly_income, employee_id),
            fetch=False
        )
        return emp

    def _row_to_employee(self, row):
        return Employee(
            employee_id=row["employee_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            department=row["department_name"],
            job_role=row["job_role"],
            monthly_income=row["monthly_income"],
            email=row.get("email"),
            hire_date=row.get("hire_date"),
            attrition=row.get("attrition", "No"),
        )
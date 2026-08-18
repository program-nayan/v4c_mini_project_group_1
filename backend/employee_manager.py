try:
    from backend.logger import get_logger
    from backend.db_manager import DatabaseConnection
    from backend.entities import Employee
    from backend.exceptions import RecordNotFoundError
    from backend.config import DB_HOST, DB_USER, DB_PASSWORD, DB_OLTP_NAME
except ImportError:
    from logger import get_logger
    from db_manager import DatabaseConnection
    from entities import Employee
    from exceptions import RecordNotFoundError
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_OLTP_NAME

logger = get_logger(__name__)

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
        logger.info("Initializing EmployeeManager with database: %s on %s", database, host)
        self.db = DatabaseConnection(database=database, host=host, user=user, password=password)

    def get_employee(self, employee_id):
        logger.debug("Fetching employee details for ID: %s", employee_id)
        rows = self.db.execute_query(_EMPLOYEE_SELECT + " WHERE e.employee_id = %s", (employee_id,))
        if not rows:
            logger.debug("No employee found with ID: %s", employee_id)
            return None
        return self._row_to_employee(rows[0])

    def list_employees(self, department_name=None):
        logger.debug("Listing employees (filter department: %s)", department_name)
        if department_name:
            rows = self.db.execute_query(_EMPLOYEE_SELECT + " WHERE d.department_name = %s", (department_name,))
        else:
            rows = self.db.execute_query(_EMPLOYEE_SELECT)
        logger.debug("Retrieved %d employee records", len(rows))
        return [self._row_to_employee(r) for r in rows]

    def list_departments(self):
        logger.debug("Fetching department list")
        return self.db.execute_query("SELECT department_id, department_name FROM DEPARTMENTS")

    def list_jobs(self):
        logger.debug("Fetching job roles list")
        return self.db.execute_query("SELECT job_id, job_role, job_level FROM JOBS")

    def _next_employee_id(self):
        rows = self.db.execute_query("SELECT MAX(employee_id) AS max_id FROM EMPLOYEES")
        next_id = (rows[0]["max_id"] or 0) + 1
        logger.debug("Computed next available employee_id: %s", next_id)
        return next_id

    def onboard_employee(self, first_name, last_name, email, department_id, job_id,
                         monthly_income, hire_date, phone_number=None, age=None,
                         gender=None, marital_status=None, education=None,
                         education_field=None, manager_id=None, distance_from_home=None,
                         total_working_years=None):
        new_id = self._next_employee_id()
        logger.info(
            "Onboarding new employee: %s %s (ID: %s, Dept: %s, Job: %s, Income: $%s)",
            first_name,
            last_name,
            new_id,
            department_id,
            job_id,
            monthly_income,
        )
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
        logger.info("Successfully persisted employee record for ID: %s", new_id)

        # Look up job role/level text for the OLAP dimension row
        job_info = self.db.execute_query("SELECT job_role, job_level FROM JOBS WHERE job_id = %s", (job_id,))
        job_role = job_info[0]["job_role"] if job_info else "Unassigned"
        job_level = job_info[0]["job_level"] if job_info else 1

        # Seed the initial SCD Type 2 record in OLAP so new hires show up on the dashboard
        try:
            logger.info("Inserting initial Dim_Employee SCD2 record for Employee ID %s in OLAP", new_id)
            self.db.execute_query(
                "INSERT INTO hr_olap_db.Dim_Employee ("
                "  employee_id, full_name, email, job_role, job_level, monthly_income,"
                "  department_id, hire_date, effective_start_date, effective_end_date,"
                "  is_current, change_reason, attrition"
                ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'9999-12-31',1,%s,'No')",
                (new_id, f"{first_name} {last_name}", email, job_role, job_level,
                 monthly_income, department_id, hire_date, hire_date, "New Hire"),
                fetch=False
            )
            logger.info("Successfully inserted OLAP Dim_Employee record for Employee ID %s", new_id)
        except Exception as e:
            logger.warning("OLAP Dim_Employee insert failed for Employee ID %s: %s", new_id, e)

        return self.get_employee(new_id)

    def assign_to_project(self, employee_id: int, project_id: int, role: str, allocation: int):
        """Assigns an employee to a project in the OLTP database."""
        logger.info(
            "Assigning Employee ID %s to Project ID %s (Role: %s, Allocation: %s%%)",
            employee_id,
            project_id,
            role,
            allocation,
        )
        emp_check = self.db.execute_query("SELECT employee_id FROM EMPLOYEES WHERE employee_id = %s", (employee_id,))
        if not emp_check:
            logger.warning("Project assignment failed: Employee ID %s does not exist", employee_id)
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
        logger.info("Successfully assigned Employee ID %s to Project ID %s", employee_id, project_id)
        return True

    def update_employee_role(self, employee_id: int, new_department_id: int, new_job_id: int, new_monthly_income: float):
        """Updates employee in OLTP and executes the SCD Type 2 stored procedure in OLAP."""
        logger.info(
            "Updating Employee ID %s: Dept=%s, Job=%s, MonthlyIncome=$%s",
            employee_id,
            new_department_id,
            new_job_id,
            new_monthly_income,
        )
        emp_check = self.db.execute_query("SELECT employee_id FROM EMPLOYEES WHERE employee_id = %s", (employee_id,))
        if not emp_check:
            logger.warning("Employee update failed: Employee ID %s does not exist", employee_id)
            raise RecordNotFoundError(f"Employee ID {employee_id} does not exist.")

        # Update OLTP Record
        self.db.execute_query(
            "UPDATE EMPLOYEES SET department_id = %s, job_id = %s, monthly_income = %s WHERE employee_id = %s",
            (new_department_id, new_job_id, new_monthly_income, employee_id),
            fetch=False
        )
        logger.info("Updated OLTP record for Employee ID: %s", employee_id)

        # Lookup Job Role & Level text for OLAP SCD2 procedure
        job_info = self.db.execute_query("SELECT job_role, job_level FROM JOBS WHERE job_id = %s", (new_job_id,))
        job_role = job_info[0]["job_role"] if job_info else "Updated Role"
        job_level = job_info[0]["job_level"] if job_info else 1

        # Current attrition flag carries forward into the new SCD2 version
        attrition_info = self.db.execute_query("SELECT attrition FROM EMPLOYEES WHERE employee_id = %s", (employee_id,))
        attrition = attrition_info[0]["attrition"] if attrition_info else "No"

        # Trigger SCD Type 2 tracking in OLAP Data Warehouse with all 7 required parameters
        try:
            logger.info("Triggering SCD Type 2 stored procedure for Employee ID %s in OLAP", employee_id)
            self.db.execute_query(
                "CALL hr_olap_db.sp_UpdateEmployeeSCD2(%s, %s, %s, %s, %s, %s, %s)",
                (employee_id, new_department_id, job_role, job_level, new_monthly_income,
                 "Department/Role Update", attrition),
                fetch=False
            )
            logger.info("SCD Type 2 stored procedure completed for Employee ID %s", employee_id)
        except Exception as e:
            logger.warning("SCD2 Stored Procedure Execution Notice for Employee ID %s: %s", employee_id, e)

        return True

    def submit_performance_review(self, employee_id: int, rating: int):
        """Logs review into OLTP and syncs to OLAP Fact_PerformanceReviews table."""
        logger.info("Submitting performance review for Employee ID %s with rating %s/4", employee_id, rating)
        emp_rows = self.db.execute_query("SELECT employee_id, department_id FROM EMPLOYEES WHERE employee_id = %s", (employee_id,))
        if not emp_rows:
            logger.warning("Performance review submission failed: Employee ID %s does not exist", employee_id)
            raise RecordNotFoundError(f"Employee ID {employee_id} does not exist.")

        dept_id = emp_rows[0]["department_id"]

        # Insert into OLTP
        self.db.execute_query(
            "INSERT INTO PERFORMANCE_REVIEWS (employee_id, review_date, performance_rating) VALUES (%s, CURDATE(), %s)",
            (employee_id, rating),
            fetch=False
        )
        logger.info("Logged performance review into OLTP for Employee ID %s", employee_id)

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
            logger.info("Syncing performance review to OLAP Fact_PerformanceReviews for Employee ID %s", employee_id)
            self.db.execute_query(olap_query, (rating, dept_id, employee_id), fetch=False)
            logger.info("Successfully synced performance review to OLAP Fact table for Employee ID %s", employee_id)
        except Exception as e:
            logger.warning("OLAP Sync Notice for Employee ID %s: %s", employee_id, e)

        return True

    def give_raise(self, employee_id, percent):
        logger.info("Processing raise of %s%% for Employee ID: %s", percent, employee_id)
        emp = self.get_employee(employee_id)
        if emp is None:
            logger.warning("Give raise failed: No employee with ID %s", employee_id)
            raise RecordNotFoundError(f"No employee with id {employee_id}")
        emp.give_raise(percent)
        self.db.execute_query(
            "UPDATE EMPLOYEES SET monthly_income = %s WHERE employee_id = %s",
            (emp.monthly_income, employee_id),
            fetch=False
        )
        logger.info("Persisted salary raise for Employee ID %s (New Income: $%s)", employee_id, emp.monthly_income)
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
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

    def update_employee_role(self, employee_id, new_department_id, new_job_id, new_monthly_income):
        affected = self.db.execute_query(
            "UPDATE EMPLOYEES SET department_id = %s, job_id = %s, monthly_income = %s WHERE employee_id = %s",
            (new_department_id, new_job_id, new_monthly_income, employee_id),
            fetch=False
        )
        if affected == 0:
            raise RecordNotFoundError(f"No employee with id {employee_id}")
        return True

    def give_raise(self, employee_id, percent):
        emp = self.get_employee(employee_id)
        if emp is None:
            raise RecordNotFoundError(f"No employee with id {employee_id}")
        emp.give_raise(percent)
        self.db.execute_query(
            "UPDATE EMPLOYEES SET monthly_income = %s WHERE employee_id = %s",
            (emp.monthly_income, employee_id), fetch=False
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
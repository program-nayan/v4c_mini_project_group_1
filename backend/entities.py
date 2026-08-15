from exceptions import ValidationError


class Employee:
    def __init__(self, employee_id, first_name, last_name, department, job_role,
                 monthly_income, email=None, hire_date=None, attrition="No"):
        self.employee_id = employee_id
        self.first_name = first_name
        self.last_name = last_name
        self.department = department
        self.job_role = job_role
        self._monthly_income = monthly_income
        self.email = email
        self.hire_date = hire_date
        self.attrition = attrition

    @property
    def monthly_income(self):
        return self._monthly_income

    @monthly_income.setter
    def monthly_income(self, value):
        if value < 0:
            raise ValidationError("monthly_income cannot be negative")
        self._monthly_income = value

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def give_raise(self, percent):
        if percent <= 0:
            raise ValidationError("percent must be positive")
        self.monthly_income = round(self.monthly_income * (1 + percent / 100), 2)

    def __repr__(self):
        return f"<Employee {self.employee_id} {self.full_name} ({self.department})>"


class Project:
    def __init__(self, project_id, name, department, start_date=None, end_date=None, budget=None):
        self.project_id = project_id
        self.name = name
        self.department = department
        self.start_date = start_date
        self.end_date = end_date
        self.budget = budget

    def __repr__(self):
        return f"<Project {self.project_id} {self.name}>"


class Review:
    def __init__(self, review_id, employee_id, review_date, performance_rating,
                 job_satisfaction, environment_satisfaction):
        self.review_id = review_id
        self.employee_id = employee_id
        self.review_date = review_date
        self.performance_rating = performance_rating
        self.job_satisfaction = job_satisfaction
        self.environment_satisfaction = environment_satisfaction

    @property
    def performance_rating(self):
        return self._performance_rating

    @performance_rating.setter
    def performance_rating(self, value):
        if not (1 <= value <= 4):
            raise ValidationError("performance_rating must be between 1 and 4")
        self._performance_rating = value

    def is_top_performer(self):
        return self.performance_rating >= 4

    def __repr__(self):
        return f"<Review emp={self.employee_id} rating={self.performance_rating}>"

import streamlit as st
import datetime
import re
from backend.logger import get_logger
from backend.employee_manager import EmployeeManager
from backend.exceptions import AppError, ValidationError, RecordNotFoundError

logger = get_logger(__name__)

# =========================================================
# RIGOROUS REGEX & VALIDATION PATTERNS
# =========================================================
# Names: Alphabetic, spaces, hyphens, apostrophes ONLY (2-50 chars)
NAME_REGEX = re.compile(r"^[A-Za-z\s\-']{2,50}$")
# Email: Strict structure format checking
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
# Phone: Must allow standard formatting symbols but require digit density
PHONE_REGEX = re.compile(r"^\+?[\d\s\-\(\)\.]{7,20}$")
# Project Role: Words and titles only; no purely numeric inputs
ROLE_REGEX = re.compile(r"^[A-Za-z\s\-\._']{2,50}$")


def validate_name(name_str: str, field_name: str) -> list[str]:
    """Strictly validates first and last human names."""
    errors = []
    if not name_str or not name_str.strip():
        errors.append(f"**{field_name}** is required.")
        return errors
        
    cleaned = name_str.strip()
    
    # 1. Explicit Number Check
    if any(char.isdigit() for char in cleaned):
        errors.append(f"**{field_name}** cannot contain numbers or digits.")
        
    # 2. Allowed Characters Check
    if not NAME_REGEX.match(cleaned):
        errors.append(f"**{field_name}** can only contain letters, spaces, hyphens, and apostrophes (2–50 characters).")
        
    # 3. Repetitive Sequence Check
    if len(set(cleaned.lower().replace(" ", ""))) <= 1:
        errors.append(f"**{field_name}** cannot consist of a single repeated character.")
        
    return errors


def validate_phone(phone_str: str) -> list[str]:
    """Validates phone number density and format."""
    errors = []
    if not phone_str or not phone_str.strip():
        return errors  # Phone is optional
        
    cleaned = phone_str.strip()
    digits = [c for c in cleaned if c.isdigit()]
    
    if len(digits) < 7:
        errors.append("Phone number must contain at least 7 numeric digits.")
        
    if any(c.isalpha() for c in cleaned):
        errors.append("Phone number cannot contain letters.")
        
    if not PHONE_REGEX.match(cleaned):
        errors.append("Phone number format is invalid (allowed: digits, spaces, +, -, parentheses).")
        
    return errors


def validate_onboard_data(first_name, last_name, email, phone_number, age, 
                         hire_date, total_working_years, manager_id, monthly_income) -> list[str]:
    """Consolidated input validation suite for onboarding."""
    errors = []
    
    # 1. Name Checks
    errors.extend(validate_name(first_name, "First Name"))
    errors.extend(validate_name(last_name, "Last Name"))
    
    # 2. Email Validation
    if not email or not email.strip():
        errors.append("**Email** is required.")
    elif " " in email.strip():
        errors.append("Email address cannot contain spaces.")
    elif not EMAIL_REGEX.match(email.strip()):
        errors.append("Please enter a valid email address (e.g., `jane.doe@company.com`).")
        
    # 3. Phone Validation
    errors.extend(validate_phone(phone_number))
    
    # 4. Age & Work Timeline Realism Checks
    if age < 18 or age > 75:
        errors.append("Age must be between 18 and 75 years.")
        
    today = datetime.date.today()
    if hire_date > today:
        errors.append("Hire date cannot be set in the future.")
        
    min_hire_age = 16
    estimated_birth_year = today.year - age
    earliest_allowed_hire_year = estimated_birth_year + min_hire_age
    if hire_date.year < earliest_allowed_hire_year:
        errors.append(f"Hire date ({hire_date.year}) implies employee was hired before age {min_hire_age} (Age: {age}).")
        
    max_possible_work_years = max(0, age - min_hire_age)
    if total_working_years > max_possible_work_years:
        errors.append(
            f"Total working years ({total_working_years}) exceeds maximum possible career span "
            f"for age {age} (max allowed: {max_possible_work_years} years)."
        )
        
    # 5. Financial & Manager ID Checks
    if monthly_income < 1000.0 or monthly_income > 500000.0:
        errors.append("Monthly Income must be between $1,000.00 and $500,000.00.")
        
    if manager_id <= 0:
        errors.append("Manager ID must be a positive integer.")
        
    return errors


def render_operational_forms():
    """Renders OLTP forms backed by the EmployeeManager OOP layer with strict input validation."""
    logger.info("Rendering OLTP Operational Management forms")
    
    # Initialize backend manager safely
    try:
        emp_manager = EmployeeManager()
        dept_data = emp_manager.list_departments()
        job_data = emp_manager.list_jobs()
        
        dept_options = {d['department_id']: f"{d['department_id']} - {d['department_name']}" for d in dept_data} if dept_data else {1: "1 - Sales", 2: "2 - R&D", 3: "3 - HR"}
        job_options = {j['job_id']: f"{j['job_id']} - {j['job_role']} (Level {j['job_level']})" for j in job_data} if job_data else {1: "1 - Software Engineer"}
        db_connected = True
        logger.info("Successfully populated department (%d) and job (%d) options from database", len(dept_options), len(job_options))
    except Exception as e:
        logger.error("Failed to initialize EmployeeManager for forms (fallback to defaults): %s", e, exc_info=True)
        st.warning(f"⚠️ Database offline or unreachable. Form dropdowns running in offline mode: {e}")
        dept_options = {1: "1 - Sales", 2: "2 - Research & Development", 3: "3 - Human Resources"}
        job_options = {1: "1 - Sales Executive", 2: "2 - Research Scientist", 3: "3 - HR Specialist"}
        db_connected = False

    tab_onboard, tab_project, tab_scd2, tab_review = st.tabs([
        "👤 Onboard Employee", 
        "📁 Project Assignment", 
        "🔄 Department/Role Update (SCD2)", 
        "⭐ Performance Review"
    ])

    # ---------------------------------------------------------
    # TAB 1: ONBOARD EMPLOYEE
    # ---------------------------------------------------------
    with tab_onboard:
        st.subheader("Onboard New Employee")
        st.caption("Inserts a live operational record into EMPLOYEES via EmployeeManager")
        
        with st.form("onboard_employee_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            first_name = col1.text_input("First Name*", placeholder="e.g. Jane")
            last_name = col2.text_input("Last Name*", placeholder="e.g. Doe")
            
            email = col1.text_input("Email*", placeholder="j.doe@company.com")
            phone_number = col2.text_input("Phone Number", placeholder="555-0199")
            
            col3, col4, col5 = st.columns(3)
            age = col3.number_input("Age*", min_value=18, max_value=75, value=28)
            gender = col4.selectbox("Gender", ["Male", "Female", "Non-Binary"])
            marital_status = col5.selectbox("Marital Status", ["Single", "Married", "Divorced"])
            
            col6, col7 = st.columns(2)
            education_field = col6.selectbox("Education Field", ["Life Sciences", "Medical", "Marketing", "Technical Degree", "Human Resources", "Other"])
            hire_date = col7.date_input("Hire Date*", value=datetime.date.today())
            
            col8, col9, col10 = st.columns(3)
            department_id = col8.selectbox("Department*", options=list(dept_options.keys()), format_func=lambda x: dept_options[x])
            job_id = col9.selectbox("Job Role*", options=list(job_options.keys()), format_func=lambda x: job_options[x])
            manager_id = col10.number_input("Manager ID*", min_value=1, value=1, step=1)
            
            col11, col12 = st.columns(2)
            monthly_income = col11.number_input("Monthly Income ($)*", min_value=1000.0, max_value=500000.0, value=6500.0, step=100.0)
            total_working_years = col12.number_input("Total Working Years*", min_value=0, max_value=60, value=3)
            
            submitted = st.form_submit_button("Submit New Employee")
            
            if submitted:
                logger.info("Onboard form submitted for: %s %s (%s)", first_name, last_name, email)
                
                # Execute Validation Suite
                validation_errors = validate_onboard_data(
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone_number=phone_number,
                    age=int(age),
                    hire_date=hire_date,
                    total_working_years=int(total_working_years),
                    manager_id=int(manager_id),
                    monthly_income=float(monthly_income)
                )

                if validation_errors:
                    logger.warning("Onboard validation failed: %s", ", ".join(validation_errors))
                    for err in validation_errors:
                        st.error(f"⚠️ {err}")
                elif not db_connected:
                    logger.error("Onboard submission failed: Database is not connected")
                    st.error("Cannot insert record: MySQL database is not connected.")
                else:
                    try:
                        emp = emp_manager.onboard_employee(
                            first_name=first_name.strip(),
                            last_name=last_name.strip(),
                            email=email.strip().lower(),
                            department_id=department_id,
                            job_id=job_id,
                            monthly_income=monthly_income,
                            hire_date=hire_date,
                            phone_number=phone_number.strip() if phone_number else None,
                            age=int(age),
                            gender=gender,
                            marital_status=marital_status,
                            education_field=education_field,
                            manager_id=int(manager_id),
                            total_working_years=int(total_working_years)
                        )
                        logger.info("Successfully onboarded employee: %s (ID: %s)", emp.full_name, emp.employee_id)
                        st.cache_data.clear()
                        st.success(f"✅ Employee **{emp.full_name}** successfully onboarded with ID **{emp.employee_id}**!")
                    except (ValidationError, AppError) as err:
                        logger.error("Onboarding failed with backend error: %s", err)
                        st.error(f"❌ Backend Error: {err}")

    # ---------------------------------------------------------
    # TAB 2: PROJECT ASSIGNMENT
    # ---------------------------------------------------------
    with tab_project:
        st.subheader("Assign Employee to Project")
        with st.form("project_assignment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            employee_id = col1.number_input("Employee ID*", min_value=10001, step=1)
            project_id = col2.number_input("Project ID*", min_value=1, step=1)
            role_in_project = col1.text_input("Role in Project*", value="Contributor")
            allocation_percentage = col2.slider("Allocation (%)*", 10, 100, 100, step=10)
            
            assigned = st.form_submit_button("Assign Project")
            if assigned:
                logger.info("Project assignment form submitted: Employee ID %s -> Project ID %s", employee_id, project_id)
                
                validation_errors = []
                if employee_id < 10001:
                    validation_errors.append("Employee ID must be 10001 or greater.")
                if project_id < 1:
                    validation_errors.append("Project ID must be a positive integer.")
                
                cleaned_role = role_in_project.strip()
                if not cleaned_role or any(c.isdigit() for c in cleaned_role) or not ROLE_REGEX.match(cleaned_role):
                    validation_errors.append("Role in Project must contain letters/title words only (no digits or symbols).")
                    
                if allocation_percentage < 10 or allocation_percentage > 100:
                    validation_errors.append("Allocation percentage must be between 10% and 100%.")

                if validation_errors:
                    logger.warning("Project assignment validation error: %s", ", ".join(validation_errors))
                    for err in validation_errors:
                        st.warning(f"⚠️ {err}")
                else:
                    try:
                        emp_manager.assign_to_project(
                            employee_id=int(employee_id),
                            project_id=int(project_id),
                            role=cleaned_role,
                            allocation=int(allocation_percentage)
                        )
                        logger.info("Successfully assigned Employee %s to Project %s", employee_id, project_id)
                        st.success(
                            f"✅ Successfully assigned Employee ID **{employee_id}** "
                            f"to Project ID **{project_id}** as *{cleaned_role}* ({allocation_percentage}% allocation)!"
                        )
                    except (RecordNotFoundError, ValidationError) as err:
                        logger.warning("Project assignment failed validation: %s", err)
                        st.warning(f"⚠️ Input Validation Error: {err}")
                    except Exception as err:
                        logger.error("Project assignment failed unexpectedly: %s", err, exc_info=True)
                        st.error(f"❌ Failed to assign project: {err}")

    # ---------------------------------------------------------
    # TAB 3: DEPARTMENT / ROLE UPDATE (SCD TYPE 2)
    # ---------------------------------------------------------
    with tab_scd2:
        st.subheader("Update Department / Role (SCD Type 2)")
        st.info("ℹ️ Updates current employee details in OLTP and triggers SCD Type 2 history creation in OLAP.")
        
        with st.form("scd_update_form", clear_on_submit=True):
            emp_id = st.number_input("Target Employee ID*", min_value=10001, step=1)
            
            col1, col2 = st.columns(2)
            new_dept_id = col1.selectbox("New Department*", options=list(dept_options.keys()), format_func=lambda x: dept_options[x])
            new_job_id = col2.selectbox("New Job Role*", options=list(job_options.keys()), format_func=lambda x: job_options[x])
            new_income = st.number_input("Updated Monthly Income ($)*", min_value=1000.0, max_value=500000.0, value=8500.0, step=100.0)
            
            scd_submitted = st.form_submit_button("Apply Role / Income Change")
            
            if scd_submitted:
                logger.info("SCD2 update form submitted for Employee ID: %s", emp_id)
                
                validation_errors = []
                if emp_id < 10001:
                    validation_errors.append("Target Employee ID must be 10001 or greater.")
                if new_income < 1000.0 or new_income > 500000.0:
                    validation_errors.append("Updated Monthly Income must be between $1,000.00 and $500,000.00.")

                if validation_errors:
                    logger.warning("SCD2 validation errors: %s", ", ".join(validation_errors))
                    for err in validation_errors:
                        st.warning(f"⚠️ {err}")
                elif not db_connected:
                    logger.error("SCD2 update failed: Database not connected")
                    st.error("Cannot perform update: Database not connected.")
                else:
                    try:
                        emp_manager.update_employee_role(
                            employee_id=int(emp_id),
                            new_department_id=int(new_dept_id),
                            new_job_id=int(new_job_id),
                            new_monthly_income=float(new_income)
                        )
                        st.cache_data.clear()
                        logger.info("Successfully processed SCD2 role update for Employee ID: %s", emp_id)
                        st.success(f"✅ Successfully updated Employee ID **{emp_id}** role and income!")
                    except RecordNotFoundError as e:
                        logger.warning("Employee record not found for SCD2 update: %s", e)
                        st.warning(f"⚠️ Employee Record Not Found: {e}")
                    except AppError as e:
                        logger.error("SCD2 update failed with AppError: %s", e)
                        st.error(f"❌ Update Error: {e}")

    # ---------------------------------------------------------
    # TAB 4: PERFORMANCE REVIEW
    # ---------------------------------------------------------
    with tab_review:
        st.subheader("Submit Performance Review")
        st.info("ℹ️ Logs employee performance review into OLTP and updates OLAP Fact table.")
        
        with st.form("review_form", clear_on_submit=True):
            rev_emp_id = st.number_input("Employee ID*", min_value=10001, step=1)
            perf_rating = st.slider("Performance Rating (1-4)*", 1, 4, 3)
            
            review_submitted = st.form_submit_button("Submit Review")
            
            if review_submitted:
                logger.info("Performance review form submitted: Employee ID %s -> Rating %s/4", rev_emp_id, perf_rating)
                
                validation_errors = []
                if rev_emp_id < 10001:
                    validation_errors.append("Employee ID must be 10001 or greater.")
                if perf_rating not in [1, 2, 3, 4]:
                    validation_errors.append("Performance Rating must be an integer between 1 and 4.")

                if validation_errors:
                    logger.warning("Review submission validation errors: %s", ", ".join(validation_errors))
                    for err in validation_errors:
                        st.warning(f"⚠️ {err}")
                elif not db_connected:
                    logger.error("Performance review submission failed: Database connection inactive")
                    st.error("Cannot log review: Database connection inactive.")
                else:
                    try:
                        emp_manager.submit_performance_review(
                            employee_id=int(rev_emp_id),
                            rating=int(perf_rating)
                        )
                        st.cache_data.clear()
                        logger.info("Performance review of %s/4 successfully recorded for Employee ID %s", perf_rating, rev_emp_id)
                        st.success(f"✅ Performance review of **{perf_rating}/4** successfully logged for Employee ID **{rev_emp_id}**!")
                    except RecordNotFoundError as e:
                        logger.warning("Performance review submission failed: Employee ID %s not found", rev_emp_id)
                        st.warning(f"⚠️ Employee ID **{rev_emp_id}** not found: {e}")
                    except AppError as e:
                        logger.error("Review submission failed with AppError: %s", e)
                        st.error(f"❌ Review Submission Failed: {e}")
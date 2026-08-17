import streamlit as st
import datetime
from backend.employee_manager import EmployeeManager
from backend.exceptions import AppError, ValidationError, RecordNotFoundError

def render_operational_forms():
    """Renders OLTP forms backed by the EmployeeManager OOP layer."""
    
    # Initialize backend manager safely
    try:
        emp_manager = EmployeeManager()
        dept_data = emp_manager.list_departments()
        job_data = emp_manager.list_jobs()
        
        dept_options = {d['department_id']: f"{d['department_id']} - {d['department_name']}" for d in dept_data} if dept_data else {1: "1 - Sales", 2: "2 - R&D", 3: "3 - HR"}
        job_options = {j['job_id']: f"{j['job_id']} - {j['job_role']} (Level {j['job_level']})" for j in job_data} if job_data else {1: "1 - Software Engineer"}
        db_connected = True
    except Exception as e:
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
            age = col3.number_input("Age", min_value=18, max_value=70, value=28)
            gender = col4.selectbox("Gender", ["Male", "Female", "Non-Binary"])
            marital_status = col5.selectbox("Marital Status", ["Single", "Married", "Divorced"])
            
            col6, col7 = st.columns(2)
            education_field = col6.selectbox("Education Field", ["Life Sciences", "Medical", "Marketing", "Technical Degree", "Human Resources", "Other"])
            hire_date = col7.date_input("Hire Date", value=datetime.date.today())
            
            col8, col9, col10 = st.columns(3)
            department_id = col8.selectbox("Department", options=list(dept_options.keys()), format_func=lambda x: dept_options[x])
            job_id = col9.selectbox("Job Role", options=list(job_options.keys()), format_func=lambda x: job_options[x])
            manager_id = col10.number_input("Manager ID", min_value=1, value=1, step=1)
            
            col11, col12 = st.columns(2)
            monthly_income = col11.number_input("Monthly Income ($)", min_value=1000.0, value=6500.0, step=100.0)
            total_working_years = col12.number_input("Total Working Years", min_value=0, value=3)
            
            submitted = st.form_submit_button("Submit New Employee")
            
            if submitted:
                if not first_name or not last_name or not email:
                    st.error("Please fill in required fields: First Name, Last Name, and Email.")
                elif not db_connected:
                    st.error("Cannot insert record: MySQL database is not connected.")
                else:
                    try:
                        emp = emp_manager.onboard_employee(
                            first_name=first_name,
                            last_name=last_name,
                            email=email,
                            department_id=department_id,
                            job_id=job_id,
                            monthly_income=monthly_income,
                            hire_date=hire_date,
                            phone_number=phone_number,
                            age=age,
                            gender=gender,
                            marital_status=marital_status,
                            education_field=education_field,
                            manager_id=manager_id,
                            total_working_years=total_working_years
                        )
                        st.success(f"✅ Employee **{emp.full_name}** successfully onboarded with ID **{emp.employee_id}**!")
                    except (ValidationError, AppError) as err:
                        st.error(f"❌ Backend Error: {err}")

    # ---------------------------------------------------------
    # TAB 2: PROJECT ASSIGNMENT
    # ---------------------------------------------------------
    with tab_project:
        st.subheader("Assign Employee to Project")
        with st.form("project_assignment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            employee_id = col1.number_input("Employee ID", min_value=10001, step=1)
            project_id = col2.number_input("Project ID", min_value=1, step=1)
            role_in_project = col1.text_input("Role in Project", value="Contributor")
            allocation_percentage = col2.slider("Allocation (%)", 10, 100, 100, step=10)
            
            assigned = st.form_submit_button("Assign Project")
            if assigned:
                try:
                    # Execute live database transaction
                    emp_manager.assign_to_project(
                        employee_id=int(employee_id),
                        project_id=int(project_id),
                        role=role_in_project,
                        allocation=allocation_percentage
                    )
                    st.success(
                        f"✅ Successfully assigned Employee ID **{employee_id}** "
                        f"to Project ID **{project_id}** as *{role_in_project}* ({allocation_percentage}% allocation)!"
                    )
                except (RecordNotFoundError, ValidationError) as err:
                    st.warning(f"⚠️ Input Validation Error: {err}")
                except Exception as err:
                    st.error(f"❌ Failed to assign project: {err}")

    # ---------------------------------------------------------
    # TAB 3: DEPARTMENT / ROLE UPDATE (SCD TYPE 2)
    # ---------------------------------------------------------
    with tab_scd2:
        st.subheader("Update Department / Role (SCD Type 2)")
        st.info("ℹ️ Updates current employee details in OLTP and triggers SCD Type 2 history creation in OLAP.")
        
        with st.form("scd_update_form", clear_on_submit=True):
            emp_id = st.number_input("Target Employee ID", min_value=10001, step=1)
            
            col1, col2 = st.columns(2)
            new_dept_id = col1.selectbox("New Department", options=list(dept_options.keys()), format_func=lambda x: dept_options[x])
            new_job_id = col2.selectbox("New Job Role", options=list(job_options.keys()), format_func=lambda x: job_options[x])
            new_income = st.number_input("Updated Monthly Income ($)", min_value=1000.0, value=8500.0, step=100.0)
            
            scd_submitted = st.form_submit_button("Apply Role / Income Change")
            
            if scd_submitted:
                if not db_connected:
                    st.error("Cannot perform update: Database not connected.")
                else:
                    try:
                        emp_manager.update_employee_role(
                            employee_id=int(emp_id),
                            new_department_id=int(new_dept_id),
                            new_job_id=int(new_job_id),
                            new_monthly_income=float(new_income)
                        )
                        # Clear Streamlit query cache so analytics charts reflect the new role immediately
                        st.cache_data.clear()
                        st.success(f"✅ Successfully updated Employee ID **{emp_id}** role and income!")
                    except RecordNotFoundError as e:
                        st.warning(f"⚠️ Employee Record Not Found: {e}")
                    except AppError as e:
                        st.error(f"❌ Update Error: {e}")

    # ---------------------------------------------------------
    # TAB 4: PERFORMANCE REVIEW
    # ---------------------------------------------------------
    with tab_review:
        st.subheader("Submit Performance Review")
        st.info("ℹ️ Logs employee performance review into OLTP and updates OLAP Fact table.")
        
        with st.form("review_form", clear_on_submit=True):
            rev_emp_id = st.number_input("Employee ID", min_value=10001, step=1)
            perf_rating = st.slider("Performance Rating (1-4)", 1, 4, 3)
            
            review_submitted = st.form_submit_button("Submit Review")
            
            if review_submitted:
                if not db_connected:
                    st.error("Cannot log review: Database connection inactive.")
                else:
                    try:
                        emp_manager.submit_performance_review(
                            employee_id=int(rev_emp_id),
                            rating=int(perf_rating)
                        )
                        # Clear cached analytics data so Top Performers charts re-evaluate rankings
                        st.cache_data.clear()
                        st.success(f"✅ Performance review of **{perf_rating}/4** successfully logged for Employee ID **{rev_emp_id}**!")
                    except RecordNotFoundError as e:
                        st.warning(f"⚠️ Employee ID **{rev_emp_id}** not found: {e}")
                    except AppError as e:
                        st.error(f"❌ Review Submission Failed: {e}")
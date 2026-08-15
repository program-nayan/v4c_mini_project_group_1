import streamlit as st
import datetime

def render_operational_forms():
    """Renders OLTP data entry forms mapped directly to the OLTP ER Diagram schema."""
    
    tab_onboard, tab_project, tab_scd2, tab_review = st.tabs([
        "👤 Onboard Employee", 
        "📁 Project Assignment", 
        "🔄 Department/Role Update (SCD2)", 
        "⭐ Performance Review"
    ])

    # ---------------------------------------------------------
    # TAB 1: ONBOARD EMPLOYEE (EMPLOYEES & JOBS Table)
    # ---------------------------------------------------------
    with tab_onboard:
        st.subheader("Onboard New Employee")
        st.caption("Insert record into EMPLOYEES table")
        
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
            department_id = col8.selectbox("Department (FK)", [101, 102, 103], format_func=lambda x: {101: "101 - Sales", 102: "102 - R&D", 103: "103 - HR"}[x])
            job_id = col9.selectbox("Job Role (FK)", [1, 2, 3, 4], format_func=lambda x: {1: "1 - Software Engineer", 2: "2 - Sales Exec", 3: "3 - Research Scientist", 4: "4 - HR Spec"}[x])
            manager_id = col10.number_input("Manager ID (FK)", min_value=1, value=1, step=1)
            
            col11, col12 = st.columns(2)
            monthly_income = col11.number_input("Monthly Income ($)", min_value=1000, value=6500, step=100)
            total_working_years = col12.number_input("Total Working Years", min_value=0, value=3)
            
            submitted = st.form_submit_button("Submit New Employee")
            
            if submitted:
                if not first_name or not last_name or not email:
                    st.error("Please fill in required fields: First Name, Last Name, and Email.")
                else:
                    st.success(f"✅ Employee **{first_name} {last_name}** successfully registered!")
                    st.json({
                        "Target Table": "EMPLOYEES",
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "phone_number": phone_number,
                        "department_id": department_id,
                        "job_id": job_id,
                        "manager_id": manager_id,
                        "monthly_income": monthly_income,
                        "hire_date": str(hire_date)
                    })

    # ---------------------------------------------------------
    # TAB 2: PROJECT ASSIGNMENT (PROJECT_ASSIGNMENTS Table)
    # ---------------------------------------------------------
    with tab_project:
        st.subheader("Assign Employee to Project")
        st.caption("Insert record into PROJECT_ASSIGNMENTS table")
        
        with st.form("project_assignment_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            employee_id = col1.number_input("Employee ID (FK)", min_value=1, step=1)
            project_id = col2.number_input("Project ID (FK)", min_value=1, step=1)
            
            col3, col4 = st.columns(2)
            role_in_project = col3.text_input("Role in Project", value="Lead Tech")
            allocation_percentage = col4.slider("Allocation Percentage (%)", min_value=10, max_value=100, value=100, step=10)
            
            assigned_date = st.date_input("Assignment Date", value=datetime.date.today())
            
            assigned = st.form_submit_button("Assign Project")
            
            if assigned:
                st.success(f"✅ Employee ID **{employee_id}** assigned to Project ID **{project_id}**.")
                st.json({
                    "Target Table": "PROJECT_ASSIGNMENTS",
                    "employee_id": employee_id,
                    "project_id": project_id,
                    "role_in_project": role_in_project,
                    "allocation_percentage": allocation_percentage,
                    "assigned_date": str(assigned_date)
                })

    # ---------------------------------------------------------
    # TAB 3: SCD TYPE 2 UPDATE (Dim_Employee Warehouse Trigger)
    # ---------------------------------------------------------
    with tab_scd2:
        st.subheader("Update Department/Role (Triggers SCD Type 2)")
        st.info("ℹ️ **SCD Type 2 Logic:** Updating an employee's department, job role, or monthly income will expire their current DW record version (`is_current = 0`) and create a new active record (`is_current = 1`).")
        
        with st.form("scd_update_form", clear_on_submit=True):
            emp_id = st.number_input("Target Employee ID", min_value=1, step=1)
            
            col1, col2 = st.columns(2)
            new_dept_id = col1.selectbox("New Department (FK)", [101, 102, 103], format_func=lambda x: {101: "101 - Sales", 102: "102 - R&D", 103: "103 - HR"}[x])
            new_job_id = col2.selectbox("New Job ID (FK)", [1, 2, 3, 4], format_func=lambda x: {1: "1 - Lead Developer", 2: "2 - Sr Sales Exec", 3: "3 - Sr Scientist", 4: "4 - HR Director"}[x])
            
            new_income = st.number_input("Updated Monthly Income ($)", min_value=1000, value=8500, step=100)
            effective_date = st.date_input("Effective Date of Change", value=datetime.date.today())
            
            scd_submitted = st.form_submit_button("Apply SCD2 Promotion / Update")
            
            if scd_submitted:
                st.warning(f"⚠️ **SCD Type 2 Pipeline Initiated** for Employee ID **{emp_id}**")
                st.code(
                    f"""
                    -- 1. Expire current dimensional record
                    UPDATE Dim_Employee 
                    SET end_date = '{effective_date}', is_current = 0 
                    WHERE employee_id = {emp_id} AND is_current = 1;

                    -- 2. Insert new current version with updated attributes
                    INSERT INTO Dim_Employee (
                        employee_id, department_id, job_id, monthly_income, 
                        start_date, end_date, is_current
                    )
                    VALUES (
                        {emp_id}, {new_dept_id}, {new_job_id}, {new_income}, 
                        '{effective_date}', NULL, 1
                    );
                    """, 
                    language="sql"
                )

    # ---------------------------------------------------------
    # TAB 4: PERFORMANCE REVIEWS (PERFORMANCE_REVIEWS Table)
    # ---------------------------------------------------------
    with tab_review:
        st.subheader("Submit Performance Review")
        st.caption("Insert record into PERFORMANCE_REVIEWS table")
        
        with st.form("review_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            rev_emp_id = col1.number_input("Employee ID (FK)", min_value=1, step=1)
            review_date = col2.date_input("Review Date", value=datetime.date.today())
            
            st.markdown("##### Satisfaction & Involvement Scores (1 = Low, 4 = Very High)")
            col3, col4, col5, col6 = st.columns(4)
            env_sat = col3.slider("Env Satisfaction", 1, 4, 3)
            job_sat = col4.slider("Job Satisfaction", 1, 4, 3)
            rel_sat = col5.slider("Rel Satisfaction", 1, 4, 3)
            job_inv = col6.slider("Job Involvement", 1, 4, 3)
            
            col7, col8 = st.columns(2)
            perf_rating = col7.slider("Overall Performance Rating (1-4)", 1, 4, 3)
            percent_hike = col8.number_input("Percent Salary Hike (%)", min_value=0.0, max_value=50.0, value=12.5, step=0.5)
            
            review_submitted = st.form_submit_button("Submit Performance Review")
            
            if review_submitted:
                st.success(f"✅ Performance review successfully submitted for Employee ID **{rev_emp_id}**.")
                st.json({
                    "Target Table": "PERFORMANCE_REVIEWS",
                    "employee_id": rev_emp_id,
                    "review_date": str(review_date),
                    "environment_satisfaction": env_sat,
                    "job_satisfaction": job_sat,
                    "relationship_satisfaction": rel_sat,
                    "job_involvement": job_inv,
                    "performance_rating": perf_rating,
                    "percent_salary_hike": percent_hike
                })
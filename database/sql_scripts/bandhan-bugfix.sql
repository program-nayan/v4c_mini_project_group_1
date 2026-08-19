-- ============================================================================
-- BANDHAN BUG FIX: OLTP & OLAP ETL PIPELINE FOR HR ANALYTICS PLATFORM
-- Utilizes MySQL 8.0 Common Table Expressions (CTEs) & Window Functions
-- ============================================================================

-- ============================================================================
-- PART 1: TRUNCATE & CLEAN OLTP DATABASE
-- ============================================================================
USE hr_oltp_db;

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE PERFORMANCE_REVIEWS;
TRUNCATE TABLE PROJECT_ASSIGNMENTS;
TRUNCATE TABLE PROJECTS;
TRUNCATE TABLE EMPLOYEES;
TRUNCATE TABLE JOBS;
TRUNCATE TABLE DEPARTMENTS;

SET FOREIGN_KEY_CHECKS = 1;


-- ============================================================================
-- PART 2: POPULATE OLTP DATABASE (STAGING -> OLTP ETL)
-- ============================================================================

-- 1. Populate DEPARTMENTS (Deduplicated via CTE & Window Function)
INSERT INTO DEPARTMENTS (department_id, department_name, location)
WITH UniqueDepts AS (
    SELECT 
        department_id,
        CASE department_id
            WHEN 1 THEN 'Sales'
            WHEN 2 THEN 'Research & Development'
            WHEN 3 THEN 'Human Resources'
            ELSE COALESCE(Department, 'General')
        END AS department_name,
        CASE department_id
            WHEN 1 THEN 'New York - Tech Hub'
            WHEN 2 THEN 'San Francisco - R&D Center'
            WHEN 3 THEN 'Chicago - HQ'
            ELSE 'Headquarters'
        END AS location,
        ROW_NUMBER() OVER (PARTITION BY department_id ORDER BY department_id) AS rn
    FROM hr_staging_db.staging_employees
    WHERE department_id IS NOT NULL
)
SELECT department_id, department_name, location 
FROM UniqueDepts
WHERE rn = 1;

-- 2. Populate JOBS (Deduplicated via CTE & Window Function)
INSERT INTO JOBS (job_role, job_level)
WITH RankedJobs AS (
    SELECT 
        TRIM(JobRole) AS job_role,
        CAST(JobLevel AS UNSIGNED) AS job_level,
        ROW_NUMBER() OVER (
            PARTITION BY TRIM(JobRole), JobLevel 
            ORDER BY JobLevel ASC
        ) AS rn
    FROM hr_staging_db.staging_employees
    WHERE JobRole IS NOT NULL AND JobLevel IS NOT NULL
)
SELECT job_role, job_level
FROM RankedJobs
WHERE rn = 1;

-- 3. Populate EMPLOYEES (Active Current Records Only: is_current = 1)
INSERT INTO EMPLOYEES (
    employee_id, first_name, last_name, email, phone_number, age, 
    gender, marital_status, education, education_field, hire_date, 
    department_id, job_id, monthly_income, attrition, 
    distance_from_home, total_working_years
)
WITH ActiveEmployeesCTE AS (
    SELECT 
        s.employee_id,
        TRIM(s.first_name) AS first_name,
        TRIM(s.last_name) AS last_name,
        LOWER(TRIM(s.email)) AS email,
        s.phone_number,
        s.Age AS age,
        s.Gender AS gender,
        s.MaritalStatus AS marital_status,
        s.Education AS education,
        s.EducationField AS education_field,
        s.hire_date,
        s.department_id,
        j.job_id,
        COALESCE(s.MonthlyIncome, 0.00) AS monthly_income,
        COALESCE(s.Attrition, 'No') AS attrition,
        s.DistanceFromHome AS distance_from_home,
        s.TotalWorkingYears AS total_working_years,
        ROW_NUMBER() OVER (
            PARTITION BY s.employee_id 
            ORDER BY s.is_current DESC, s.effective_start_date DESC
        ) AS rn
    FROM hr_staging_db.staging_employees s
    JOIN JOBS j 
      ON TRIM(s.JobRole) = j.job_role 
     AND s.JobLevel = j.job_level
    JOIN DEPARTMENTS d
      ON s.department_id = d.department_id
    WHERE s.is_current = 1
)
SELECT 
    employee_id, first_name, last_name, email, phone_number, age, 
    gender, marital_status, education, education_field, hire_date, 
    department_id, job_id, monthly_income, attrition, 
    distance_from_home, total_working_years
FROM ActiveEmployeesCTE
WHERE rn = 1;

-- 4. Assign Managers (Optimized CTE & Window Function for Fast Hierarchy Setup)
WITH RankedManagers AS (
    SELECT 
        employee_id,
        department_id,
        ROW_NUMBER() OVER (
            PARTITION BY department_id 
            ORDER BY employee_id ASC
        ) AS mgr_rank
    FROM EMPLOYEES
    WHERE employee_id % 5 = 0
)
UPDATE EMPLOYEES e
JOIN RankedManagers m 
  ON e.department_id = m.department_id 
 AND m.mgr_rank = 1
SET e.manager_id = m.employee_id
WHERE e.employee_id % 5 != 0;

-- 5. Populate Seed PROJECTS & ASSIGNMENTS
INSERT INTO PROJECTS (project_name, department_id, start_date, budget) VALUES
('Cloud Infrastructure Modernization', 2, '2024-01-15', 500000.00),
('Enterprise AI Assistant Upgrade', 2, '2024-06-01', 350000.00),
('Global Sales ERP Integration', 1, '2025-02-10', 450000.00),
('HR Payroll Automation & Analytics', 3, '2025-09-01', 200000.00),
('Customer Portal 2.0 Redesign', 1, '2026-01-05', 150000.00);

-- Populate PROJECT_ASSIGNMENTS (Assign exactly 1 primary project per assigned employee via CTE & Window Function)
INSERT INTO PROJECT_ASSIGNMENTS (employee_id, project_id, role_in_project, allocation_percentage, assigned_date)
WITH RankedAssignments AS (
    SELECT 
        e.employee_id,
        p.project_id,
        e.hire_date,
        ROW_NUMBER() OVER (
            PARTITION BY e.employee_id 
            ORDER BY p.start_date DESC, p.project_id DESC
        ) AS project_rn
    FROM EMPLOYEES e
    JOIN PROJECTS p 
      ON e.department_id = p.department_id
    WHERE e.employee_id % 3 = 0
)
SELECT 
    employee_id,
    project_id,
    'Contributor' AS role_in_project,
    100 AS allocation_percentage,
    hire_date AS assigned_date
FROM RankedAssignments
WHERE project_rn = 1;

-- 6. Populate PERFORMANCE_REVIEWS (Deduplicated via CTE & Window Function)
INSERT INTO PERFORMANCE_REVIEWS (
    employee_id, review_date, environment_satisfaction, 
    job_satisfaction, relationship_satisfaction, job_involvement, 
    performance_rating, percent_salary_hike
)
WITH CleanReviewsCTE AS (
    SELECT 
        s.employee_id,
        s.effective_start_date AS review_date,
        COALESCE(s.EnvironmentSatisfaction, 3) AS env_sat,
        COALESCE(s.JobSatisfaction, 3) AS job_sat,
        COALESCE(s.RelationshipSatisfaction, 3) AS rel_sat,
        COALESCE(s.JobInvolvement, 3) AS job_inv,
        COALESCE(s.PerformanceRating, 3) AS perf_rating,
        COALESCE(s.PercentSalaryHike, 0.00) AS salary_hike,
        ROW_NUMBER() OVER (
            PARTITION BY s.employee_id, s.effective_start_date 
            ORDER BY s.is_current DESC
        ) AS rn
    FROM hr_staging_db.staging_employees s
    JOIN EMPLOYEES e 
      ON s.employee_id = e.employee_id
)
SELECT 
    employee_id, review_date, env_sat, job_sat, rel_sat, 
    job_inv, perf_rating, salary_hike
FROM CleanReviewsCTE
WHERE rn = 1;


-- ============================================================================
-- PART 3: REGISTER STORED PROCEDURES & EXECUTE DATA WAREHOUSE ETL
-- ============================================================================
USE hr_olap_db;

-- 1. Procedure: Populate Base Dimensions
DROP PROCEDURE IF EXISTS sp_ETL_Populate_Base_Dimensions;
DELIMITER //
CREATE PROCEDURE sp_ETL_Populate_Base_Dimensions()
BEGIN
    DECLARE current_dt DATE DEFAULT '2010-01-01';
    DECLARE end_dt DATE DEFAULT '2035-12-31';

    SET FOREIGN_KEY_CHECKS = 0;
    TRUNCATE TABLE Dim_Department;
    TRUNCATE TABLE Dim_Project;
    SET FOREIGN_KEY_CHECKS = 1;

    -- A. Populate Dim_Department
    INSERT INTO Dim_Department (department_id, department_name, location)
    SELECT department_id, department_name, location
    FROM hr_oltp_db.DEPARTMENTS;

    -- B. Populate Dim_Project (Key 1 = Default Unassigned Record)
    INSERT INTO Dim_Project (project_key, project_id, project_name, start_date, end_date, budget)
    VALUES (1, 0, 'Unassigned / Operational Task', '2010-01-01', '9999-12-31', 0.00);

    INSERT INTO Dim_Project (project_id, project_name, start_date, end_date, budget)
    SELECT project_id, project_name, start_date, end_date, budget
    FROM hr_oltp_db.PROJECTS;

    -- C. Populate Dim_Date
    IF (SELECT COUNT(*) FROM Dim_Date) = 0 THEN
        WHILE current_dt <= end_dt DO
            INSERT IGNORE INTO Dim_Date (
                date_key, full_date, year, quarter, month, month_name, day_of_month, day_of_week
            )
            VALUES (
                CAST(DATE_FORMAT(current_dt, '%Y%m%d') AS UNSIGNED),
                current_dt,
                YEAR(current_dt),
                QUARTER(current_dt),
                MONTH(current_dt),
                MONTHNAME(current_dt),
                DAYOFMONTH(current_dt),
                DAYNAME(current_dt)
            );
            SET current_dt = DATE_ADD(current_dt, INTERVAL 1 DAY);
        END WHILE;
    END IF;
END //
DELIMITER ;

-- 2. Procedure: Populate Dim_Employee (SCD Type 2 Load using LEAD & ROW_NUMBER)
DROP PROCEDURE IF EXISTS sp_ETL_Populate_Dim_Employee_SCD2;
DELIMITER //
CREATE PROCEDURE sp_ETL_Populate_Dim_Employee_SCD2()
BEGIN
    SET FOREIGN_KEY_CHECKS = 0;
    TRUNCATE TABLE Dim_Employee;
    SET FOREIGN_KEY_CHECKS = 1;

    INSERT INTO Dim_Employee (
        employee_id, full_name, email, job_role, job_level,
        monthly_income, department_id, hire_date,
        effective_start_date, effective_end_date, is_current,
        change_reason, attrition
    )
    WITH DeduplicatedStaging AS (
        SELECT 
            s.employee_id,
            CONCAT(TRIM(s.first_name), ' ', TRIM(s.last_name)) AS full_name,
            LOWER(TRIM(s.email)) AS email,
            TRIM(s.JobRole) AS job_role,
            CAST(s.JobLevel AS UNSIGNED) AS job_level,
            COALESCE(s.MonthlyIncome, 0.00) AS monthly_income,
            s.department_id,
            s.hire_date,
            s.effective_start_date,
            COALESCE(s.change_reason, 'Initial Onboarding') AS change_reason,
            COALESCE(s.Attrition, 'No') AS attrition,
            ROW_NUMBER() OVER (
                PARTITION BY s.employee_id, s.effective_start_date 
                ORDER BY s.is_current DESC
            ) AS rn
        FROM hr_staging_db.staging_employees s
        WHERE s.employee_id IS NOT NULL 
          AND s.effective_start_date IS NOT NULL
    ),
    StructuredSCD2 AS (
        SELECT
            employee_id,
            full_name,
            email,
            job_role,
            job_level,
            monthly_income,
            department_id,
            hire_date,
            effective_start_date,
            LEAD(effective_start_date) OVER (
                PARTITION BY employee_id 
                ORDER BY effective_start_date ASC
            ) AS calculated_next_start,
            change_reason,
            attrition
        FROM DeduplicatedStaging
        WHERE rn = 1
    ),
    RefinedSCD2 AS (
        SELECT 
            employee_id,
            full_name,
            email,
            job_role,
            job_level,
            monthly_income,
            department_id,
            hire_date,
            effective_start_date,
            CASE 
                WHEN calculated_next_start IS NOT NULL THEN calculated_next_start
                ELSE '9999-12-31'
            END AS effective_end_date,
            CASE 
                WHEN calculated_next_start IS NULL THEN 1 
                ELSE 0 
            END AS is_current,
            change_reason,
            attrition
        FROM StructuredSCD2
    )
    SELECT 
        employee_id, full_name, email, job_role, job_level,
        monthly_income, department_id, hire_date,
        effective_start_date, effective_end_date, is_current,
        change_reason, attrition
    FROM RefinedSCD2
    ORDER BY employee_id, effective_start_date;

END //
DELIMITER ;

-- 3. Procedure: Populate Fact_PerformanceReviews
DROP PROCEDURE IF EXISTS sp_ETL_Populate_Fact_Performance;
DELIMITER //
CREATE PROCEDURE sp_ETL_Populate_Fact_Performance()
BEGIN
    SET FOREIGN_KEY_CHECKS = 0;
    TRUNCATE TABLE Fact_PerformanceReviews;
    SET FOREIGN_KEY_CHECKS = 1;

    INSERT INTO Fact_PerformanceReviews (
        emp_key, dept_key, project_key, review_date_key,
        environment_satisfaction, job_satisfaction,
        relationship_satisfaction, job_involvement,
        performance_rating, percent_salary_hike, monthly_income
    )
    WITH DeduplicatedStaging AS (
        SELECT 
            s.employee_id,
            s.department_id,
            s.effective_start_date,
            COALESCE(s.EnvironmentSatisfaction, 3) AS env_sat,
            COALESCE(s.JobSatisfaction, 3) AS job_sat,
            COALESCE(s.RelationshipSatisfaction, 3) AS rel_sat,
            COALESCE(s.JobInvolvement, 3) AS job_inv,
            COALESCE(s.PerformanceRating, 3) AS perf_rating,
            COALESCE(s.PercentSalaryHike, 0.00) AS salary_hike,
            COALESCE(s.MonthlyIncome, 0.00) AS monthly_income,
            ROW_NUMBER() OVER (
                PARTITION BY s.employee_id, s.effective_start_date 
                ORDER BY s.is_current DESC
            ) AS rn
        FROM hr_staging_db.staging_employees s
        WHERE s.employee_id IS NOT NULL 
          AND s.effective_start_date IS NOT NULL
    ),
    PrimaryProjectAssignment AS (
        SELECT 
            pa.employee_id,
            p.project_key,
            ROW_NUMBER() OVER (
                PARTITION BY pa.employee_id 
                ORDER BY pa.assigned_date DESC, pa.assignment_id DESC
            ) AS proj_rn
        FROM hr_oltp_db.PROJECT_ASSIGNMENTS pa
        JOIN Dim_Project p 
          ON pa.project_id = p.project_id
    ),
    FactIngestionCTE AS (
        SELECT
            e.emp_key,
            d.dept_key,
            COALESCE(pa.project_key, 1) AS project_key,
            CAST(DATE_FORMAT(s.effective_start_date, '%Y%m%d') AS UNSIGNED) AS review_date_key,
            s.env_sat,
            s.job_sat,
            s.rel_sat,
            s.job_inv,
            s.perf_rating,
            s.salary_hike,
            s.monthly_income,
            ROW_NUMBER() OVER (
                PARTITION BY s.employee_id, s.effective_start_date 
                ORDER BY e.emp_key DESC
            ) AS fact_rn
        FROM DeduplicatedStaging s
        JOIN Dim_Employee e
          ON s.employee_id = e.employee_id
         AND s.effective_start_date = e.effective_start_date
        JOIN Dim_Department d
          ON s.department_id = d.department_id
        JOIN Dim_Date dt
          ON CAST(DATE_FORMAT(s.effective_start_date, '%Y%m%d') AS UNSIGNED) = dt.date_key
        LEFT JOIN PrimaryProjectAssignment pa
          ON s.employee_id = pa.employee_id 
         AND pa.proj_rn = 1
        WHERE s.rn = 1
    )
    SELECT 
        emp_key, dept_key, project_key, review_date_key,
        env_sat, job_sat, rel_sat, job_inv,
        perf_rating, salary_hike, monthly_income
    FROM FactIngestionCTE
    WHERE fact_rn = 1;

END //
DELIMITER ;

-- 4. Procedure: Incremental SCD Type 2 Update (Called by Backend UI)
DROP PROCEDURE IF EXISTS sp_UpdateEmployeeSCD2;
DELIMITER //
CREATE PROCEDURE sp_UpdateEmployeeSCD2 (
    IN p_employee_id INT,
    IN p_new_department_id INT,
    IN p_new_job_role VARCHAR(100),
    IN p_new_job_level INT,
    IN p_new_monthly_income DECIMAL(10,2),
    IN p_change_reason VARCHAR(100),
    IN p_attrition VARCHAR(10)
)
BEGIN
    DECLARE v_old_emp_key INT;
    DECLARE v_full_name VARCHAR(200);
    DECLARE v_email VARCHAR(150);
    DECLARE v_hire_date DATE;
    DECLARE v_today DATE;

    SET v_today = CURRENT_DATE();

    -- 1. Locate current active record
    SELECT emp_key, full_name, email, hire_date
    INTO v_old_emp_key, v_full_name, v_email, v_hire_date
    FROM Dim_Employee
    WHERE employee_id = p_employee_id AND is_current = 1
    ORDER BY emp_key DESC
    LIMIT 1;

    IF v_old_emp_key IS NOT NULL THEN
        -- 2. Expire old record
        UPDATE Dim_Employee
        SET effective_end_date = v_today,
            is_current = 0
        WHERE emp_key = v_old_emp_key;

        -- 3. Insert new active SCD2 version
        INSERT INTO Dim_Employee (
            employee_id, full_name, email, job_role, job_level,
            monthly_income, department_id, hire_date,
            effective_start_date, effective_end_date, is_current,
            change_reason, attrition
        )
        VALUES (
            p_employee_id, v_full_name, v_email, p_new_job_role, p_new_job_level,
            p_new_monthly_income, p_new_department_id, v_hire_date,
            v_today, '9999-12-31', 1, p_change_reason, COALESCE(p_attrition, 'No')
        );

        SELECT 'SUCCESS: Employee SCD Type 2 record updated!' AS result;
    ELSE
        SELECT 'ERROR: Active employee not found!' AS result;
    END IF;
END //
DELIMITER ;

-- 5. Procedure: Master Pipeline Runner
DROP PROCEDURE IF EXISTS sp_Run_Full_OLAP_ETL;
DELIMITER //
CREATE PROCEDURE sp_Run_Full_OLAP_ETL()
BEGIN
    CALL sp_ETL_Populate_Base_Dimensions();
    CALL sp_ETL_Populate_Dim_Employee_SCD2();
    CALL sp_ETL_Populate_Fact_Performance();
    
    SELECT 'SUCCESS: Full OLAP ETL Pipeline Executed Successfully!' AS status;
END //
DELIMITER ;

-- TRIGGER FULL DATA WAREHOUSE LOAD
CALL sp_Run_Full_OLAP_ETL();


-- ============================================================================
-- PART 4: VERIFICATION CHECKS
-- ============================================================================
SELECT COUNT(*) AS active_oltp_employees FROM hr_oltp_db.EMPLOYEES;
SELECT COUNT(*) AS total_olap_dim_employees FROM hr_olap_db.Dim_Employee;
SELECT is_current, COUNT(*) AS count FROM hr_olap_db.Dim_Employee GROUP BY is_current;
SELECT COUNT(*) AS total_performance_facts FROM hr_olap_db.Fact_PerformanceReviews;
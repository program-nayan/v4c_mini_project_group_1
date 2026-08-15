CREATE DATABASE IF NOT EXISTS hr_olap_db;
USE hr_olap_db;

-- ========================================================
-- 1. DIMENSION: Dim_Department
-- ========================================================
CREATE TABLE IF NOT EXISTS Dim_Department (
    dept_key INT AUTO_INCREMENT PRIMARY KEY,  -- Surrogate Key
    department_id INT NOT NULL,               -- Business Key
    department_name VARCHAR(100) NOT NULL,
    location VARCHAR(100)
);

-- ========================================================
-- 2. DIMENSION: Dim_Project
-- ========================================================
CREATE TABLE IF NOT EXISTS Dim_Project (
    project_key INT AUTO_INCREMENT PRIMARY KEY, -- Surrogate Key
    project_id INT NOT NULL,                  -- Business Key
    project_name VARCHAR(150) NOT NULL,
    start_date DATE,
    end_date DATE,
    budget DECIMAL(12,2)
);

-- ========================================================
-- 3. DIMENSION: Dim_Date
-- ========================================================
CREATE TABLE IF NOT EXISTS Dim_Date (
    date_key INT PRIMARY KEY,                 -- Format: YYYYMMDD
    full_date DATE NOT NULL,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(20) NOT NULL,
    day_of_month INT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL
);

-- ========================================================
-- 4. DIMENSION: Dim_Employee (SCD Type 2)
-- ========================================================
CREATE TABLE IF NOT EXISTS Dim_Employee (
    emp_key INT AUTO_INCREMENT PRIMARY KEY,   -- Surrogate Key (Changes with each SCD2 version)
    employee_id INT NOT NULL,                 -- Business Key (Remains constant for same person)
    full_name VARCHAR(200) NOT NULL,
    email VARCHAR(150) NOT NULL,
    job_role VARCHAR(100),
    job_level INT,
    monthly_income DECIMAL(10,2),
    department_id INT,
    hire_date DATE,
    effective_start_date DATE NOT NULL,       -- SCD2 Trackers
    effective_end_date DATE NOT NULL,         -- SCD2 Trackers
    is_current TINYINT NOT NULL DEFAULT 1,    -- SCD2 Active Flag (1=Active, 0=Expired)
    change_reason VARCHAR(100)
);

-- Indexing for fast SCD2 lookup and JOIN joins
CREATE INDEX idx_emp_scd2 ON Dim_Employee(employee_id, is_current);

-- ========================================================
-- 5. FACT TABLE: Fact_PerformanceReviews
-- ========================================================
CREATE TABLE IF NOT EXISTS Fact_PerformanceReviews (
    review_fact_id INT AUTO_INCREMENT PRIMARY KEY,
    emp_key INT NOT NULL,                      -- FK to Dim_Employee
    dept_key INT NOT NULL,                     -- FK to Dim_Department
    project_key INT NOT NULL,                  -- FK to Dim_Project
    review_date_key INT NOT NULL,              -- FK to Dim_Date
    environment_satisfaction INT,
    job_satisfaction INT,
    relationship_satisfaction INT,
    job_involvement INT,
    performance_rating INT,
    percent_salary_hike DECIMAL(5,2),
    monthly_income DECIMAL(10,2),
    FOREIGN KEY (emp_key) REFERENCES Dim_Employee(emp_key),
    FOREIGN KEY (dept_key) REFERENCES Dim_Department(dept_key),
    FOREIGN KEY (project_key) REFERENCES Dim_Project(project_key),
    FOREIGN KEY (review_date_key) REFERENCES Dim_Date(date_key)
);






----------------- Populate Dimensions & Fact Table---------------------------



USE hr_olap_db;

-- --------------------------------------------------------
-- A. POPULATE Dim_Department
-- --------------------------------------------------------
INSERT INTO Dim_Department (department_id, department_name, location)
SELECT department_id, department_name, location 
FROM hr_oltp_db.DEPARTMENTS;

-- --------------------------------------------------------
-- B. POPULATE Dim_Project (Including Default Unassigned Record)
-- --------------------------------------------------------
-- Default Unassigned Record for employees without projects
INSERT INTO Dim_Project (project_key, project_id, project_name, start_date, end_date, budget)
VALUES (1, 0, 'Unassigned / Operational Task', '2015-01-01', '9999-12-31', 0.00);

-- Populate existing projects from OLTP
INSERT INTO Dim_Project (project_id, project_name, start_date, end_date, budget)
SELECT project_id, project_name, start_date, end_date, budget
FROM hr_oltp_db.PROJECTS;

-- --------------------------------------------------------
-- C. POPULATE Dim_Date (Generating Dates 2015 to 2030)
-- --------------------------------------------------------
-- Stored Procedure to auto-fill calendar dates
DELIMITER //
CREATE PROCEDURE PopulateDimDate()
BEGIN
    DECLARE current_dt DATE DEFAULT '2015-01-01';
    DECLARE end_dt DATE DEFAULT '2030-12-31';

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
END //
DELIMITER ;

CALL PopulateDimDate();
DROP PROCEDURE PopulateDimDate;

-- --------------------------------------------------------
-- D. POPULATE Dim_Employee (BULK SCD TYPE 2 INGESTION: ~100k+ Rows)
-- --------------------------------------------------------
INSERT INTO Dim_Employee (
    employee_id, full_name, email, job_role, job_level, 
    monthly_income, department_id, hire_date, 
    effective_start_date, effective_end_date, is_current, change_reason
)
SELECT 
    s.employee_id,
    CONCAT(s.first_name, ' ', s.last_name) AS full_name,
    s.email,
    s.JobRole,
    s.JobLevel,
    s.MonthlyIncome,
    s.department_id,
    s.hire_date,
    s.effective_start_date,
    s.effective_end_date,
    s.is_current,
    s.change_reason
FROM hr_staging_db.staging_employees s
ORDER BY s.employee_id, s.effective_start_date;

-- --------------------------------------------------------
-- E. POPULATE Fact_PerformanceReviews
-- --------------------------------------------------------
-- Links Fact records to the specific historical Dim_Employee version active on review_date
INSERT INTO Fact_PerformanceReviews (
    emp_key, dept_key, project_key, review_date_key, 
    environment_satisfaction, job_satisfaction, 
    relationship_satisfaction, job_involvement, 
    performance_rating, percent_salary_hike, monthly_income
)
SELECT 
    e.emp_key,
    d.dept_key,
    COALESCE(p.project_key, 1) AS project_key,  -- Default to 1 (Unassigned) if no project
    CAST(DATE_FORMAT(s.effective_start_date, '%Y%m%d') AS UNSIGNED) AS review_date_key,
    s.EnvironmentSatisfaction,
    s.JobSatisfaction,
    s.RelationshipSatisfaction,
    s.JobInvolvement,
    s.PerformanceRating,
    s.PercentSalaryHike,
    s.MonthlyIncome
FROM hr_staging_db.staging_employees s
-- Match exact historical surrogate key (emp_key) based on date window
JOIN Dim_Employee e 
  ON s.employee_id = e.employee_id 
 AND s.effective_start_date = e.effective_start_date
JOIN Dim_Department d 
  ON s.department_id = d.department_id
LEFT JOIN hr_oltp_db.PROJECT_ASSIGNMENTS pa 
  ON s.employee_id = pa.employee_id
LEFT JOIN Dim_Project p 
  ON pa.project_id = p.project_id;
  
  

CREATE DATABASE IF NOT EXISTS hr_oltp_db;
USE hr_oltp_db;

-- 1. DEPARTMENTS TABLE
CREATE TABLE IF NOT EXISTS DEPARTMENTS (
    department_id INT PRIMARY KEY,
    department_name VARCHAR(100) NOT NULL,
    location VARCHAR(100) DEFAULT 'Headquarters'
);

-- 2. JOBS TABLE
CREATE TABLE IF NOT EXISTS JOBS (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    job_role VARCHAR(100) NOT NULL,
    job_level INT NOT NULL,
    CONSTRAINT uq_job UNIQUE (job_role, job_level)
);

-- 3. EMPLOYEES TABLE (Current Active State)
CREATE TABLE IF NOT EXISTS EMPLOYEES (
    employee_id INT PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    phone_number VARCHAR(50),
    age INT,
    gender VARCHAR(20),
    marital_status VARCHAR(20),
    education INT,
    education_field VARCHAR(100),
    hire_date DATE NOT NULL,
    department_id INT NOT NULL,
    job_id INT NOT NULL,
    manager_id INT NULL,
    monthly_income DECIMAL(10,2),
    attrition VARCHAR(10) DEFAULT 'No',
    distance_from_home INT,
    total_working_years INT,
    FOREIGN KEY (department_id) REFERENCES DEPARTMENTS(department_id),
    FOREIGN KEY (job_id) REFERENCES JOBS(job_id),
    FOREIGN KEY (manager_id) REFERENCES EMPLOYEES(employee_id)
);

-- 4. PROJECTS TABLE
CREATE TABLE IF NOT EXISTS PROJECTS (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    project_name VARCHAR(150) NOT NULL,
    department_id INT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL,
    budget DECIMAL(12,2),
    FOREIGN KEY (department_id) REFERENCES DEPARTMENTS(department_id)
);

-- 5. PROJECT_ASSIGNMENTS TABLE
CREATE TABLE IF NOT EXISTS PROJECT_ASSIGNMENTS (
    assignment_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    project_id INT NOT NULL,
    role_in_project VARCHAR(100) DEFAULT 'Contributor',
    allocation_percentage INT DEFAULT 100,
    assigned_date DATE NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES EMPLOYEES(employee_id),
    FOREIGN KEY (project_id) REFERENCES PROJECTS(project_id)
);

-- 6. PERFORMANCE_REVIEWS TABLE
CREATE TABLE IF NOT EXISTS PERFORMANCE_REVIEWS (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT NOT NULL,
    review_date DATE NOT NULL,
    environment_satisfaction INT,
    job_satisfaction INT,
    relationship_satisfaction INT,
    job_involvement INT,
    performance_rating INT,
    percent_salary_hike DECIMAL(5,2),
    FOREIGN KEY (employee_id) REFERENCES EMPLOYEES(employee_id)
);





--------- Populate OLTP Tables from Staging----------------------------------------------------------


USE hr_oltp_db;


-- 1. Populate DEPARTMENTS
INSERT INTO DEPARTMENTS (department_id, department_name, location)
SELECT 
    department_id,
    CASE department_id
        WHEN 1 THEN 'Sales'
        WHEN 2 THEN 'Research & Development'
        WHEN 3 THEN 'Human Resources'
    END AS department_name,
    CASE department_id
        WHEN 1 THEN 'New York - Tech Hub'
        WHEN 2 THEN 'San Francisco - R&D Center'
        WHEN 3 THEN 'Chicago - HQ'
    END AS location
FROM (
    SELECT DISTINCT department_id FROM hr_staging_db.staging_employees
) AS unique_depts;

-- 2. Populate JOBS
INSERT INTO JOBS (job_role, job_level)
SELECT DISTINCT JobRole, JobLevel 
FROM hr_staging_db.staging_employees;


-- 3. Populate EMPLOYEES (Filtering for Active Current Records: is_current = 1)
INSERT INTO EMPLOYEES (
    employee_id, first_name, last_name, email, phone_number, age, 
    gender, marital_status, education, education_field, hire_date, 
    department_id, job_id, monthly_income, attrition, 
    distance_from_home, total_working_years
)
SELECT 
    s.employee_id,
    s.first_name,
    s.last_name,
    s.email,
    s.phone_number,
    s.Age,
    s.Gender,
    s.MaritalStatus,
    s.Education,
    s.EducationField,
    s.hire_date,
    s.department_id,
    j.job_id,
    s.MonthlyIncome,
    s.Attrition,
    s.DistanceFromHome,
    s.TotalWorkingYears
FROM hr_staging_db.staging_employees s
JOIN JOBS j 
  ON s.JobRole = j.job_role 
 AND s.JobLevel = j.job_level
WHERE s.is_current = 1;

-- 4. Assign Managers (Self-Referencing Foreign Key Setup)
UPDATE EMPLOYEES e
SET manager_id = (
    SELECT m.employee_id 
    FROM (SELECT employee_id, department_id FROM EMPLOYEES) m 
    WHERE m.department_id = e.department_id 
      AND m.employee_id != e.employee_id 
    LIMIT 1
)
WHERE e.employee_id % 5 != 0; -- Assign managers to 80% of staff

-- 5. Populate Seed PROJECTS
INSERT INTO PROJECTS (project_name, department_id, start_date, budget) VALUES
('Cloud Infrastructure Modernization', 2, '2024-01-15', 500000.00),
('Enterprise AI Assistant Upgrade', 2, '2024-06-01', 350000.00),
('Global Sales ERP Integration', 1, '2025-02-10', 450000.00),
('HR Payroll Automation & Analytics', 3, '2025-09-01', 200000.00),
('Customer Portal 2.0 Redesign', 1, '2026-01-05', 150000.00);

-- 6. Populate PROJECT_ASSIGNMENTS
INSERT INTO PROJECT_ASSIGNMENTS (employee_id, project_id, role_in_project, allocation_percentage, assigned_date)
SELECT 
    e.employee_id,
    p.project_id,
    'Contributor' AS role_in_project,
    100 AS allocation_percentage,
    e.hire_date
FROM EMPLOYEES e
JOIN PROJECTS p ON e.department_id = p.department_id
WHERE e.employee_id % 3 = 0;

-- 7. Populate PERFORMANCE_REVIEWS
INSERT INTO PERFORMANCE_REVIEWS (
    employee_id, review_date, environment_satisfaction, 
    job_satisfaction, relationship_satisfaction, job_involvement, 
    performance_rating, percent_salary_hike
)
SELECT 
    s.employee_id,
    s.effective_start_date AS review_date,
    s.EnvironmentSatisfaction,
    s.JobSatisfaction,
    s.RelationshipSatisfaction,
    s.JobInvolvement,
    s.PerformanceRating,
    s.PercentSalaryHike
FROM hr_staging_db.staging_employees s;




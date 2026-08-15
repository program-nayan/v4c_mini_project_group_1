-- ========================================================
-- 1. CREATE SCHEMAS
-- ========================================================
CREATE DATABASE IF NOT EXISTS hr_staging_db;
CREATE DATABASE IF NOT EXISTS hr_oltp_db;

-- ========================================================
-- 2. CREATE STAGING TABLE
-- ========================================================
USE hr_staging_db;

DROP TABLE IF EXISTS staging_employees;

CREATE TABLE staging_employees (
    employee_id INT,
    Age INT,
    Attrition VARCHAR(10),
    BusinessTravel VARCHAR(50),
    DailyRate INT,
    Department VARCHAR(100),
    DistanceFromHome INT,
    Education INT,
    EducationField VARCHAR(100),
    EnvironmentSatisfaction INT,
    Gender VARCHAR(20),
    HourlyRate INT,
    JobInvolvement INT,
    JobLevel INT,
    JobRole VARCHAR(100),
    JobSatisfaction INT,
    MaritalStatus VARCHAR(20),
    MonthlyIncome INT,
    MonthlyRate INT,
    NumCompaniesWorked INT,
    OverTime VARCHAR(10),
    PercentSalaryHike INT,
    PerformanceRating INT,
    RelationshipSatisfaction INT,
    StockOptionLevel INT,
    TotalWorkingYears INT,
    TrainingTimesLastYear INT,
    WorkLifeBalance INT,
    YearsAtCompany INT,
    YearsInCurrentRole INT,
    YearsSinceLastPromotion INT,
    YearsWithCurrManager INT,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(150),
    phone_number VARCHAR(50),
    department_id INT,
    hire_date DATE,
    effective_start_date DATE,
    effective_end_date DATE,
    is_current TINYINT,
    change_reason VARCHAR(100)
);




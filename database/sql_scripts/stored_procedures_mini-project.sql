USE hr_olap_db;

DROP PROCEDURE IF EXISTS sp_UpdateEmployeeSCD2;

DELIMITER //

CREATE PROCEDURE sp_UpdateEmployeeSCD2 (
    IN p_employee_id INT,
    IN p_new_department_id INT,
    IN p_new_job_role VARCHAR(100),
    IN p_new_job_level INT,
    IN p_new_monthly_income DECIMAL(10,2),
    IN p_change_reason VARCHAR(100),
    IN p_attrition VARCHAR(10)  -- Added Parameter
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
    LIMIT 1;

    IF v_old_emp_key IS NOT NULL THEN
        -- 2. Expire old record
        UPDATE Dim_Employee
        SET effective_end_date = v_today,
            is_current = 0
        WHERE emp_key = v_old_emp_key;

        -- 3. Insert new active SCD2 version with Attrition state
        INSERT INTO Dim_Employee (
            employee_id, full_name, email, job_role, job_level,
            monthly_income, department_id, hire_date,
            effective_start_date, effective_end_date, is_current,
            change_reason, attrition
        )
        VALUES (
            p_employee_id, v_full_name, v_email, p_new_job_role, p_new_job_level,
            p_new_monthly_income, p_new_department_id, v_hire_date,
            v_today, '9999-12-31', 1, p_change_reason, p_attrition
        );

        SELECT 'SUCCESS: Employee SCD Type 2 record updated!' AS result;
    ELSE
        SELECT 'ERROR: Active employee not found!' AS result;
    END IF;
END //

DELIMITER ;
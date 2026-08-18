import os
import re
import json
import yaml
import pandas as pd
import streamlit as st
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

from backend.db_manager import DatabaseConnection
from backend.exceptions import AppError
from backend.config import DB_OLAP_NAME, DB_OLTP_NAME, DB_HOST, DB_USER, DB_PASSWORD

# =========================================================
# 1. LOAD CONFIG.YAML DIRECTLY FROM ROOT DIRECTORY
# =========================================================
CONFIG_YAML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")

def load_yaml_config() -> dict:
    if os.path.exists(CONFIG_YAML_PATH):
        with open(CONFIG_YAML_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}

yaml_config = load_yaml_config()
GEMINI_MODEL_NAME = yaml_config.get("gemini", {}).get("model_name", "gemini-2.5-flash")
GEMINI_TEMPERATURE = float(yaml_config.get("gemini", {}).get("temperature", 0.1))

# =========================================================
# 2. PYDANTIC SCHEMA FOR STRICT STRUCTURED OUTPUT
# =========================================================
class SqlQueryPayload(BaseModel):
    target_db: str = Field(description="Target database to execute query against: 'OLAP' or 'OLTP'")
    sql_query: str = Field(description="Sanitized MySQL query matching the schema rules")
    explanation: str = Field(description="Brief 1-2 sentence explanation of what this query fetches")

# =========================================================
# 3. SYSTEM INSTRUCTIONS & ERD CONTEXT
# =========================================================
SYSTEM_PROMPT = f"""
You are an expert AI SQL Data Analyst for an Enterprise HR System.
Your task is to convert natural language questions into valid MySQL queries.

--- DATABASE SCHEMAS ---

[DEFAULT TARGET DB] OLAP Data Warehouse (`{DB_OLAP_NAME}` - Star Schema):
- DIM_EMPLOYEE: emp_key (PK), employee_id (BK), full_name, email, job_id, job_role, monthly_income, attrition, effective_start_date, effective_end_date, is_current (1=Active, 0=Expired), change_reason
- DIM_PROJECT: project_key (PK), project_id (BK), project_name, start_date, end_date
- DIM_DEPARTMENT: dept_key (PK), department_id (BK), department_name, location
- DIM_DATE: date_key (PK, YYYYMMDD), full_date, year, quarter, month, month_name, day_of_month, day_of_week
- FACT_PERFORMANCE_REVIEWS: review_fact_id (PK), emp_key (FK), project_key (FK), dept_key (FK), review_date_key (FK), environment_satisfaction, job_satisfaction, relationship_satisfaction, job_involvement, performance_rating, percent_salary_hike, monthly_income

[FALLBACK TARGET DB] OLTP Operational Database (`{DB_OLTP_NAME}` - Normalized ERD):
- DEPARTMENTS: department_id (PK), department_name, location
- JOBS: job_id (PK), job_role, job_level
- EMPLOYEES: employee_id (PK), first_name, last_name, email, phone_number, age, gender, marital_status, education, education_field, hire_date, department_id (FK), job_id (FK), manager_id (FK), monthly_income, attrition, distance_from_home, total_working_years
- PROJECTS: project_id (PK), project_name, department_id (FK), start_date, end_date, budget
- PROJECT_ASSIGNMENTS: assignment_id (PK), employee_id (FK), project_id (FK), role_in_project, allocation_percentage, assigned_date
- PERFORMANCE_REVIEWS: review_id (PK), employee_id (FK), review_date, environment_satisfaction, job_satisfaction, relationship_satisfaction, job_involvement, performance_rating, percent_salary_hike

--- ROUTING & SQL RULES ---
1. DEFAULT DB: Always set `target_db` to "OLAP".
2. OLTP FALLBACK: Set `target_db` to "OLTP" ONLY if operational fields not present in OLAP are required (e.g., `phone_number`, `manager_id`, `allocation_percentage`, `distance_from_home`, `total_working_years`, `marital_status`).
3. SCD TYPE 2 RULE: When querying `DIM_EMPLOYEE` in OLAP, ALWAYS include `WHERE is_current = 1` unless historical state changes or past versions are requested.
4. READ-ONLY SECURITY: Generate ONLY `SELECT` or `WITH` queries. NEVER generate `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, or multi-statement queries.
"""

# =========================================================
# 4. SECURITY & QUERY VALIDATION
# =========================================================
def validate_sql_security(sql_query: str) -> tuple[bool, str]:
    """Ensures generated SQL is strictly read-only and safe."""
    query_clean = sql_query.strip().upper()
    
    if ";" in query_clean[:-1]:
        return False, "Multi-statement queries (containing semicolons) are prohibited."
    
    if not (query_clean.startswith("SELECT") or query_clean.startswith("WITH")):
        return False, "Query must strictly begin with SELECT or WITH."
        
    forbidden_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", 
        "CREATE", "GRANT", "REVOKE", "EXEC", "CALL", "INTO OUTFILE"
    ]
    for word in forbidden_keywords:
        if re.search(rf"\b{word}\b", query_clean):
            return False, f"Forbidden keyword detected: '{word}'."
            
    return True, "Valid"

def inject_limit_clause(sql_query: str, max_limit: int = 100) -> str:
    """Appends LIMIT clause if not present to prevent UI memory strain."""
    if not re.search(r"\bLIMIT\s+\d+", sql_query, re.IGNORECASE):
        sql_query = sql_query.rstrip(";") + f" LIMIT {max_limit};"
    return sql_query

def execute_generated_query(target_db_type: str, sql_query: str) -> pd.DataFrame:
    """Executes query against target database using db_manager."""
    db_name = DB_OLAP_NAME if target_db_type.upper() == "OLAP" else DB_OLTP_NAME
    conn = DatabaseConnection(database=db_name, host=DB_HOST, user=DB_USER, password=DB_PASSWORD)
    results = conn.execute_query(sql_query)
    return pd.DataFrame(results)

# =========================================================
# 5. AI QUERY GENERATOR
# =========================================================
def generate_and_validate_sql(user_prompt: str, max_retries: int = 2) -> dict:
    """Uses google-genai Client with Pydantic structured schema validation."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Missing API Key. Please set `GEMINI_API_KEY` in your `.env` file.")
        
    client = genai.Client(api_key=api_key)
    
    current_prompt = user_prompt
    conversation_history = []
    
    for attempt in range(max_retries + 1):
        prompt_content = current_prompt
        if conversation_history:
            prompt_content += "\n\nPrevious Failed Attempts & Error Logs:\n" + "\n".join(conversation_history)
            
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt_content,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=SqlQueryPayload,
                temperature=GEMINI_TEMPERATURE,
            )
        )
        
        try:
            payload = json.loads(response.text)
            target_db = payload.get("target_db", "OLAP")
            raw_sql = payload.get("sql_query", "")
            explanation = payload.get("explanation", "")
            
            is_safe, error_msg = validate_sql_security(raw_sql)
            if not is_safe:
                raise ValueError(f"Security Policy Violation: {error_msg}")
                
            safe_sql = inject_limit_clause(raw_sql)
            df_result = execute_generated_query(target_db, safe_sql)
            
            return {
                "target_db": target_db,
                "sql_query": safe_sql,
                "explanation": explanation,
                "data": df_result
            }
            
        except Exception as e:
            err_str = str(e)
            if attempt == max_retries:
                raise RuntimeError(f"Failed after {max_retries + 1} attempts. Last Error: {err_str}")
            
            conversation_history.append(f"Attempt {attempt + 1} SQL: {raw_sql if 'raw_sql' in locals() else 'N/A'}")
            conversation_history.append(f"Execution Error: {err_str}")
            current_prompt = f"The previous SQL query failed with error: '{err_str}'. Fix the query and regenerate."

# =========================================================
# 6. STREAMLIT CHATBOT UI
# =========================================================
def render_sql_chatbot():
    """Renders Streamlit Chatbot Interface."""
    st.subheader("💬 AI Data Analyst Assistant")
    st.caption(f"Active Model: `{GEMINI_MODEL_NAME}` | Ask natural language questions about workforce metrics or performance reviews.")

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = [
            {
                "role": "assistant", 
                "content": "Hello! I am your AI Data Analyst. Ask me anything about employee records, salary trends, or performance reviews."
            }
        ]

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "sql_query" in msg:
                st.code(msg["sql_query"], language="sql")
            if "target_db" in msg:
                st.caption(f"🎯 Target Engine: `{msg['target_db']}` Database")
            if "df_data" in msg and msg["df_data"] is not None:
                if not msg["df_data"].empty:
                    st.dataframe(msg["df_data"], use_container_width=True)
                else:
                    st.info("ℹ️ Query executed successfully, but returned 0 rows.")

    if user_input := st.chat_input("e.g., Show top 5 earners in Sales and their performance rating"):
        st.session_state.chat_messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Generating query and fetching database records..."):
                try:
                    res = generate_and_validate_sql(user_input)
                    
                    st.markdown(res["explanation"])
                    st.code(res["sql_query"], language="sql")
                    st.caption(f"🎯 Target Engine: `{res['target_db']}` Database")
                    
                    if not res["data"].empty:
                        st.dataframe(res["data"], use_container_width=True)
                    else:
                        st.info("ℹ️ Query executed successfully, but returned 0 records.")

                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": res["explanation"],
                        "sql_query": res["sql_query"],
                        "target_db": res["target_db"],
                        "df_data": res["data"]
                    })

                except Exception as err:
                    err_msg = f"❌ **Error generating query:** {err}"
                    st.error(err_msg)
                    st.session_state.chat_messages.append({"role": "assistant", "content": err_msg})
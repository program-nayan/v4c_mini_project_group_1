import os
import streamlit as st

def get_config(key, default=""):
    """Reads configuration from Streamlit Secrets or Environment Variables."""
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)

DB_HOST = get_config("DB_HOST", "localhost")
DB_PORT = int(get_config("DB_PORT", 3306))  # Explicitly cast to integer
DB_USER = get_config("DB_USER", "root")
DB_PASSWORD = get_config("DB_PASS", "")     # Make sure secret key matches 'DB_PASS'
DB_OLTP_NAME = get_config("DB_OLTP_NAME", "hr_oltp_db")
DB_OLAP_NAME = get_config("DB_OLAP_NAME", "hr_olap_db")
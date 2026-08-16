import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASS", "")
DB_OLTP_NAME = os.getenv("DB_OLTP_NAME", "hr_oltp_db")
DB_OLAP_NAME = os.getenv("DB_OLAP_NAME", "hr_olap_db")
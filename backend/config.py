import os
from dotenv import load_dotenv

try:
    from backend.logger import get_logger
except ImportError:
    from logger import get_logger

load_dotenv()

logger = get_logger(__name__)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASS", "")
DB_OLTP_NAME = os.getenv("DB_OLTP_NAME", "hr_oltp_db")
DB_OLAP_NAME = os.getenv("DB_OLAP_NAME", "hr_olap_db")

logger.info(
    "Environment configuration loaded: Host=%s, User=%s, OLTP_DB=%s, OLAP_DB=%s",
    DB_HOST,
    DB_USER,
    DB_OLTP_NAME,
    DB_OLAP_NAME,
)
import sys
import os

try:
    from backend.logger import get_logger
    from backend.db_manager import DatabaseConnection
    from backend.config import DB_HOST, DB_USER, DB_PASSWORD, DB_OLTP_NAME
except ImportError:
    from logger import get_logger
    from db_manager import DatabaseConnection
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_OLTP_NAME

logger = get_logger(__name__)

def test_database_connection():
    logger.info("Starting database connection test to [%s] on host [%s]...", DB_OLTP_NAME, DB_HOST)
    try:
        db = DatabaseConnection(
            database=DB_OLTP_NAME,
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        result = db.execute_query("SELECT COUNT(*) AS total FROM EMPLOYEES")
        logger.info("Database connection test succeeded! Result: %s", result)
        print(result, flush=True)
        return result
    except Exception as e:
        logger.error("Database connection test failed: %s", e, exc_info=True)
        raise

if __name__ == "__main__":
    test_database_connection()
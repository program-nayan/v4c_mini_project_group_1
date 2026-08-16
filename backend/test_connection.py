from db_manager import DatabaseConnection
from config import DB_HOST, DB_USER, DB_PASSWORD, DB_OLTP_NAME
 
db = DatabaseConnection(
    database=DB_OLTP_NAME,
    host=DB_HOST,
    user=DB_USER,
    password=DB_PASSWORD
)
 
result = db.execute_query(
    "SELECT COUNT(*) AS total FROM EMPLOYEES"
)
 
print(result, flush=True)
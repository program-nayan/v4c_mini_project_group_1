import mysql.connector
from mysql.connector import Error as MySQLError

try:
    from backend.logger import get_logger
    from backend.config import DB_HOST, DB_USER, DB_PASSWORD, DB_PORT
    from backend.exceptions import (
        DatabaseConnectionError,
        QueryExecutionError,
        InvalidReferenceError,
        DuplicateRecordError,
    )
except ImportError:
    from logger import get_logger
    from config import DB_HOST, DB_USER, DB_PASSWORD, DB_PORT
    from exceptions import (
        DatabaseConnectionError,
        QueryExecutionError,
        InvalidReferenceError,
        DuplicateRecordError,
    )

logger = get_logger(__name__)


class DatabaseConnection:
    _instances = {}

    def __new__(cls, database, host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT):
        if database not in cls._instances:
            logger.info("Initializing new DatabaseConnection instance for database: %s", database)
            instance = super().__new__(cls)
            instance._connect(host, user, password, database, port)
            cls._instances[database] = instance
        return cls._instances[database]

    def _connect(self, host, user, password, database, port):
        self.database = database
        self.host = host
        self.port = int(port)  # Ensure port is explicitly cast to integer
        try:
            logger.info("Connecting to MySQL database '%s' at %s:%d as user '%s'", database, host, self.port, user)
            self._conn = mysql.connector.connect(
                host=self.host,
                user=user,
                password=password,
                database=database,
                port=self.port,         # Explicitly pass the integer port number
                connect_timeout=10,     # Standard timeout parameter in mysql.connector
                use_pure=True,          # Ensures pure Python implementation
                autocommit=True
            )
            logger.info("Successfully connected to MySQL database: %s", database)
        except MySQLError as e:
            logger.error("Failed to connect to MySQL database '%s' on %s:%d: %s", database, host, self.port, e)
            raise DatabaseConnectionError(str(e)) from e

    def execute_query(self, query, params=None, fetch=True):
        cursor = self._conn.cursor(dictionary=True)
        query_snippet = " ".join(query.strip().split()[:10])
        logger.debug("Executing query on [%s]: %s... with params: %s", self.database, query_snippet, params)
        try:
            cursor.execute(query, params or ())
            if fetch:
                results = cursor.fetchall()
                logger.debug("Query fetched %d rows from [%s]", len(results), self.database)
                return results
            if cursor.with_rows:
                cursor.fetchall()
            for pending_result in cursor.stored_results():
                pending_result.fetchall()
            self._conn.commit()
            logger.debug("Query executed and committed on [%s]. Affected rows: %d", self.database, cursor.rowcount)
            return cursor.rowcount
        except MySQLError as e:
            logger.error("Query execution failed on [%s]. Rolling back. Error: %s. Query: %s", self.database, e, query)
            self._conn.rollback()
            if e.errno == 1452:
                logger.error("Foreign key constraint violation (errno 1452): %s", e)
                raise InvalidReferenceError(str(e)) from e
            if e.errno == 1062:
                logger.error("Duplicate record constraint violation (errno 1062): %s", e)
                raise DuplicateRecordError(str(e)) from e
            raise QueryExecutionError(str(e)) from e
        finally:
            cursor.close()

    def close(self):
        logger.info("Closing MySQL connection for database: %s", getattr(self, "database", "unknown"))
        self._conn.close()

    @classmethod
    def reset_instances(cls):
        logger.info("Resetting all cached DatabaseConnection instances.")
        cls._instances = {}
import mysql.connector
from mysql.connector import Error as MySQLError

try:
    from backend.logger import get_logger
    from backend.exceptions import (
        DatabaseConnectionError,
        QueryExecutionError,
        InvalidReferenceError,
        DuplicateRecordError,
    )
except ImportError:
    from logger import get_logger
    from exceptions import (
        DatabaseConnectionError,
        QueryExecutionError,
        InvalidReferenceError,
        DuplicateRecordError,
    )

logger = get_logger(__name__)


class DatabaseConnection:
    _instances = {}

    def __new__(cls, database, host="localhost", user="root", password=""):
        if database not in cls._instances:
            logger.info("Initializing new DatabaseConnection instance for database: %s", database)
            instance = super().__new__(cls)
            instance._connect(host, user, password, database)
            cls._instances[database] = instance
        return cls._instances[database]

    def _connect(self, host, user, password, database):
        self.database = database
        self.host = host
        try:
            logger.info("Connecting to MySQL database '%s' at %s as user '%s'", database, host, user)
            self._conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database,
                connection_timeout=5,  # Prevents script from hanging indefinitely
                use_pure=True,  # Ensures pure Python implementation for better compatibility
                autocommit=True
            )
            logger.info("Successfully connected to MySQL database: %s", database)
        except MySQLError as e:
            logger.error("Failed to connect to MySQL database '%s' on %s: %s", database, host, e)
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

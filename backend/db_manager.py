import mysql.connector
from mysql.connector import Error as MySQLError

from exceptions import DatabaseConnectionError, QueryExecutionError, InvalidReferenceError, DuplicateRecordError


class DatabaseConnection:
    _instances = {}

    def __new__(cls, database, host="localhost", user="root", password=""):
        if database not in cls._instances:
            instance = super().__new__(cls)
            instance._connect(host, user, password, database)
            cls._instances[database] = instance
        return cls._instances[database]

    def _connect(self, host, user, password, database):
        try:
            self._conn = mysql.connector.connect(
                host=host, user=user, password=password, database=database
            )
        except MySQLError as e:
            raise DatabaseConnectionError(str(e)) from e

    def execute_query(self, query, params=None, fetch=True):
        cursor = self._conn.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ())
            if fetch:
                return cursor.fetchall()
            self._conn.commit()
            return cursor.rowcount
        except MySQLError as e:
            self._conn.rollback()
            if e.errno == 1452:
                raise InvalidReferenceError(str(e)) from e
            if e.errno == 1062:
                raise DuplicateRecordError(str(e)) from e
            raise QueryExecutionError(str(e)) from e
        finally:
            cursor.close()

    def close(self):
        self._conn.close()

    @classmethod
    def reset_instances(cls):
        cls._instances = {}

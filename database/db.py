# database/db.py
import pyodbc
from config import DB_CONFIG
from contextlib import contextmanager


class Database:
    def __init__(self):

        # Сохраняем имя базы как атрибут объекта
        self.database_name = DB_CONFIG['database']

        self.connection_string = (
            f"DRIVER={{{DB_CONFIG['driver']}}};"
            f"SERVER={DB_CONFIG['server']},{DB_CONFIG['port']};"
            f"DATABASE={DB_CONFIG['database']};"
            f"UID={DB_CONFIG['user']};"
            f"PWD={DB_CONFIG['password']};"
            f"Encrypt=no;"
            f"TrustServerCertificate=yes;"
        )

    @contextmanager
    def connect(self):
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string)
            yield conn
        except pyodbc.Error as e:
            print(f"Ошибка базы данных: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def fetch_all(self, query, params=None):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            rows = cursor.fetchall()
            columns = [column[0] for column in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, query, params=None):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            row = cursor.fetchone()
            if row:
                columns = [column[0] for column in cursor.description]
                return dict(zip(columns, row))
            return None

    def execute(self, query, params=None):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params or ())
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise Exception(f"Ошибка выполнения запроса: {e}")

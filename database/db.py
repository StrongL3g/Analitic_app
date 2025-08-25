# database/db.py
import pyodbc
from contextlib import contextmanager

# Убрали импорт из config здесь, будем передавать конфиг через конструктор

class Database:
    def __init__(self, db_config):
        self.db_config = db_config
        self.database_name = db_config['database']

        self.connection_string = (
            f"DRIVER={{{db_config['driver']}}};"
            f"SERVER={db_config['server']},{db_config['port']};"
            f"DATABASE={db_config['database']};"
            f"UID={db_config['user']};"
            f"PWD={db_config['password']};"
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

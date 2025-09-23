import pyodbc
import psycopg2
from contextlib import contextmanager

class Database:
    def __init__(self, db_config):
        self.db_config = db_config
        self.db_type = db_config.get('db_type', 'mssql')
        self.database_name = db_config['database']

    @contextmanager
    def connect(self):
        conn = None
        try:
            if self.db_type == 'postgres':
                # Подключение к PostgreSQL
                conn = psycopg2.connect(
                    host=self.db_config['host'],
                    port=self.db_config['port'],
                    database=self.db_config['database'],
                    user=self.db_config['user'],
                    password=self.db_config['password']
                )
            else:
                # Подключение к MSSQL
                connection_string = (
                    f"DRIVER={{{self.db_config['driver']}}};"
                    f"SERVER={self.db_config['server']},{self.db_config.get('port', '1433')};"
                    f"DATABASE={self.db_config['database']};"
                    f"UID={self.db_config['user']};"
                    f"PWD={self.db_config['password']};"
                    f"Encrypt=no;"
                    f"TrustServerCertificate=yes;"
                )
                conn = pyodbc.connect(connection_string)

            yield conn
        except Exception as e:
            print(f"Ошибка подключения к БД ({self.db_type}): {e}")
            raise
        finally:
            if conn:
                conn.close()

    def fetch_all(self, query, params=None):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())

            if self.db_type == 'postgres':
                # Для PostgreSQL
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            else:
                # Для MSSQL
                rows = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, query, params=None):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            row = cursor.fetchone()

            if row:
                if self.db_type == 'postgres':
                    columns = [desc[0] for desc in cursor.description]
                    return dict(zip(columns, row))
                else:
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

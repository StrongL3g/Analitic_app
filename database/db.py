import pyodbc
import psycopg2
from contextlib import contextmanager
import re

class Database:
    def __init__(self, db_config):
        self.db_config = db_config
        self.db_type = db_config.get('db_type', 'mssql')
        self.database_name = db_config['database']

    def _prepare_query_and_params(self, query, params):
        """Подготавливает запрос и параметры для конкретной СУБД"""
        if params is None:
            return query, None

        #print(f"Исходный запрос: {query}")

        if self.db_type == 'postgres':
            converted_query = query.replace('?', '%s')
            #print(f"Конвертированный запрос: {converted_query}")
            return converted_query, params
        else:
            return query, params

    @contextmanager
    def connect(self):
        conn = None
        try:
            if self.db_type == 'postgres':
                conn = psycopg2.connect(
                    host=self.db_config['host'],
                    port=self.db_config['port'],
                    database=self.db_config['database'],
                    user=self.db_config['user'],
                    password=self.db_config['password']
                )
            else:
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
            prepared_query, prepared_params = self._prepare_query_and_params(query, params)

            cursor.execute(prepared_query, prepared_params or ())

            if self.db_type == 'postgres':
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(columns, row)) for row in rows]
            else:
                rows = cursor.fetchall()
                columns = [column[0] for column in cursor.description]
                return [dict(zip(columns, row)) for row in rows]

    def fetch_one(self, query, params=None):
        with self.connect() as conn:
            cursor = conn.cursor()
            prepared_query, prepared_params = self._prepare_query_and_params(query, params)
            cursor.execute(prepared_query, prepared_params or ())
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
            prepared_query, prepared_params = self._prepare_query_and_params(query, params)

            try:
                cursor.execute(prepared_query, prepared_params or ())
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                conn.rollback()
                raise Exception(f"Ошибка выполнения запроса: {e}")

# database/db.py
import pyodbc
import psycopg2
from contextlib import contextmanager
import re


class _PreparedCursor:
    """Обёртка над psycopg2/pyodbc курсором с авто-конверсией запроса."""

    def __init__(self, cursor, db_type):
        self._cursor = cursor
        self._db_type = db_type

    def _convert_query(self, query):
        if self._db_type == 'postgres':
            query = re.sub(r'\[([^\]]+)\]', r'"\1"', query)
            query = query.replace('?', '%s')
        return query

    def execute(self, query, params=None):
        query = self._convert_query(query)
        if params is None:
            return self._cursor.execute(query)
        return self._cursor.execute(query, params)

    def executemany(self, query, params_list):
        query = self._convert_query(query)
        return self._cursor.executemany(query, params_list)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class Database:
    def __init__(self, db_config):
        self.db_config = db_config
        self.db_type = db_config.get('db_type', 'mssql')
        self.database_name = db_config['database']

    def _prepare_query_and_params(self, query, params):
        """Приводит запрос к синтаксису конкретной СУБД."""
        if self.db_type == 'postgres':
            # 1) MSSQL-идентификаторы [name] -> "name"
            query = re.sub(r'\[([^\]]+)\]', r'"\1"', query)
            # 2) Плейсхолдеры ? -> %s
            query = query.replace('?', '%s')
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

    @contextmanager
    def transaction(self):
        """Несколько запросов в одной транзакции с авто-конверсией ? -> %s."""
        with self.connect() as conn:
            cursor = conn.cursor()
            prepared = _PreparedCursor(cursor, self.db_type)
            try:
                yield prepared
                conn.commit()
            except Exception:
                conn.rollback()
                raise

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

    def executemany(self, query, params_list):
        """Выполняет один запрос для списка параметров (пакетное выполнение)"""
        with self.connect() as conn:
            cursor = conn.cursor()
            prepared_query, _ = self._prepare_query_and_params(query, None)
            try:
                cursor.executemany(prepared_query, params_list)
                conn.commit()
                return cursor.rowcount
            except Exception as e:
                conn.rollback()
                raise Exception(f"Ошибка пакетного выполнения запроса: {e}")
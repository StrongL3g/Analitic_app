# database/db.py
import pyodbc
import psycopg2
from contextlib import contextmanager
import re
import ast

from database.audit import get_audit, parse_sql


class _PreparedCursor:
    """Обёртка над psycopg2/pyodbc курсором с авто-конверсией запроса."""

    def __init__(self, cursor, db_type, database=None):
        self._cursor = cursor
        self._db_type = db_type
        self._database = database  # ссылка на Database для логов

    def _convert_query(self, query):
        if self._db_type == 'postgres':
            query = re.sub(r'\[([^\]]+)\]', r'"\1"', query)
            query = query.replace('?', '%s')
        return query

    def execute(self, query, params=None):
        raw_query = query
        query = self._convert_query(query)

        old_value = None
        if self._database is not None and self._database.audit_enabled:
            old_value = self._database._fetch_old_rows(raw_query, params)

        try:
            if params is None:
                res = self._cursor.execute(query)
            else:
                res = self._cursor.execute(query, params)
        except Exception as e:
            if self._database is not None and self._database.audit_enabled:
                self._database._audit_log(raw_query, params, old_value, None,
                                          success=False, error=str(e))
            raise

        if self._database is not None and self._database.audit_enabled:
            self._database._audit_log(raw_query, params, old_value, None, success=True)
        return res

    def executemany(self, query, params_list):
        query = self._convert_query(query)
        if self._database is not None and self._database.audit_enabled:
            self._database._audit_log(query, ("<batch>", len(params_list)),
                                      None, None, success=True)
        return self._cursor.executemany(query, params_list)

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class Database:
    def __init__(self, db_config, username=None, role=None):
        self.db_config = db_config
        self.db_type = db_config.get('db_type', 'mssql')
        self.database_name = db_config['database']

        # Аудит
        self.username = username
        self.role = role
        self.audit_enabled = True

    # ========================================================
    #  Аудит
    # ========================================================
    def set_audit(self, enabled: bool):
        """Временно включить/выключить аудит (для массовых операций)."""
        self.audit_enabled = enabled

    def _fetch_old_rows(self, query, params):
        """
        Для UPDATE/DELETE заранее читает «старые» значения.
        Возвращает строку-repr списка словарей или None.
        """
        op, table = parse_sql(query)
        if op not in ("UPDATE", "DELETE") or not table:
            return None

        # Отрезаем WHERE и всё, что за ним
        m = re.search(r"\bWHERE\b(.+)$", query, re.IGNORECASE | re.DOTALL)
        if not m:
            return None
        where_part = m.group(0).strip()

        # Считаем, сколько ? уходит в WHERE
        where_placeholders = where_part.count('?')

        # Формируем параметры ТОЛЬКО для WHERE
        if not params:
            select_params = None
        elif where_placeholders == 0:
            # В WHERE нет плейсхолдеров, но параметры есть — значит они все ушли в SET
            select_params = None
        else:
            n = where_placeholders
            if isinstance(params, (list, tuple)):
                select_params = tuple(params[-n:]) if n <= len(params) else tuple(params)
            else:
                select_params = (params,)

        select_sql = f"SELECT * FROM {table} {where_part}"

        try:
            was = self.audit_enabled
            self.audit_enabled = False
            rows = self.fetch_all(select_sql, select_params if select_params else None)
            self.audit_enabled = was
            return repr(rows) if rows else None
        except Exception as e:
            self.audit_enabled = True
            print(f"[audit] Не удалось прочитать старые значения: {e}")
            return None

    @staticmethod
    def _parse_update_columns(query: str):
        """
        Для UPDATE возвращает список колонок из SET в порядке появления ?.
        "UPDATE t SET a = ?, b = ?, c = ? WHERE id = ?" -> ['a', 'b', 'c']
        """
        m = re.search(r"\bSET\b(.+?)\bWHERE\b", query, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        set_part = m.group(1)
        cols = re.findall(r'([\[\]\w\".]+)\s*=\s*\?', set_part)
        return [c.strip('[]"').lower() for c in cols]

    def _audit_log(self, query, params, old_value, new_value, success=True, error=None):
        """Записать в аудит-журнал."""
        op, table = parse_sql(query)
        if op is None:
            return  # не INSERT/UPDATE/DELETE — не логируем

        record_id = None
        if params and isinstance(params, (list, tuple)) and params:
            record_id = params[-1]

        # === Формируем читаемое "стало" ===
        readable_new = params
        cols = []
        if op == "UPDATE" and isinstance(params, (list, tuple)):
            cols = self._parse_update_columns(query)
            if cols:
                values = list(params[:len(cols)])
                readable_new = dict(zip(cols, values))

        # === Формируем читаемое "было" — только изменяемые колонки ===
        readable_old = old_value
        if op == "UPDATE" and cols and old_value:
            try:
                old_list = ast.literal_eval(old_value)
                if old_list and isinstance(old_list[0], dict):
                    filtered = {k: old_list[0].get(k) for k in cols if k in old_list[0]}
                    readable_old = repr(filtered)
            except Exception:
                pass  # если не распарсилось — оставляем как было

        try:
            get_audit().write(
                username=self.username,
                role=self.role,
                operation=op,
                table_name=table,
                record_id=record_id,
                old_value=readable_old,
                new_value=repr(readable_new),
                sql_text=query,
                success=success,
                error=error,
            )
        except Exception as e:
            print(f"[audit] Ошибка записи лога: {e}")

    # ========================================================
    #  Работа с запросами
    # ========================================================
    def _prepare_query_and_params(self, query, params):
        if self.db_type == 'postgres':
            query = re.sub(r'\[([^\]]+)\]', r'"\1"', query)
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
        """Несколько запросов в одной транзакции с авто-конверсией и аудитом."""
        with self.connect() as conn:
            cursor = conn.cursor()
            prepared = _PreparedCursor(cursor, self.db_type, database=self)
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

            old_value = None
            if self.audit_enabled:
                old_value = self._fetch_old_rows(query, params)

            try:
                cursor.execute(prepared_query, prepared_params or ())
                conn.commit()

                if self.audit_enabled:
                    self._audit_log(query, params, old_value, None, success=True)

                return cursor.rowcount
            except Exception as e:
                conn.rollback()

                if self.audit_enabled:
                    self._audit_log(query, params, old_value, None, success=False, error=str(e))

                raise Exception(f"Ошибка выполнения запроса: {e}")

    def executemany(self, query, params_list):
        with self.connect() as conn:
            cursor = conn.cursor()
            prepared_query, _ = self._prepare_query_and_params(query, None)
            try:
                cursor.executemany(prepared_query, params_list)
                conn.commit()

                if self.audit_enabled:
                    self._audit_log(query, ("<batch>", len(params_list)),
                                    None, None, success=True)

                return cursor.rowcount
            except Exception as e:
                conn.rollback()

                if self.audit_enabled:
                    self._audit_log(query, ("<batch>", len(params_list)),
                                    None, None, success=False, error=str(e))

                raise Exception(f"Ошибка пакетного выполнения запроса: {e}")
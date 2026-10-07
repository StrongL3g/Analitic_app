# database/audit.py
"""
Аудит изменений в БД. Пишет лог в локальный SQLite-файл.

Хранение: <project_root>/logs/audit.db
"""

import os
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path


# ============================================================
#  Парсер SQL — вытаскивает операцию и таблицу
# ============================================================

_RE_INSERT = re.compile(r"^\s*INSERT\s+INTO\s+([\[\]\w\".]+)", re.IGNORECASE)
_RE_UPDATE = re.compile(r"^\s*UPDATE\s+([\[\]\w\".]+)", re.IGNORECASE)
_RE_DELETE = re.compile(r"^\s*DELETE\s+FROM\s+([\[\]\w\".]+)", re.IGNORECASE)


def parse_sql(query: str):
    """
    Возвращает (operation, table) или (None, None),
    если это не INSERT/UPDATE/DELETE.
    """
    q = query.strip()
    for regex, op in ((_RE_INSERT, "INSERT"), (_RE_UPDATE, "UPDATE"), (_RE_DELETE, "DELETE")):
        m = regex.match(q)
        if m:
            table = m.group(1).strip('[]"').lower()
            return op, table
    return None, None


# ============================================================
#  Хранилище
# ============================================================

class AuditLog:
    def __init__(self, project_root: Path = None):
        if project_root is None:
            # database/audit.py -> project_root = родитель папки database
            project_root = Path(__file__).resolve().parent.parent
        log_dir = project_root / "logs"
        log_dir.mkdir(exist_ok=True)
        self.db_path = log_dir / "audit.db"

        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts          TEXT NOT NULL,
                    username    TEXT,
                    role        TEXT,
                    operation   TEXT NOT NULL,
                    table_name  TEXT,
                    record_id   TEXT,
                    old_value   TEXT,
                    new_value   TEXT,
                    sql_text    TEXT,
                    success     INTEGER DEFAULT 1,
                    error       TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit(ts)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON audit(username)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_table ON audit(table_name)")
            conn.commit()

    # ---------- Запись ----------
    def write(self, *, username, role, operation, table_name,
              record_id=None, old_value=None, new_value=None,
              sql_text=None, success=True, error=None):
        """Записать одну запись. Потокобезопасно."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO audit
                        (ts, username, role, operation, table_name,
                         record_id, old_value, new_value, sql_text, success, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now().isoformat(timespec="seconds"),
                    username, role, operation, table_name,
                    None if record_id is None else str(record_id),
                    old_value, new_value, sql_text,
                    1 if success else 0,
                    error,
                ))
                conn.commit()

    # ---------- Чтение ----------
    def fetch(self, *, limit=500, username=None, table_name=None,
              operation=None, date_from=None, date_to=None):
        """Прочитать лог с фильтрами. Для страницы «Журнал»."""
        where = []
        params = []
        if username:
            where.append("username = ?")
            params.append(username)
        if table_name:
            where.append("table_name = ?")
            params.append(table_name)
        if operation:
            where.append("operation = ?")
            params.append(operation)
        if date_from:
            where.append("ts >= ?")
            params.append(date_from)
        if date_to:
            where.append("ts <= ?")
            params.append(date_to)

        sql = "SELECT * FROM audit"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def count_all(self) -> int:
        """Общее число записей в журнале."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("SELECT COUNT(*) FROM audit")
            return cur.fetchone()[0]

    # ---------- Обслуживание ----------
    def get_size_bytes(self) -> int:
        """Размер файла журнала в байтах."""
        try:
            return os.path.getsize(self.db_path)
        except OSError:
            return 0

    def purge_older_than(self, days: int) -> int:
        """Удалить записи старше N дней. Возвращает число удалённых."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="seconds")
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("DELETE FROM audit WHERE ts < ?", (cutoff,))
                conn.commit()
                deleted = cur.rowcount
                # VACUUM вернёт освободившееся место обратно на диск
                try:
                    conn.execute("VACUUM")
                except sqlite3.OperationalError:
                    pass
                return deleted

    def purge_all(self) -> int:
        """Полностью очистить журнал."""
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("DELETE FROM audit")
                conn.commit()
                deleted = cur.rowcount
                try:
                    conn.execute("VACUUM")
                except sqlite3.OperationalError:
                    pass
                return deleted


# ============================================================
#  Singleton — чтобы не открывать файл при каждом запросе
# ============================================================

_audit_singleton: AuditLog | None = None


def get_audit() -> AuditLog:
    global _audit_singleton
    if _audit_singleton is None:
        _audit_singleton = AuditLog()
    return _audit_singleton
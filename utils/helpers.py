# utils/helpers.py
from typing import Dict, Optional
from database.db import Database

# Глобальный кэш для оптимизации
_ln_name_cache: Dict[int, str] = {}
_db_instance: Optional[Database] = None

def set_database_instance(db: Database):
    """Устанавливает экземпляр БД для использования в функциях"""
    global _db_instance
    _db_instance = db

def get_ln_name(ln_nmb: int) -> str:
    """
    Получает имя линии по её номеру из SET01.

    Args:
        ln_nmb (int): Номер линии

    Returns:
        str: Имя линии или "-1" если не найдено
    """
    global _ln_name_cache, _db_instance

    # Проверяем кэш
    if ln_nmb in _ln_name_cache:
        return _ln_name_cache[ln_nmb]

    # Проверяем наличие БД
    if _db_instance is None:
        return "-1"

    try:
        # Запрашиваем имя из БД
        query = """
        SELECT [ln_name]
        FROM [AMMKASAKDB01].[dbo].[LN_SET01]
        WHERE [ln_nmb] = ? AND [ac_nmb] = 1
        """
        # Исправлено: добавлена открывающая скобка для fetch_one(
        result = _db_instance.fetch_one(query, [ln_nmb])

        if result and result.get("ln_name"):
            name = result["ln_name"]
        else:
            name = "-1"

        # Сохраняем в кэш
        _ln_name_cache[ln_nmb] = name
        return name

    except Exception as e:
        print(f"Ошибка при получении имени для ln_nmb={ln_nmb}: {e}")
        return "-1"

def clear_ln_name_cache():
    """Очищает кэш имён линий"""
    global _ln_name_cache
    _ln_name_cache.clear()

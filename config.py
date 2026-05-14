# config.py
import os
import json
from pathlib import Path
from typing import Dict, Any

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ (для импорта в другие файлы) ---
# Устанавливаем значения по умолчанию, чтобы программа не падала при импортах
AC_COUNT = 1
PR_COUNT = 8


# --- РАБОТА С ЛОКАЛЬНЫМ ФАЙЛОМ НАСТРОЕК (config.json) ---
def load_app_config():
    """Загружает настройки подключения к БД из config.json"""
    try:
        from utils.path_manager import get_config_path

        config_file = get_config_path() / "config.json"

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Если файла нет, создаем с настройками по умолчанию
            default_config = {
                "DB_TYPE": "postgres",
                "DB_HOST": "ip",
                "DB_PORT": "port",  # postgres - 5432 \ mssql - 1433
                "DB_NAME": "name",
                "DB_USER": "user",
                "DB_PASSWORD": "password",
                "DB_SERVER": "server",
                "DB_DRIVER": "ODBC Driver 18 for SQL Server"
            }
            save_app_config(default_config)
            return default_config

    except Exception as e:
        print(f"Ошибка загрузки config.json: {e}")
        return {}


def save_app_config(config: Dict[str, Any]):
    """Сохраняет настройки приложения в config.json"""
    try:
        from utils.path_manager import get_config_path
        config_file = get_config_path() / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения config.json: {e}")


def get_config(key, default=None):
    app_conf = load_app_config()
    return app_conf.get(key, default)


def set_config(key, value):
    """Сохраняет или обновляет конкретную настройку в config.json"""
    try:
        from utils.path_manager import get_config_path
        config_file = get_config_path() / "config.json"

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        config[key] = value

        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Ошибка сохранения настройки {key}: {e}")


def unset_config(key):
    """Удаляет настройку из config.json"""
    try:
        from utils.path_manager import get_config_path
        config_file = get_config_path() / "config.json"

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if key in config:
                del config[key]
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Ошибка удаления настройки {key}: {e}")


# --- ИНИЦИАЛИЗАЦИЯ ПОДКЛЮЧЕНИЯ К БД ---
_temp_conf = load_app_config()
db_type = _temp_conf.get("DB_TYPE", "mssql").lower()

if db_type == "postgres":
    DB_CONFIG = {
        "host": _temp_conf.get("DB_HOST"),
        "port": _temp_conf.get("DB_PORT", "5432"),
        "database": _temp_conf.get("DB_NAME"),
        "user": _temp_conf.get("DB_USER"),
        "password": _temp_conf.get("DB_PASSWORD"),
        "db_type": "postgres"
    }
else:  # MSSQL
    DB_CONFIG = {
        "server": _temp_conf.get("DB_SERVER"),
        "port": _temp_conf.get("DB_PORT", "1433"),
        "database": _temp_conf.get("DB_NAME"),
        "user": _temp_conf.get("DB_USER"),
        "password": _temp_conf.get("DB_PASSWORD"),
        "driver": _temp_conf.get("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
        "db_type": "mssql"
    }

def refresh_app_settings():
    """
    Обновляет глобальные переменные AC_COUNT и PR_COUNT,
    подсчитывая количество записей в новых таблицах-справочниках.
    """
    global AC_COUNT, PR_COUNT
    try:
        from database.db import Database
        db = Database(DB_CONFIG)

        # Считаем количество приборов
        res_ac = db.fetch_one("SELECT COUNT(*) as cnt FROM cfg00")
        AC_COUNT = res_ac['cnt'] if res_ac else 1

        # Считаем количество продуктов
        res_pr = db.fetch_one("SELECT COUNT(*) as cnt FROM cfg02")
        PR_COUNT = res_pr['cnt'] if res_pr else 1

        print(f"Настройки загружены из справочников: AC={AC_COUNT}, PR={PR_COUNT}")

    except Exception as e:
        print(f"Ошибка получения конфигурации из справочников (используем константы): {e}")
        AC_COUNT = 1
        PR_COUNT = 8
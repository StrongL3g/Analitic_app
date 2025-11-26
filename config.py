from dotenv import load_dotenv
import os
import json
from pathlib import Path
from typing import Dict, Any

# Загружаем переменные из .env (ТОЛЬКО ДЛЯ ЧТЕНИЯ)
load_dotenv()

# Функция для получения значения переменной (read-only) - сохраняем название
def get_config(key, default=None):
    return os.getenv(key, default)

# Функция для установки значения переменной - сохраняем название, но меняем реализацию
def set_config(key, value):
    """Сохраняет настройки в config.json вместо .env"""
    try:
        from utils.path_manager import get_config_path

        # Загружаем текущий config
        config_file = get_config_path() / "config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            config = {}

        # Обновляем значение
        config[key] = value

        # Сохраняем обратно
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        print(f"Настройка {key} сохранена в config.json")

    except Exception as e:
        print(f"Ошибка сохранения настройки {key}: {e}")

# Функция для удаления переменной - сохраняем название
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

                print(f"Настройка {key} удалена из config.json")

    except Exception as e:
        print(f"Ошибка удаления настройки {key}: {e}")

# Тип базы данных (mssql/postgres)
DB_TYPE = get_config("DB_TYPE", "mssql").lower()

# Конфигурация для разных БД
def get_db_config():
    db_type = get_config("DB_TYPE", "mssql").lower()

    if db_type == "postgres":
        return {
            "host": get_config("DB_HOST"),
            "port": get_config("DB_PORT", "5432"),
            "database": get_config("DB_NAME"),
            "user": get_config("DB_USER"),
            "password": get_config("DB_PASSWORD"),
            "db_type": "postgres"
        }
    else:  # MSSQL по умолчанию
        return {
            "server": get_config("DB_SERVER"),
            "port": get_config("DB_PORT", "1433"),
            "database": get_config("DB_NAME"),
            "user": get_config("DB_USER"),
            "password": get_config("DB_PASSWORD"),
            "driver": get_config("DB_DRIVER", "ODBC Driver 17 for SQL Server"),
            "db_type": "mssql"
        }

# Получаем конфигурацию БД
DB_CONFIG = get_db_config()

# Функция для получения конфигурации из базы данных
def get_db_settings():
    """Получает AC_COUNT и PR_COUNT из базы данных"""
    try:
        # Импортируем здесь, чтобы избежать циклической зависимости
        from database.db import Database
        db = Database(DB_CONFIG)

        query = "SELECT ac_nmb, pr_nmb FROM SET00"
        result = db.fetch_one(query)

        if result:
            return {
                "AC_COUNT": result.get('ac_nmb', 1),
                "PR_COUNT": result.get('pr_nmb', 1)
            }
        else:
            print("Предупреждение: Не найдены данные в таблице SET00")
            return {"AC_COUNT": 1, "PR_COUNT": 1}

    except Exception as e:
        print(f"Ошибка при получении конфигурации из БД: {e}")
        return {"AC_COUNT": 1, "PR_COUNT": 1}

# Функция для загрузки настроек приложения
def load_app_config():
    """Загружает настройки приложения из config.json"""
    try:
        from utils.path_manager import get_config_path

        config_file = get_config_path() / "config.json"

        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Если файла нет, создаем с настройками по умолчанию
            default_config = {"AC_COUNT": 1, "PR_COUNT": 8}
            save_app_config(default_config)
            return default_config

    except Exception as e:
        print(f"Ошибка загрузки config.json: {e}")
        return {"AC_COUNT": 1, "PR_COUNT": 8}

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

# Загружаем настройки приложения
app_config = load_app_config()

# Количество приборов и принтеров (теперь из config.json)
AC_COUNT = app_config.get("AC_COUNT", 1)
PR_COUNT = app_config.get("PR_COUNT", 8)

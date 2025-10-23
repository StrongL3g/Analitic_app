from dotenv import load_dotenv, set_key
import os

# Загружаем переменные из .env
load_dotenv()

# Функция для получения значения переменной
def get_config(key, default=None):
    return os.getenv(key, default)

# Функция для установки значения переменной
def set_config(key, value):
    os.environ[key] = str(value)
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    set_key(env_path, key, str(value))

# Функция для удаления переменной
def unset_config(key):
    if key in os.environ:
        del os.environ[key]

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

# Получаем настройки из БД
db_settings = get_db_settings()

# Количество приборов и принтеров
AC_COUNT = db_settings["AC_COUNT"]
PR_COUNT = db_settings["PR_COUNT"]


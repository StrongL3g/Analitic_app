# config.py
from dotenv import load_dotenv, set_key
import os

# Загружаем переменные из .env
load_dotenv()

# Функция для получения значения переменной
def get_config(key, default=None):
    return os.getenv(key, default)

# Функция для установки значения переменной
def set_config(key, value):
    # Обновляем значение в памяти (для текущей сессии)
    os.environ[key] = str(value)
    # Обновляем значение в файле .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    set_key(env_path, key, str(value))

# Функция для удаления переменной
def unset_config(key):
    # Удаляем значение из памяти (для текущей сессии)
    if key in os.environ:
        del os.environ[key]
    # Удаляем значение из файла .env
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    # dotenv не предоставляет прямого способа unset, поэтому перезапишем файл
    # или можно использовать unset_key если доступна
    # unset_key(env_path, key) # Если библиотека поддерживает
    # Пока просто обновим значение на пустое или удалим вручную при необходимости

# Конфигурация БД
DB_CONFIG = {
    "server": get_config("DB_SERVER"),
    "port": get_config("DB_PORT"),
    "database": get_config("DB_NAME"),
    "user": get_config("DB_USER"),
    "password": get_config("DB_PASSWORD"),
    "driver": get_config("DB_DRIVER")
}

# Количество приборов
AC_COUNT = int(get_config("AC_COUNT", 1)) # Загружаем с значением по умолчанию 1

# config.py
from dotenv import load_dotenv
import os

load_dotenv()  # Загружает .env

DB_CONFIG = {
    "server": os.getenv("DB_SERVER"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "port": 1433,
    "driver": os.getenv("DB_DRIVER")
}

# config.py
from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    "server": os.getenv("DB_SERVER"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "driver": os.getenv("DB_DRIVER")
}

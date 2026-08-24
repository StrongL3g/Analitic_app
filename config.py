# config.py
import os
import sys
import json
from pathlib import Path
from typing import Dict, Any
from cryptography.fernet import Fernet

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
AC_COUNT = 1
PR_COUNT = 8


class SecureConfigManager:
    """Менеджер для безопасного хранения конфигурации с шифрованием"""

    def __init__(self):
        if getattr(sys, 'frozen', False):
            self.base_path = Path(sys.executable).parent
        else:
            self.base_path = Path(__file__).parent

        self.config_dir = self.base_path / 'config'
        self.config_dir.mkdir(exist_ok=True)

        self.key_file = self.config_dir / 'config.key'
        self.config_file = self.config_dir / 'config.encrypted'

        self._hide_files()

    def _hide_files(self):
        """Скрывает файлы конфигурации в Windows"""
        if os.name == 'nt':
            try:
                import ctypes
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(self.config_dir))
                if attrs != -1 and not (attrs & 2):
                    ctypes.windll.kernel32.SetFileAttributesW(str(self.config_dir), attrs | 2)

                for file in self.config_dir.glob('*'):
                    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file))
                    if attrs != -1 and not (attrs & 2):
                        ctypes.windll.kernel32.SetFileAttributesW(str(file), attrs | 2)
            except:
                pass

    def _get_or_create_key(self) -> bytes:
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key

    def _get_cipher(self) -> Fernet:
        return Fernet(self._get_or_create_key())

    def load_config(self) -> Dict[str, Any]:
        try:
            if not self.config_file.exists():
                return self._create_default_config()

            cipher = self._get_cipher()
            with open(self.config_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = cipher.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode('utf-8'))

        except Exception as e:
            print(f"⚠️ Ошибка загрузки конфига: {e}")
            return self._create_default_config()

    def save_config(self, config: Dict[str, Any]):
        try:
            cipher = self._get_cipher()
            json_data = json.dumps(config, ensure_ascii=False, indent=2)
            encrypted_data = cipher.encrypt(json_data.encode('utf-8'))

            with open(self.config_file, 'wb') as f:
                f.write(encrypted_data)

            print("✅ Конфигурация сохранена")

        except Exception as e:
            print(f"❌ Ошибка сохранения конфига: {e}")

    def _create_default_config(self) -> Dict[str, Any]:
        default_config = {
            "DB_TYPE": "mssql",
            "DB_HOST": "localhost",
            "DB_PORT": "1433",
            "DB_NAME": "database_name",
            "DB_USER": "username",
            "DB_PASSWORD": "password",
            "DB_SERVER": "server_name",
            "DB_DRIVER": "ODBC Driver 18 for SQL Server",
            "THEME": "Системная",
            "CUSTOM_BG": "#ffffff",
            "CUSTOM_TEXT": "#000000",
            "CUSTOM_ACCENT": "#2196F3"
        }
        self.save_config(default_config)
        return default_config

    def get(self, key: str, default=None):
        config = self.load_config()
        return config.get(key, default)

    def set(self, key: str, value: Any):
        config = self.load_config()
        config[key] = value
        self.save_config(config)

    def get_db_config(self) -> Dict[str, Any]:
        config = self.load_config()
        db_type = config.get("DB_TYPE", "mssql").lower()

        if db_type == "postgres":
            return {
                "host": config.get("DB_HOST"),
                "port": config.get("DB_PORT", "5432"),
                "database": config.get("DB_NAME"),
                "user": config.get("DB_USER"),
                "password": config.get("DB_PASSWORD"),
                "db_type": "postgres"
            }
        else:
            return {
                "server": config.get("DB_SERVER"),
                "port": config.get("DB_PORT", "1433"),
                "database": config.get("DB_NAME"),
                "user": config.get("DB_USER"),
                "password": config.get("DB_PASSWORD"),
                "driver": config.get("DB_DRIVER", "ODBC Driver 18 for SQL Server"),
                "db_type": "mssql"
            }


# --- ИНИЦИАЛИЗАЦИЯ ---
_secure_manager = SecureConfigManager()


# --- ОСНОВНЫЕ ФУНКЦИИ ---
def get_config(key, default=None):
    """Получает настройку"""
    return _secure_manager.get(key, default)


def set_config(key, value):
    """Устанавливает настройку"""
    _secure_manager.set(key, value)


# --- ФУНКЦИИ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ ---
def load_app_config():
    """Устаревшая функция. Используйте get_config()"""
    return _secure_manager.load_config()


def save_app_config(config):
    """Устаревшая функция. Используйте set_config()"""
    _secure_manager.save_config(config)


def unset_config(key):
    """Удаляет настройку"""
    config = _secure_manager.load_config()
    if key in config:
        del config[key]
        _secure_manager.save_config(config)


# --- КОНФИГ ДЛЯ БД ---
DB_CONFIG = _secure_manager.get_db_config()


def refresh_app_settings():
    """Обновляет глобальные переменные AC_COUNT и PR_COUNT"""
    global AC_COUNT, PR_COUNT
    try:
        from database.db import Database
        db = Database(DB_CONFIG)

        res_ac = db.fetch_one("SELECT COUNT(*) as cnt FROM cfg00")
        AC_COUNT = res_ac['cnt'] if res_ac else 1

        res_pr = db.fetch_one("SELECT COUNT(*) as cnt FROM cfg02")
        PR_COUNT = res_pr['cnt'] if res_pr else 1

        print(f"✅ Настройки загружены: AC={AC_COUNT}, PR={PR_COUNT}")

    except Exception as e:
        print(f"⚠️ Ошибка загрузки настроек: {e}")
        AC_COUNT = 1
        PR_COUNT = 8


if __name__ == "__main__":
    print("Тестирование SecureConfigManager")
    print(f"DB_CONFIG: {DB_CONFIG}")
    print(f"THEME: {get_config('THEME')}")
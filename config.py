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
        # Определяем базовый путь для EXE или скрипта
        if getattr(sys, 'frozen', False):
            self.base_path = Path(sys.executable).parent
        else:
            self.base_path = Path(__file__).parent

        self.config_dir = self.base_path / 'config'
        self.config_dir.mkdir(exist_ok=True)

        # Файлы для хранения
        self.key_file = self.config_dir / 'config.key'
        self.config_file = self.config_dir / 'config.encrypted'

        # Маска для файлов (скрытые)
        self._hide_files()

    def _hide_files(self):
        """Скрывает файлы конфигурации в Windows"""
        if os.name == 'nt':
            try:
                import ctypes
                # Скрываем директорию config
                attrs = ctypes.windll.kernel32.GetFileAttributesW(str(self.config_dir))
                if attrs != -1 and not (attrs & 2):  # 2 = FILE_ATTRIBUTE_HIDDEN
                    ctypes.windll.kernel32.SetFileAttributesW(str(self.config_dir), attrs | 2)

                # Скрываем файлы внутри
                for file in self.config_dir.glob('*'):
                    attrs = ctypes.windll.kernel32.GetFileAttributesW(str(file))
                    if attrs != -1 and not (attrs & 2):
                        ctypes.windll.kernel32.SetFileAttributesW(str(file), attrs | 2)
            except:
                pass  # Если не удалось скрыть - просто игнорируем

    def _get_or_create_key(self) -> bytes:
        """Получает или создает ключ шифрования"""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            return key

    def _get_cipher(self) -> Fernet:
        """Возвращает объект шифра"""
        return Fernet(self._get_or_create_key())

    def load_config(self) -> Dict[str, Any]:
        """Загружает зашифрованную конфигурацию"""
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
        """Сохраняет зашифрованную конфигурацию"""
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
        """Создает конфигурацию по умолчанию"""
        default_config = {
            "DB_TYPE": "mssql",  # или postgres
            "DB_HOST": "localhost",
            "DB_PORT": "1433",  # для mssql
            "DB_NAME": "database_name",
            "DB_USER": "username",
            "DB_PASSWORD": "password",
            "DB_SERVER": "server_name",
            "DB_DRIVER": "ODBC Driver 18 for SQL Server"
        }
        self.save_config(default_config)
        return default_config

    def get(self, key: str, default=None):
        """Получает значение конкретной настройки"""
        config = self.load_config()
        return config.get(key, default)

    def set(self, key: str, value: Any):
        """Устанавливает значение конкретной настройки"""
        config = self.load_config()
        config[key] = value
        self.save_config(config)

    def get_db_config(self) -> Dict[str, Any]:
        """Получает конфигурацию для подключения к БД"""
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
        else:  # MSSQL
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


# Глобальные переменные для обратной совместимости
def get_config(key, default=None):
    """Получает настройку"""
    return _secure_manager.get(key, default)


def set_config(key, value):
    """Устанавливает настройку"""
    _secure_manager.set(key, value)


# Конфиг для БД
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


# Для тестирования
if __name__ == "__main__":
    print("Тестирование SecureConfigManager")
    print(f"DB_CONFIG: {DB_CONFIG}")

    # Пример сохранения
    set_config("DB_HOST", "192.168.1.100")
    print(f"DB_HOST: {get_config('DB_HOST')}")
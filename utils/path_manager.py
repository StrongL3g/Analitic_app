# utils/path_manager.py
import os
import sys
import json
from pathlib import Path

class PathManager:
    def __init__(self):
        self._base_path = None
        self._config_path = None
        self._ensure_paths()

    def _ensure_paths(self):
        """Определяет базовые пути и создает необходимые директории"""
        if getattr(sys, 'frozen', False):
            # Режим собранного приложения
            self._base_path = Path(sys._MEIPASS)
            # Для записи данных используем директорию рядом с исполняемым файлом
            self._app_data_path = Path(os.path.dirname(sys.executable))
        else:
            # Режим разработки
            self._base_path = Path(__file__).parent.parent
            self._app_data_path = self._base_path

        # Создаем необходимые директории
        self._ensure_directories()

    def _ensure_directories(self):
        """Создает необходимые директории для данных"""
        directories = [
            self.get_config_path(),
            self.get_data_path(),
            self.get_logs_path()
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def get_base_path(self) -> Path:
        """Возвращает базовый путь (для чтения ресурсов)"""
        return self._base_path

    def get_app_data_path(self) -> Path:
        """Возвращает путь для записи данных (конфиги, JSON и т.д.)"""
        return self._app_data_path

    def get_config_path(self) -> Path:
        """Возвращает путь к конфигурационным файлам"""
        return self._app_data_path / "config"

    def get_data_path(self) -> Path:
        """Возвращает путь для хранения данных"""
        return self._app_data_path / "data"

    def get_logs_path(self) -> Path:
        """Возвращает путь для логов"""
        return self._app_data_path / "logs"

    def get_resource_path(self, relative_path: str) -> Path:
        """Возвращает полный путь к ресурсу (для чтения)"""
        return self._base_path / relative_path

    def get_writable_path(self, relative_path: str) -> Path:
        """Возвращает полный путь для записи данных"""
        return self._app_data_path / relative_path

# Глобальный экземпляр
path_manager = PathManager()

# Удобные функции-алиасы
def get_config_path() -> Path:
    return path_manager.get_config_path()

def get_data_path() -> Path:
    return path_manager.get_data_path()

def get_resource_path(relative_path: str) -> Path:
    return path_manager.get_resource_path(relative_path)

def get_writable_path(relative_path: str) -> Path:
    return path_manager.get_writable_path(relative_path)

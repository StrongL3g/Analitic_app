# views/settings.py
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QLineEdit, QPushButton, QMessageBox, QGroupBox, QFormLayout, QComboBox, QInputDialog
)
from PySide6.QtCore import Qt
from database.db import Database
from config import load_app_config, save_app_config
from utils.path_manager import get_config_path


class SettingsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        # Путь к файлу пресетов будет рядом с config.json
        self.presets_file = get_config_path() / "presets.json"
        self.presets = {}

        self.init_ui()
        self.load_presets()
        self.load_current_settings()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Настройки подключения к базе данных")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Группа управления пресетами ---
        preset_group = QGroupBox("Пресеты подключений")
        preset_layout = QHBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("--- Выберите пресет ---")
        self.preset_combo.currentIndexChanged.connect(self.apply_preset)
        self.preset_combo.setMinimumWidth(250)
        preset_layout.addWidget(self.preset_combo)

        save_preset_btn = QPushButton("Сохранить как пресет")
        save_preset_btn.clicked.connect(self.save_preset)
        preset_layout.addWidget(save_preset_btn)

        del_preset_btn = QPushButton("Удалить пресет")
        del_preset_btn.setStyleSheet("background-color: #ffcdd2;")
        del_preset_btn.clicked.connect(self.delete_preset)
        preset_layout.addWidget(del_preset_btn)

        preset_layout.addStretch()
        preset_group.setLayout(preset_layout)
        layout.addWidget(preset_group)

        # --- Форма параметров БД ---
        db_group = QGroupBox("Параметры подключения (config.json)")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.db_type = QComboBox()
        self.db_type.addItems(["mssql", "postgres"])
        self.db_type.setFixedWidth(300)

        self.db_host = QLineEdit()
        self.db_host.setFixedWidth(300)

        self.db_port = QLineEdit()
        self.db_port.setFixedWidth(300)

        self.db_name = QLineEdit()
        self.db_name.setFixedWidth(300)

        self.db_user = QLineEdit()
        self.db_user.setFixedWidth(300)

        self.db_pass = QLineEdit()
        self.db_pass.setFixedWidth(300)
        self.db_pass.setEchoMode(QLineEdit.Password)  # Скрываем пароль звездочками

        self.db_driver = QLineEdit()
        self.db_driver.setFixedWidth(300)

        form_layout.addRow("Тип БД:", self.db_type)
        form_layout.addRow("Хост / Сервер (IP):", self.db_host)
        form_layout.addRow("Порт:", self.db_port)
        form_layout.addRow("Имя базы данных:", self.db_name)
        form_layout.addRow("Пользователь:", self.db_user)
        form_layout.addRow("Пароль:", self.db_pass)
        form_layout.addRow("ODBC Драйвер (только для MSSQL):", self.db_driver)

        db_group.setLayout(form_layout)
        layout.addWidget(db_group)

        # --- Кнопки управления ---
        btn_layout = QHBoxLayout()
        test_btn = QPushButton("Проверить подключение")
        test_btn.clicked.connect(self.test_connection)
        test_btn.setFixedWidth(200)

        save_btn = QPushButton("Сохранить настройки")
        save_btn.setStyleSheet("background-color: #c8e6c9; font-weight: bold;")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setFixedWidth(200)

        btn_layout.addWidget(test_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Информация ---
        info_label = QLabel(
            "<b>Внимание:</b> После сохранения новых настроек БД "
            "необходимо перезапустить приложение, чтобы они вступили в силу!"
        )
        info_label.setStyleSheet("color: #d32f2f; padding-top: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        self.setLayout(layout)

    def load_current_settings(self):
        """Загружает текущие настройки из config.json в форму"""
        config = load_app_config()

        db_type = config.get("DB_TYPE", "mssql").lower()
        self.db_type.setCurrentText(db_type)

        # Для MSSQL в старом конфиге использовался DB_SERVER, для Postgres - DB_HOST
        host = config.get("DB_SERVER") if db_type == "mssql" else config.get("DB_HOST")
        self.db_host.setText(host or config.get("DB_HOST") or "")

        self.db_port.setText(config.get("DB_PORT", ""))
        self.db_name.setText(config.get("DB_NAME", ""))
        self.db_user.setText(config.get("DB_USER", ""))
        self.db_pass.setText(config.get("DB_PASSWORD", ""))
        self.db_driver.setText(config.get("DB_DRIVER", "ODBC Driver 18 for SQL Server"))

    def get_form_data(self):
        """Считывает данные с формы и формирует словарь"""
        db_type = self.db_type.currentText()
        host = self.db_host.text().strip()

        return {
            "DB_TYPE": db_type,
            "DB_HOST": host,  # Пишем в оба поля, чтобы не было путаницы
            "DB_SERVER": host,  # Пишем в оба поля, чтобы не было путаницы
            "DB_PORT": self.db_port.text().strip(),
            "DB_NAME": self.db_name.text().strip(),
            "DB_USER": self.db_user.text().strip(),
            "DB_PASSWORD": self.db_pass.text().strip(),
            "DB_DRIVER": self.db_driver.text().strip()
        }

    def load_presets(self):
        """Загружает пресеты из presets.json"""
        self.presets = {}
        if self.presets_file.exists():
            try:
                with open(self.presets_file, 'r', encoding='utf-8') as f:
                    self.presets = json.load(f)
            except Exception as e:
                print(f"Ошибка чтения пресетов: {e}")

        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("--- Выберите пресет ---")
        for name in self.presets.keys():
            self.preset_combo.addItem(name)
        self.preset_combo.blockSignals(False)

    def apply_preset(self, index):
        """Применяет выбранный пресет к полям формы"""
        if index <= 0: return
        preset_name = self.preset_combo.currentText()
        preset = self.presets.get(preset_name, {})

        db_type = preset.get("DB_TYPE", "mssql").lower()
        self.db_type.setCurrentText(db_type)

        host = preset.get("DB_SERVER") if db_type == "mssql" else preset.get("DB_HOST")
        self.db_host.setText(host or "")

        self.db_port.setText(preset.get("DB_PORT", ""))
        self.db_name.setText(preset.get("DB_NAME", ""))
        self.db_user.setText(preset.get("DB_USER", ""))
        self.db_pass.setText(preset.get("DB_PASSWORD", ""))
        self.db_driver.setText(preset.get("DB_DRIVER", "ODBC Driver 18 for SQL Server"))

    def save_preset(self):
        """Сохраняет текущие данные формы как новый пресет"""
        name, ok = QInputDialog.getText(self, "Сохранить пресет", "Введите название пресета:")
        if ok and name.strip():
            name = name.strip()
            self.presets[name] = self.get_form_data()
            try:
                with open(self.presets_file, 'w', encoding='utf-8') as f:
                    json.dump(self.presets, f, ensure_ascii=False, indent=4)
                self.load_presets()
                self.preset_combo.setCurrentText(name)
                QMessageBox.information(self, "Успех", f"Пресет '{name}' успешно сохранен!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить пресет: {e}")

    def delete_preset(self):
        """Удаляет выбранный пресет"""
        index = self.preset_combo.currentIndex()
        if index <= 0: return
        name = self.preset_combo.currentText()

        reply = QMessageBox.question(self, "Подтверждение", f"Удалить пресет '{name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if name in self.presets:
                del self.presets[name]
                try:
                    with open(self.presets_file, 'w', encoding='utf-8') as f:
                        json.dump(self.presets, f, ensure_ascii=False, indent=4)
                    self.load_presets()
                    QMessageBox.information(self, "Успех", f"Пресет '{name}' удален.")
                except Exception as e:
                    QMessageBox.critical(self, "Ошибка", f"Не удалось удалить пресет: {e}")

    def test_connection(self):
        """Создает временное подключение с введенными данными для проверки"""
        data = self.get_form_data()
        db_type = data["DB_TYPE"].lower()

        if db_type == "postgres":
            test_config = {
                "host": data["DB_HOST"],
                "port": data["DB_PORT"] or "5432",
                "database": data["DB_NAME"],
                "user": data["DB_USER"],
                "password": data["DB_PASSWORD"],
                "db_type": "postgres"
            }
        else:
            test_config = {
                "server": data["DB_SERVER"],
                "port": data["DB_PORT"] or "1433",
                "database": data["DB_NAME"],
                "user": data["DB_USER"],
                "password": data["DB_PASSWORD"],
                "driver": data["DB_DRIVER"],
                "db_type": "mssql"
            }

        temp_db = Database(test_config)
        try:
            # Пытаемся открыть и сразу закрыть соединение
            with temp_db.connect():
                pass
            QMessageBox.information(self, "Успех", "Подключение успешно установлено!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", f"Не удалось подключиться к БД:\n\n{e}")

    def save_settings(self):
        """Сохраняет настройки в главный config.json"""
        data = self.get_form_data()
        try:
            save_app_config(data)
            QMessageBox.information(
                self, "Настройки сохранены",
                "Конфигурация базы данных успешно сохранена в config.json!\n\n"
                "Пожалуйста, перезапустите приложение для применения новых настроек."
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {e}")
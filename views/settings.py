# views/settings.py
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QLineEdit,
    QPushButton, QMessageBox, QGroupBox, QFormLayout, QComboBox,
    QInputDialog, QColorDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.db import Database
from config import load_app_config, save_app_config
from utils.path_manager import get_config_path


class SettingsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.presets_file = get_config_path() / "presets.json"
        self.presets = {}

        # Кастомные цвета по умолчанию
        self.custom_bg = "#ffffff"
        self.custom_text = "#000000"
        self.custom_accent = "#2196F3"

        self.init_ui()
        self.load_presets()
        self.load_current_settings()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Настройки системы")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # =====================================================================
        # 1. ГРУППА: ВНЕШНИЙ ВИД И ЦВЕТОВАЯ ГАММА
        # =====================================================================
        theme_group = QGroupBox("Внешний вид и интерфейс")
        theme_layout = QFormLayout()
        theme_layout.setLabelAlignment(Qt.AlignLeft)

        self.theme_selector = QComboBox()
        self.theme_selector.addItems(["Системная", "Светлая", "Тёмная", "Кастомная"])
        self.theme_selector.setFixedWidth(300)
        self.theme_selector.currentIndexChanged.connect(self.toggle_custom_color_inputs)
        theme_layout.addRow("Цветовая палитра:", self.theme_selector)

        # Контейнер для кнопок выбора кастомных цветов
        self.custom_colors_widget = QWidget()
        custom_colors_layout = QVBoxLayout(self.custom_colors_widget)
        custom_colors_layout.setContentsMargins(0, 5, 0, 5)
        custom_colors_layout.setSpacing(8)

        # Кнопка Цвет фона
        h_bg_layout = QHBoxLayout()
        self.btn_bg_color = QPushButton("Выбрать цвет")
        self.btn_bg_color.setFixedWidth(150)
        self.btn_bg_color.clicked.connect(lambda: self.pick_color("bg"))
        self.lbl_bg_preview = QLabel("Текст")
        self.lbl_bg_preview.setFixedWidth(140)
        self.lbl_bg_preview.setAlignment(Qt.AlignCenter)
        h_bg_layout.addWidget(self.btn_bg_color)
        h_bg_layout.addWidget(self.lbl_bg_preview)
        custom_colors_layout.addLayout(h_bg_layout)

        # Кнопка Цвет текста
        h_text_layout = QHBoxLayout()
        self.btn_text_color = QPushButton("Выбрать цвет")
        self.btn_text_color.setFixedWidth(150)
        self.btn_text_color.clicked.connect(lambda: self.pick_color("text"))
        self.lbl_text_preview = QLabel("Пример текста")
        self.lbl_text_preview.setFixedWidth(140)
        self.lbl_text_preview.setAlignment(Qt.AlignCenter)
        h_text_layout.addWidget(self.btn_text_color)
        h_text_layout.addWidget(self.lbl_text_preview)
        custom_colors_layout.addLayout(h_text_layout)

        # Кнопка Акцентный цвет
        h_accent_layout = QHBoxLayout()
        self.btn_accent_color = QPushButton("Выбрать цвет")
        self.btn_accent_color.setFixedWidth(150)
        self.btn_accent_color.clicked.connect(lambda: self.pick_color("accent"))
        self.lbl_accent_preview = QLabel("Кнопки / Элементы")
        self.lbl_accent_preview.setFixedWidth(140)
        self.lbl_accent_preview.setAlignment(Qt.AlignCenter)
        h_accent_layout.addWidget(self.btn_accent_color)
        h_accent_layout.addWidget(self.lbl_accent_preview)
        custom_colors_layout.addLayout(h_accent_layout)

        theme_layout.addRow("", self.custom_colors_widget)
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        # =====================================================================
        # 2. ГРУППА: ПРЕСЕТЫ ПОДКЛЮЧЕНИЙ К БД
        # =====================================================================
        preset_group = QGroupBox("Пресеты подключений к БД")
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

        # =====================================================================
        # 3. ГРУППА: ПАРАМЕТРЫ ПОДКЛЮЧЕНИЯ
        # =====================================================================
        db_group = QGroupBox("Параметры текущего подключения к БД")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignLeft)

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
        self.db_pass.setEchoMode(QLineEdit.Password)

        self.db_driver = QLineEdit()
        self.db_driver.setFixedWidth(300)

        form_layout.addRow("Тип СУБД:", self.db_type)
        form_layout.addRow("Хост / Сервер (IP):", self.db_host)
        form_layout.addRow("Порт:", self.db_port)
        form_layout.addRow("Имя базы данных:", self.db_name)
        form_layout.addRow("Пользователь:", self.db_user)
        form_layout.addRow("Пароль:", self.db_pass)
        form_layout.addRow("ODBC Драйвер (для MSSQL):", self.db_driver)

        db_group.setLayout(form_layout)
        layout.addWidget(db_group)

        # --- Кнопки сохранения ---
        btn_layout = QHBoxLayout()
        test_btn = QPushButton("Проверить подключение")
        test_btn.clicked.connect(self.test_connection)
        test_btn.setFixedWidth(200)

        save_btn = QPushButton("Сохранить всё")
        save_btn.setStyleSheet("background-color: #c8e6c9; font-weight: bold;")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setFixedWidth(200)

        btn_layout.addWidget(test_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        info_label = QLabel(
            "<b>Важно:</b> Новые параметры базы данных и стили оформления вступят в силу после перезапуска приложения.")
        info_label.setStyleSheet("color: #d32f2f; padding-top: 5px;")
        layout.addWidget(info_label)

        layout.addStretch()

    def toggle_custom_color_inputs(self):
        """Показывает или скрывает настройку цветов в зависимости от выбранного режима"""
        is_custom = self.theme_selector.currentText() == "Кастомная"
        self.custom_colors_widget.setVisible(is_custom)

    def update_color_previews(self):
        """Обновляет плашки предпросмотра выбранных кастомных цветов"""
        self.lbl_bg_preview.setStyleSheet(
            f"background-color: {self.custom_bg}; border: 1px solid #777; border-radius: 3px;")
        self.lbl_text_preview.setStyleSheet(
            f"background-color: {self.custom_bg}; color: {self.custom_text}; border: 1px solid #777; border-radius: 3px;")
        self.lbl_accent_preview.setStyleSheet(
            f"background-color: {self.custom_accent}; color: #ffffff; font-weight: bold; border-radius: 3px;")

    def pick_color(self, target):
        """Открывает палитру для выбора цвета"""
        current_hex = self.custom_bg if target == "bg" else (
            self.custom_text if target == "text" else self.custom_accent)
        color = QColorDialog.getColor(QColor(current_hex), self, "Выберите цвет")

        if color.isValid():
            hex_name = color.name()
            if target == "bg":
                self.custom_bg = hex_name
            elif target == "text":
                self.custom_text = hex_name
            elif target == "accent":
                self.custom_accent = hex_name
            self.update_color_previews()

    def load_current_settings(self):
        """Загружает текущую конфигурацию из config.json"""
        config = load_app_config()

        # Загрузка темы
        current_theme = config.get("THEME", "Системная")
        self.theme_selector.setCurrentText(current_theme)

        self.custom_bg = config.get("CUSTOM_BG", "#ffffff")
        self.custom_text = config.get("CUSTOM_TEXT", "#000000")
        self.custom_accent = config.get("CUSTOM_ACCENT", "#2196F3")
        self.update_color_previews()
        self.toggle_custom_color_inputs()

        # Загрузка параметров БД
        db_type = config.get("DB_TYPE", "mssql").lower()
        self.db_type.setCurrentText(db_type)
        host = config.get("DB_SERVER") if db_type == "mssql" else config.get("DB_HOST")
        self.db_host.setText(host or config.get("DB_HOST") or "")
        self.db_port.setText(config.get("DB_PORT", ""))
        self.db_name.setText(config.get("DB_NAME", ""))
        self.db_user.setText(config.get("DB_USER", ""))
        self.db_pass.setText(config.get("DB_PASSWORD", ""))
        self.db_driver.setText(config.get("DB_DRIVER", "ODBC Driver 18 for SQL Server"))

    def get_form_data(self):
        db_type = self.db_type.currentText()
        host = self.db_host.text().strip()

        # Собираем данные БД и данные оформления вместе
        return {
            "THEME": self.theme_selector.currentText(),
            "CUSTOM_BG": self.custom_bg,
            "CUSTOM_TEXT": self.custom_text,
            "CUSTOM_ACCENT": self.custom_accent,
            "DB_TYPE": db_type,
            "DB_HOST": host,
            "DB_SERVER": host,
            "DB_PORT": self.db_port.text().strip(),
            "DB_NAME": self.db_name.text().strip(),
            "DB_USER": self.db_user.text().strip(),
            "DB_PASSWORD": self.db_pass.text().strip(),
            "DB_DRIVER": self.db_driver.text().strip()
        }

    def load_presets(self):
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
            with temp_db.connect():
                pass
            QMessageBox.information(self, "Успех", "Подключение успешно установлено!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка подключения", f"Не удалось подключиться к БД:\n\n{e}")

    def save_settings(self):
        data = self.get_form_data()
        try:
            # Читаем старый конфиг, чтобы не затереть AC_COUNT и PR_COUNT
            old_config = load_app_config()
            old_config.update(data)

            save_app_config(old_config)
            QMessageBox.information(
                self, "Успех",
                "Все настройки успешно зафиксированы!\n\n"
                "Пожалуйста, перезапустите систему для полного переключения цветовой схемы и параметров БД."
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить настройки: {e}")
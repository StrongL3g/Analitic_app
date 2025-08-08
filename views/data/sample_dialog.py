# views/data/sample_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QLineEdit, QDateTimeEdit, QMessageBox
)
from PySide6.QtCore import Qt, QDateTime
from database.db import Database
import datetime

import json
import os
from typing import List, Dict


class SampleDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Формирование выборки")
        self.resize(800, 600)

        # Храним данные выборки
        self.sample_data = []

        self.init_ui()
        self.load_products()

        # Загружаем существующую выборку
        self.load_sample_from_file()

    def init_ui(self):
        layout = QVBoxLayout()

        # === Панель добавления ===
        add_group = QLabel("Добавить продукт в выборку:")
        add_group.setStyleSheet("font-weight: bold;")
        layout.addWidget(add_group)

        # Элементы выбора
        form_layout = QFormLayout()

        # Кнопка "Добавить продукт"
        self.btn_add_product = QPushButton("Добавить продукт")
        self.btn_add_product.clicked.connect(self.add_product)

        # Выбор даты и времени "от"
        self.date_from = QDateTimeEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.time_from = QDateTimeEdit()
        self.time_from.setDisplayFormat("HH:mm")
        self.time_from.setCalendarPopup(False)

        # Установим значения по умолчанию (текущая дата и время)
        now = QDateTime.currentDateTime()
        self.date_from.setDateTime(now)
        self.time_from.setDateTime(now)

        # Выбор даты и времени "до"
        self.date_to = QDateTimeEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.time_to = QDateTimeEdit()
        self.time_to.setDisplayFormat("HH:mm")
        self.time_to.setCalendarPopup(False)

        # Установим значения по умолчанию (через 1 день)
        tomorrow = now.addDays(1)
        self.date_to.setDateTime(tomorrow)
        self.time_to.setDateTime(now)

        # Комбобокс с продуктами
        self.combo_products = QComboBox()

        # Добавляем элементы в форму
        form_layout.addRow("Продукт:", self.combo_products)
        form_layout.addRow("Дата от:", self.date_from)
        form_layout.addRow("Время от:", self.time_from)
        form_layout.addRow("Дата до:", self.date_to)
        form_layout.addRow("Время до:", self.time_to)
        form_layout.addRow("", self.btn_add_product)

        layout.addLayout(form_layout)

        # === Таблица выборки ===
        layout.addWidget(QLabel("Текущая выборка:"))

        self.table_sample = QTableWidget()
        self.table_sample.setColumnCount(6)
        self.table_sample.setHorizontalHeaderLabels([
            "№ продукта", "Дата от", "Время от", "Дата до", "Время до", "Действия"
        ])
        self.table_sample.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table_sample)

        # === Кнопки управления ===
        btn_layout = QHBoxLayout()
        self.btn_ok = QPushButton("ОК")
        self.btn_cancel = QPushButton("Отмена")
        self.btn_clear = QPushButton("Очистить")

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_clear.clicked.connect(self.clear_sample)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_clear)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def load_products(self):
        """Загружает список продуктов из базы данных"""
        try:
            # TODO: Заменить на реальный запрос к таблице продуктов
            # Пока используем тестовые данные
            products = [
                (1, "Продукт 1"),
                (2, "Продукт 2"),
                (3, "Продукт 3"),
                (4, "Продукт 4"),
                (5, "Продукт 5"),
                (6, "Продукт 6"),
                (7, "Продукт 7"),
                (8, "Продукт 8")
            ]

            self.combo_products.clear()
            for product_id, product_name in products:
                self.combo_products.addItem(f"{product_id} - {product_name}", product_id)

        except Exception as e:
            print(f"Ошибка загрузки продуктов: {e}")
            # В случае ошибки добавим тестовые значения
            self.combo_products.clear()
            for i in range(1, 6):
                self.combo_products.addItem(f"{i} - Тестовый продукт {i}", i)

    def add_product(self):
        """Добавляет продукт в таблицу выборки"""
        # Проверяем ограничения
        if len(self.sample_data) >= 100:
            QMessageBox.warning(self, "Ошибка", "Максимальное количество строк: 100")
            return

        # Получаем данные
        product_id = self.combo_products.currentData()
        product_text = self.combo_products.currentText()

        date_from = self.date_from.date().toString("dd.MM.yyyy")
        time_from = self.time_from.time().toString("HH:mm")

        date_to = self.date_to.date().toString("dd.MM.yyyy")
        time_to = self.time_to.time().toString("HH:mm")

        # Проверяем, что дата/время "до" больше дата/время "от"
        datetime_from = QDateTime(self.date_from.date(), self.time_from.time())
        datetime_to = QDateTime(self.date_to.date(), self.time_to.time())

        if datetime_to <= datetime_from:
            QMessageBox.warning(self, "Ошибка",
                "Дата/время 'до' должна быть больше дата/время 'от'")
            return

        # Добавляем в таблицу
        row = self.table_sample.rowCount()
        self.table_sample.insertRow(row)

        # Заполняем ячейки
        self.table_sample.setItem(row, 0, QTableWidgetItem(str(product_id)))
        self.table_sample.setItem(row, 1, QTableWidgetItem(date_from))
        self.table_sample.setItem(row, 2, QTableWidgetItem(time_from))
        self.table_sample.setItem(row, 3, QTableWidgetItem(date_to))
        self.table_sample.setItem(row, 4, QTableWidgetItem(time_to))

        # Кнопка удаления
        btn_delete = QPushButton("Удалить")
        btn_delete.clicked.connect(lambda _, r=row: self.delete_row(r))
        self.table_sample.setCellWidget(row, 5, btn_delete)

        # Сохраняем данные
        self.sample_data.append({
            'product_id': product_id,
            'product_text': product_text,
            'date_from': date_from,
            'time_from': time_from,
            'date_to': date_to,
            'time_to': time_to
        })

        print(f"Добавлен продукт: {product_text}, {date_from} {time_from} - {date_to} {time_to}")

    def delete_row(self, row):
        """Удаляет строку из таблицы"""
        if 0 <= row < self.table_sample.rowCount():
            self.table_sample.removeRow(row)
            if row < len(self.sample_data):
                del self.sample_data[row]
            # Обновляем индексы кнопок удаления
            self.update_delete_buttons()

    def update_delete_buttons(self):
        """Обновляет обработчики событий для кнопок удаления"""
        for row in range(self.table_sample.rowCount()):
            btn_delete = self.table_sample.cellWidget(row, 5)
            if btn_delete:
                # Отключаем старый обработчик
                try:
                    btn_delete.clicked.disconnect()
                except:
                    pass
                # Подключаем новый обработчик
                btn_delete.clicked.connect(lambda _, r=row: self.delete_row(r))

    def clear_sample(self):
        """Очищает всю выборку"""
        self.table_sample.setRowCount(0)
        self.sample_data.clear()

    def get_sample_data(self):
        """Возвращает данные выборки"""
        return self.sample_data

    def load_sample_from_file(self):
        """Загружает выборку из файла"""
        try:
            if os.path.exists("config/sample.json"):
                with open("config/sample.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.sample_data = data
                        self.update_table_from_data()
        except Exception as e:
            print(f"Ошибка загрузки выборки из файла: {e}")

    def save_sample_to_file(self):
        """Сохраняет выборку в файл"""
        try:
            os.makedirs("config", exist_ok=True)
            with open("config/sample.json", "w", encoding="utf-8") as f:
                json.dump(self.sample_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения выборки в файл: {e}")

    def accept(self):
        """Переопределяем метод accept для сохранения данных"""
        self.save_sample_to_file()
        super().accept()

    def update_table_from_data(self):
        """Обновляет таблицу на основе данных выборки"""
        self.table_sample.setRowCount(0)
        for item in self.sample_data:
            row = self.table_sample.rowCount()
            self.table_sample.insertRow(row)

            self.table_sample.setItem(row, 0, QTableWidgetItem(str(item['product_id'])))
            self.table_sample.setItem(row, 1, QTableWidgetItem(item['date_from']))
            self.table_sample.setItem(row, 2, QTableWidgetItem(item['time_from']))
            self.table_sample.setItem(row, 3, QTableWidgetItem(item['date_to']))
            self.table_sample.setItem(row, 4, QTableWidgetItem(item['time_to']))

            # Кнопка удаления
            btn_delete = QPushButton("Удалить")
            # Используем замыкание для правильной передачи row
            btn_delete.clicked.connect(self.make_delete_handler(row))
            self.table_sample.setCellWidget(row, 5, btn_delete)

    def make_delete_handler(self, row):
        """Фабрика обработчиков удаления строк"""
        return lambda: self.delete_row(row)

# views/data/sample_dialog.py
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QDateTimeEdit, QMessageBox, QWidget, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, QDateTime, QTime
from database.db import Database

import json
import os
from typing import List, Dict
from utils.path_manager import get_config_path


class SampleDialog(QDialog):
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Формирование выборки")
        self.resize(850, 600)

        # Храним данные выборки
        self.sample_data = []
        self.editing_row = None  # Флаг для режима редактирования

        self.init_ui()
        self.load_products()

        # Загружаем существующую выборку
        self.load_sample_from_file()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # === Панель добавления / редактирования ===
        self.lbl_mode = QLabel("Добавление новой выборки:")
        self.lbl_mode.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        main_layout.addWidget(self.lbl_mode)

        form_layout = QFormLayout()

        # Комбобокс с продуктами
        self.combo_products = QComboBox()
        self.combo_products.setMinimumWidth(300)

        # Выбор даты и времени (Объединенные виджеты)
        self.datetime_from = QDateTimeEdit()
        self.datetime_from.setCalendarPopup(True)
        self.datetime_from.setDisplayFormat("dd.MM.yyyy HH:mm")

        self.datetime_to = QDateTimeEdit()
        self.datetime_to.setCalendarPopup(True)
        self.datetime_to.setDisplayFormat("dd.MM.yyyy HH:mm")

        # Кнопки быстрых периодов
        quick_btn_layout = QHBoxLayout()
        btn_today = QPushButton("За сегодня")
        btn_yesterday = QPushButton("Вчера")
        btn_3days = QPushButton("За 3 дня")
        btn_week = QPushButton("За неделю")

        btn_today.clicked.connect(lambda: self.set_quick_period(0))
        btn_yesterday.clicked.connect(lambda: self.set_quick_period(1))
        btn_3days.clicked.connect(lambda: self.set_quick_period(3))
        btn_week.clicked.connect(lambda: self.set_quick_period(7))

        quick_btn_layout.addWidget(QLabel("Быстрый выбор:"))
        quick_btn_layout.addWidget(btn_today)
        quick_btn_layout.addWidget(btn_yesterday)
        quick_btn_layout.addWidget(btn_3days)
        quick_btn_layout.addWidget(btn_week)
        quick_btn_layout.addStretch()

        # Добавляем элементы в форму
        form_layout.addRow("Продукт:", self.combo_products)
        form_layout.addRow("Период ОТ:", self.datetime_from)
        form_layout.addRow("Период ДО:", self.datetime_to)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(quick_btn_layout)

        # Кнопки управления записью (Добавить / Сохранить / Отменить)
        record_btn_layout = QHBoxLayout()
        self.btn_add_update = QPushButton("Добавить в выборку")
        self.btn_add_update.setStyleSheet("font-weight: bold; padding: 5px;")
        self.btn_add_update.clicked.connect(self.add_or_update_product)

        self.btn_cancel_edit = QPushButton("Отменить редактирование")
        self.btn_cancel_edit.setVisible(False)
        self.btn_cancel_edit.clicked.connect(self.reset_form)

        record_btn_layout.addWidget(self.btn_add_update)
        record_btn_layout.addWidget(self.btn_cancel_edit)
        record_btn_layout.addStretch()
        main_layout.addLayout(record_btn_layout)

        # Выставляем время по умолчанию
        self.set_quick_period(0)

        main_layout.addWidget(QLabel(""))  # Отступ

        # === Таблица выборки ===
        self.lbl_table = QLabel("Текущая выборка (кликните на строку для редактирования):")
        main_layout.addWidget(self.lbl_table)

        self.table_sample = QTableWidget()
        self.table_sample.setColumnCount(4)
        self.table_sample.setHorizontalHeaderLabels(["Продукт", "Начало (ОТ)", "Конец (ДО)", "Действия"])
        self.table_sample.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_sample.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_sample.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_sample.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        # Настройки таблицы для удобного выбора
        self.table_sample.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_sample.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_sample.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_sample.itemSelectionChanged.connect(self.load_row_for_editing)

        main_layout.addWidget(self.table_sample)

        # === Нижние Кнопки управления ===
        bottom_btn_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Очистить всё")
        self.btn_cancel = QPushButton("Отмена")
        self.btn_ok = QPushButton("Сохранить и Выйти")
        self.btn_ok.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 6px 15px;")

        self.btn_clear.clicked.connect(self.clear_sample)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok.clicked.connect(self.accept)

        bottom_btn_layout.addWidget(self.btn_clear)
        bottom_btn_layout.addStretch()
        bottom_btn_layout.addWidget(self.btn_cancel)
        bottom_btn_layout.addWidget(self.btn_ok)
        main_layout.addLayout(bottom_btn_layout)

    def set_quick_period(self, days_back):
        """Устанавливает даты в зависимости от пресета"""
        now = QDateTime.currentDateTime()

        if days_back == 0:
            # За сегодня (с 00:00 до текущего времени)
            start_of_day = QDateTime(now.date(), QTime(0, 0))
            self.datetime_from.setDateTime(start_of_day)
            self.datetime_to.setDateTime(now)
        elif days_back == 1:
            # Вчера (с 00:00 до 23:59 вчерашнего дня)
            yesterday = now.addDays(-1)
            start_of_yesterday = QDateTime(yesterday.date(), QTime(0, 0))
            end_of_yesterday = QDateTime(yesterday.date(), QTime(23, 59))
            self.datetime_from.setDateTime(start_of_yesterday)
            self.datetime_to.setDateTime(end_of_yesterday)
        else:
            # За N дней (от текущего времени минус N дней до текущего времени)
            past = now.addDays(-days_back)
            self.datetime_from.setDateTime(past)
            self.datetime_to.setDateTime(now)

    def load_products(self):
        """Загружает список продуктов из базы данных, исключая -1"""
        try:
            self.combo_products.clear()

            # Динамическая загрузка из базы
            products = self.db.fetch_all("SELECT pr_nmb, pr_name FROM cfg02 WHERE pr_nmb > 0 ORDER BY pr_nmb")

            if not products:
                self.combo_products.addItem("Нет доступных продуктов", 1)
                return

            for p in products:
                pr_nmb = p['pr_nmb']
                pr_name = p['pr_name'] if p['pr_name'] else f"Продукт {pr_nmb}"
                self.combo_products.addItem(f"№{pr_nmb} - {pr_name}", pr_nmb)

        except Exception as e:
            print(f"Ошибка загрузки продуктов: {e}")
            self.combo_products.clear()
            # Фолбэк на случай ошибки БД
            for i in range(1, 6):
                self.combo_products.addItem(f"№{i} - Ошибка БД {i}", i)

    def add_or_update_product(self):
        """Добавляет новую строку или обновляет существующую"""
        if len(self.sample_data) >= 100 and self.editing_row is None:
            QMessageBox.warning(self, "Ошибка", "Максимальное количество строк: 100")
            return

        dt_from = self.datetime_from.dateTime()
        dt_to = self.datetime_to.dateTime()

        if dt_to <= dt_from:
            QMessageBox.warning(self, "Ошибка", "Дата 'ДО' должна быть позже даты 'ОТ'.")
            return

        product_id = self.combo_products.currentData()
        product_text = self.combo_products.currentText()

        # Форматируем данные для сохранения в старом формате JSON
        new_record = {
            'product_id': product_id,
            'product_text': product_text,
            'date_from': dt_from.toString("dd.MM.yyyy"),
            'time_from': dt_from.toString("HH:mm"),
            'date_to': dt_to.toString("dd.MM.yyyy"),
            'time_to': dt_to.toString("HH:mm")
        }

        if self.editing_row is not None:
            # Обновляем существующую
            self.sample_data[self.editing_row] = new_record
            self.reset_form()
        else:
            # Добавляем новую
            self.sample_data.append(new_record)

        self.update_table_from_data()

    def load_row_for_editing(self):
        """Загружает выбранную в таблице строку в форму для редактирования"""
        selected_items = self.table_sample.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        self.editing_row = row
        data = self.sample_data[row]

        # Меняем UI под редактирование
        self.lbl_mode.setText(f"Редактирование строки #{row + 1}:")
        self.lbl_mode.setStyleSheet("font-weight: bold; font-size: 14px; color: #d97706;")  # Оранжевый акцент
        self.btn_add_update.setText("Сохранить изменения")
        self.btn_cancel_edit.setVisible(True)

        # Подставляем продукт
        idx = self.combo_products.findData(data['product_id'])
        if idx >= 0:
            self.combo_products.setCurrentIndex(idx)

        # Подставляем даты
        dt_from_str = f"{data['date_from']} {data['time_from']}"
        dt_to_str = f"{data['date_to']} {data['time_to']}"

        self.datetime_from.setDateTime(QDateTime.fromString(dt_from_str, "dd.MM.yyyy HH:mm"))
        self.datetime_to.setDateTime(QDateTime.fromString(dt_to_str, "dd.MM.yyyy HH:mm"))

    def reset_form(self):
        """Сбрасывает форму в режим добавления"""
        self.editing_row = None
        self.lbl_mode.setText("Добавление новой выборки:")
        self.lbl_mode.setStyleSheet("font-weight: bold; font-size: 14px; color: #333;")
        self.btn_add_update.setText("Добавить в выборку")
        self.btn_cancel_edit.setVisible(False)
        self.table_sample.clearSelection()

    def delete_row(self, row):
        """Удаляет строку из таблицы"""
        if 0 <= row < len(self.sample_data):
            del self.sample_data[row]

            # Если мы удалили строку, которую сейчас редактировали - сбрасываем форму
            if self.editing_row == row:
                self.reset_form()
            elif self.editing_row is not None and self.editing_row > row:
                # Смещаем индекс редактируемой строки, если удалили что-то выше неё
                self.editing_row -= 1

            self.update_table_from_data()

    def clear_sample(self):
        """Очищает всю выборку"""
        self.sample_data.clear()
        self.reset_form()
        self.update_table_from_data()

    def load_sample_from_file(self):
        """Загружает выборку из файла"""
        try:
            sample_path = get_config_path() / "sample" / "s_regress.json"
            if sample_path.exists():
                with open(sample_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.sample_data = data
                        self.update_table_from_data()
        except Exception as e:
            print(f"Ошибка загрузки выборки из файла: {e}")

    def save_sample_to_file(self):
        """Сохраняет выборку в файл"""
        try:
            sample_dir = get_config_path() / "sample"
            sample_dir.mkdir(parents=True, exist_ok=True)
            sample_path = sample_dir / "s_regress.json"
            with open(sample_path, "w", encoding="utf-8") as f:
                json.dump(self.sample_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения выборки в файл: {e}")

    def accept(self):
        self.save_sample_to_file()
        super().accept()

    def update_table_from_data(self):
        """Обновляет таблицу на основе данных выборки"""
        # Отключаем сигналы, чтобы при очистке не сработал itemSelectionChanged
        self.table_sample.blockSignals(True)
        self.table_sample.setRowCount(0)

        for row, item in enumerate(self.sample_data):
            self.table_sample.insertRow(row)

            prod_text = item.get('product_text', f"Продукт {item['product_id']}")
            dt_from = f"{item['date_from']} {item['time_from']}"
            dt_to = f"{item['date_to']} {item['time_to']}"

            self.table_sample.setItem(row, 0, QTableWidgetItem(prod_text))
            self.table_sample.setItem(row, 1, QTableWidgetItem(dt_from))
            self.table_sample.setItem(row, 2, QTableWidgetItem(dt_to))

            # Кнопка удаления
            btn_delete = QPushButton("Удалить")
            btn_delete.setStyleSheet("color: white; background-color: #ef4444; border-radius: 3px; padding: 2px;")
            btn_delete.clicked.connect(self.make_delete_handler(row))

            # Обертка для центрирования кнопки в ячейке
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.addWidget(btn_delete)
            layout.setContentsMargins(2, 2, 2, 2)
            self.table_sample.setCellWidget(row, 3, widget)

        self.table_sample.blockSignals(False)

        # Если мы находимся в режиме редактирования, выделяем нужную строку
        if self.editing_row is not None and self.editing_row < self.table_sample.rowCount():
            self.table_sample.selectRow(self.editing_row)

    def make_delete_handler(self, row):
        """Фабрика обработчиков удаления строк"""
        return lambda: self.delete_row(row)
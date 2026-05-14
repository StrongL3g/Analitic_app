from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLineEdit, QLabel,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from database.db import Database
from config import refresh_app_settings


class CfgprPage(QWidget):
    """Страница справочника продуктов (Таблица cfg02)"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Поле поиска
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск (№ или название):"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Введите номер или название")
        self.filter_edit.setFixedWidth(250)
        self.filter_edit.textChanged.connect(self.apply_filter)
        search_layout.addWidget(self.filter_edit)
        search_layout.addStretch()
        layout.addLayout(search_layout)

        # 2. Ряд кнопок (Сохранить, Добавить, Удалить)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_data)

        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_row)

        self.del_btn = QPushButton("Удалить")
        self.del_btn.clicked.connect(self.delete_row)

        for btn in (self.save_btn, self.add_btn, self.del_btn):
            btn.setFixedWidth(120)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 3. Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["№ (pr_nmb)", "Название", "Описание"])

        # Настройка растягивания колонок
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def load_data(self):
        """Загрузка данных из таблицы cfg02"""
        self.table.setRowCount(0)
        try:
            query = "SELECT pr_nmb, pr_name, pr_desc FROM cfg02 ORDER BY pr_nmb"
            rows = self.db.fetch_all(query)
            if not rows:
                return

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                # Номер продукта (Не редактируемый)
                it_nmb = QTableWidgetItem(str(row['pr_nmb']))
                it_nmb.setFlags(it_nmb.flags() & ~Qt.ItemIsEditable)
                it_nmb.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, it_nmb)

                # Название и описание (Редактируемые)
                self.table.setItem(i, 1, QTableWidgetItem(str(row['pr_name'] if row['pr_name'] else "")))
                self.table.setItem(i, 2, QTableWidgetItem(str(row['pr_desc'] if row['pr_desc'] else "")))

        except Exception as e:
            print(f"Ошибка загрузки cfg02: {e}")

    def apply_filter(self, text):
        """Фильтрация строк по номеру или названию"""
        text = text.lower()
        for i in range(self.table.rowCount()):
            item_id = self.table.item(i, 0)
            item_name = self.table.item(i, 1)

            match_id = text in item_id.text().lower() if item_id else False
            match_name = text in item_name.text().lower() if item_name else False

            self.table.setRowHidden(i, not (match_id or match_name))

    def save_data(self):
        """Массовое обновление измененных данных"""
        try:
            for i in range(self.table.rowCount()):
                pr_nmb = int(self.table.item(i, 0).text())
                pr_name = self.table.item(i, 1).text().strip()
                pr_desc = self.table.item(i, 2).text().strip()

                query = "UPDATE cfg02 SET pr_name = ?, pr_desc = ? WHERE pr_nmb = ?"
                self.db.execute(query, (pr_name, pr_desc, pr_nmb))

            QMessageBox.information(self, "Успех", "Данные продуктов успешно сохранены!")
            refresh_app_settings()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def add_row(self):
        """Добавление нового продукта с автоинкрементом ID"""
        try:
            # Находим следующий свободный номер
            query = "SELECT MAX(pr_nmb) as max_id FROM cfg02"
            res = self.db.fetch_one(query)
            new_id = (res['max_id'] or 0) + 1

            # Вставляем пустую заготовку
            self.db.execute("INSERT INTO cfg02 (pr_nmb, pr_name, pr_desc) VALUES (?, ?, ?)",
                            (new_id, f"Продукт {new_id}", ""))
            self.load_data()
            refresh_app_settings()

            # Прокручиваем к новой строке
            self.table.scrollToBottom()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить продукт: {e}")

    def delete_row(self):
        """Удаление выбранного продукта"""
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите продукт в таблице для удаления!")
            return

        pr_nmb = self.table.item(row, 0).text()
        pr_name = self.table.item(row, 1).text()

        reply = QMessageBox.question(self, 'Подтверждение',
                                     f"Удалить продукт №{pr_nmb} ({pr_name})?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                self.db.execute("DELETE FROM cfg02 WHERE pr_nmb = ?", (pr_nmb,))
                self.load_data()
                refresh_app_settings()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить: {e}")
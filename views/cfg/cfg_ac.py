from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLineEdit, QLabel,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from database.db import Database
from config import refresh_app_settings


class CfgacPage(QWidget):
    """Страница справочника приборов (Таблица cfg00)"""

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

        # 2. Ряд кнопок
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
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["№ (ac_nmb)", "Название", "Описание", "№ измерения"])

        # Настройка ширины колонок
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def load_data(self):
        self.table.setRowCount(0)
        try:
            query = "SELECT ac_nmb, ac_name, ac_desc, meas_nmb FROM cfg00 ORDER BY ac_nmb"
            rows = self.db.fetch_all(query)
            if not rows: return

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                # ID (Только для чтения)
                it_nmb = QTableWidgetItem(str(row['ac_nmb']))
                it_nmb.setFlags(it_nmb.flags() & ~Qt.ItemIsEditable)
                it_nmb.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, it_nmb)

                # Название
                self.table.setItem(i, 1, QTableWidgetItem(str(row['ac_name'] if row['ac_name'] else "")))
                # Описание
                self.table.setItem(i, 2, QTableWidgetItem(str(row['ac_desc'] if row['ac_desc'] else "")))
                # Номер измерения
                self.table.setItem(i, 3, QTableWidgetItem(str(row['meas_nmb'] if row['meas_nmb'] else "1")))

        except Exception as e:
            print(f"Ошибка загрузки cfg00: {e}")

    def apply_filter(self, text):
        text = text.lower()
        for i in range(self.table.rowCount()):
            item_id = self.table.item(i, 0)
            item_name = self.table.item(i, 1)

            match_id = text in item_id.text().lower() if item_id else False
            match_name = text in item_name.text().lower() if item_name else False

            self.table.setRowHidden(i, not (match_id or match_name))

    def save_data(self):
        try:
            for i in range(self.table.rowCount()):
                ac_nmb = int(self.table.item(i, 0).text())
                ac_name = self.table.item(i, 1).text().strip()
                ac_desc = self.table.item(i, 2).text().strip()

                # Обработка пустого ввода для номера измерения
                meas_text = self.table.item(i, 3).text().strip()
                meas_nmb = int(meas_text) if meas_text.isdigit() else 1

                query = "UPDATE cfg00 SET ac_name = ?, ac_desc = ?, meas_nmb = ? WHERE ac_nmb = ?"
                self.db.execute(query, (ac_name, ac_desc, meas_nmb, ac_nmb))

            QMessageBox.information(self, "Успех", "Данные приборов успешно сохранены!")
            refresh_app_settings()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def add_row(self):
        try:
            # Ищем максимальный номер
            query = "SELECT MAX(ac_nmb) as max_id FROM cfg00"
            res = self.db.fetch_one(query)
            new_id = (res['max_id'] or 0) + 1

            self.db.execute("INSERT INTO cfg00 (ac_nmb, ac_name, ac_desc, meas_nmb) VALUES (?, ?, ?, ?)",
                            (new_id, f"Прибор {new_id}", "", 1))
            self.load_data()
            refresh_app_settings()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить строку: {e}")

    def delete_row(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите строку для удаления!")
            return

        ac_nmb = self.table.item(row, 0).text()
        reply = QMessageBox.question(self, 'Подтверждение', f"Удалить прибор №{ac_nmb}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                self.db.execute("DELETE FROM cfg00 WHERE ac_nmb = ?", (ac_nmb,))
                self.load_data()
                refresh_app_settings()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить: {e}")
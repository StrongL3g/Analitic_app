from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLineEdit, QLabel,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from database.db import Database


class CfgspPage(QWidget):
    """Страница справочника пробоотборников (Таблица cfg04)"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск (№ или название):"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setFixedWidth(250)
        self.filter_edit.textChanged.connect(self.apply_filter)
        search_layout.addWidget(self.filter_edit)
        search_layout.addStretch()
        layout.addLayout(search_layout)

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

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["№ (sp_nmb)", "Название", "Описание"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def load_data(self):
        self.table.setRowCount(0)
        try:
            query = "SELECT sp_nmb, sp_name, sp_desc FROM cfg04 ORDER BY sp_nmb"
            rows = self.db.fetch_all(query)
            if not rows: return

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                it_nmb = QTableWidgetItem(str(row['sp_nmb']))
                it_nmb.setFlags(it_nmb.flags() & ~Qt.ItemIsEditable)
                it_nmb.setTextAlignment(Qt.AlignCenter)

                self.table.setItem(i, 0, it_nmb)
                self.table.setItem(i, 1, QTableWidgetItem(str(row['sp_name'] if row['sp_name'] else "")))
                self.table.setItem(i, 2, QTableWidgetItem(str(row['sp_desc'] if row['sp_desc'] else "")))
        except Exception as e:
            print(f"Ошибка загрузки cfg04: {e}")

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
                sp_nmb = int(self.table.item(i, 0).text())
                sp_name = self.table.item(i, 1).text().strip()
                sp_desc = self.table.item(i, 2).text().strip()

                query = "UPDATE cfg04 SET sp_name = ?, sp_desc = ? WHERE sp_nmb = ?"
                self.db.execute(query, (sp_name, sp_desc, sp_nmb))
            QMessageBox.information(self, "Успех", "Пробоотборники сохранены!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def add_row(self):
        try:
            query = "SELECT MAX(sp_nmb) as max_id FROM cfg04"
            res = self.db.fetch_one(query)
            new_id = (res['max_id'] or 0) + 1

            self.db.execute("INSERT INTO cfg04 (sp_nmb, sp_name, sp_desc) VALUES (?, ?, ?)",
                            (new_id, f"Сэмплер {new_id}", ""))
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить строку: {e}")

    def delete_row(self):
        row = self.table.currentRow()
        if row < 0: return

        sp_nmb = self.table.item(row, 0).text()
        reply = QMessageBox.question(self, 'Подтверждение', f"Удалить пробоотборник №{sp_nmb}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                self.db.execute("DELETE FROM cfg04 WHERE sp_nmb = ?", (sp_nmb,))
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить: {e}")
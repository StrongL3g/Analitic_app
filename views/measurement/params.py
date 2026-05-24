# views/products/params.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.db import Database


class ParamsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Параметры измерения продуктов")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setFixedWidth(120)

        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_data)
        save_btn.setFixedWidth(180)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Таблица: PR_SET ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["№", "Продукт", "Ток (I, мкА)", "Напряжение (U, кВ)", "Время (сек)"])

        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        def format_val(val):
            if val is None: return ""
            return str(int(val)) if val == int(val) else str(val)

        try:
            query = """
            SELECT p.id, p.pr_nmb, p.[current], p.[voltage], p.[time], c.pr_name
            FROM pr_set p
            LEFT JOIN cfg02 c ON p.pr_nmb = c.pr_nmb
            ORDER BY p.pr_nmb
            """
            data = self.db.fetch_all(query)
            self.table.setRowCount(len(data))

            for i, row in enumerate(data):
                # Номер продукта
                item_nmb = QTableWidgetItem(str(row["pr_nmb"]))
                item_nmb.setFlags(item_nmb.flags() & ~Qt.ItemIsEditable)
                item_nmb.setData(Qt.UserRole, {"id": row["id"], "pr_nmb": row["pr_nmb"]})
                item_nmb.setBackground(QColor(240, 240, 240))
                item_nmb.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, item_nmb)

                # Название продукта
                item_name = QTableWidgetItem(str(row.get("pr_name") or ""))
                item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
                item_name.setBackground(QColor(240, 240, 240))
                self.table.setItem(i, 1, item_name)

                # Ток
                item_c = QTableWidgetItem(format_val(row["current"]))
                item_c.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 2, item_c)

                # Напряжение
                item_v = QTableWidgetItem(format_val(row["voltage"]))
                item_v.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 3, item_v)

                # Время
                item_t = QTableWidgetItem(format_val(row["time"]))
                item_t.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 4, item_t)

        except Exception as e:
            print(f"Ошибка загрузки pr_set: {e}")

    def save_data(self):
        updated = 0
        try:
            for i in range(self.table.rowCount()):
                item_nmb = self.table.item(i, 0)
                if not item_nmb: continue
                meta = item_nmb.data(Qt.UserRole)
                if not meta: continue

                pr_id = meta["id"]

                current = self.table.item(i, 2).text().strip()
                voltage = self.table.item(i, 3).text().strip()
                time_val = self.table.item(i, 4).text().strip()

                params = [
                    float(current.replace(',', '.')) if current else None,
                    float(voltage.replace(',', '.')) if voltage else None,
                    float(time_val.replace(',', '.')) if time_val else None,
                    pr_id
                ]
                self.db.execute("UPDATE pr_set SET [current]=?, [voltage]=?, [time]=? WHERE id=?", params)
                updated += 1

            if updated > 0:
                QMessageBox.information(self, "Успех", "Параметры продуктов успешно сохранены!")
                self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения параметров: {e}")
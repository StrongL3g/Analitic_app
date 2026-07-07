# views/products/params.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QMessageBox, QHeaderView, QGroupBox, QSplitter
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

        title = QLabel("Параметры измерения продуктов и реперов")
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

        # Создаем разделитель (чтобы можно было менять размер таблиц мышкой)
        splitter = QSplitter(Qt.Vertical)

        # --- Таблица: PR_SET (Продукты) ---
        group_pr = QGroupBox("Параметры продуктов (pr_set)")
        layout_pr = QVBoxLayout()
        self.table_pr = QTableWidget()
        self.table_pr.setColumnCount(5)
        self.table_pr.setHorizontalHeaderLabels(["№", "Продукт", "Ток (I, мкА)", "Напряжение (U, кВ)", "Время (сек)"])
        self.table_pr.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_pr.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_pr.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_pr.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_pr.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table_pr.verticalHeader().setVisible(False)
        self.table_pr.verticalHeader().setDefaultSectionSize(30)
        layout_pr.addWidget(self.table_pr)
        group_pr.setLayout(layout_pr)

        # --- Таблица: RF_SET (Реперы) ---
        group_rf = QGroupBox("Параметры реперов (rf_set)")
        layout_rf = QVBoxLayout()
        self.table_rf = QTableWidget()
        self.table_rf.setColumnCount(4)
        self.table_rf.setHorizontalHeaderLabels(
            ["Анализатор (AC)", "Ток (I, мкА)", "Напряжение (U, кВ)", "Время (сек)"])
        self.table_rf.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_rf.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_rf.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_rf.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_rf.verticalHeader().setVisible(False)
        self.table_rf.verticalHeader().setDefaultSectionSize(30)
        layout_rf.addWidget(self.table_rf)
        group_rf.setLayout(layout_rf)

        # Добавляем группы в сплиттер
        splitter.addWidget(group_pr)
        splitter.addWidget(group_rf)

        # Настраиваем пропорции (например, 70% на продукты, 30% на реперы)
        splitter.setSizes([700, 300])

        layout.addWidget(splitter)
        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        def format_val(val):
            if val is None: return ""
            return str(int(val)) if val == int(val) else str(val)

        # Загрузка таблицы Продуктов
        try:
            query_pr = """
            SELECT p.id, p.pr_nmb, p.[current], p.[voltage], p.[time], c.pr_name
            FROM pr_set p
            LEFT JOIN cfg02 c ON p.pr_nmb = c.pr_nmb
            ORDER BY p.pr_nmb
            """
            data_pr = self.db.fetch_all(query_pr)
            self.table_pr.setRowCount(len(data_pr))

            for i, row in enumerate(data_pr):
                # Номер продукта
                item_nmb = QTableWidgetItem(str(row["pr_nmb"]))
                item_nmb.setFlags(item_nmb.flags() & ~Qt.ItemIsEditable)
                item_nmb.setData(Qt.UserRole, {"id": row["id"], "pr_nmb": row["pr_nmb"]})
                item_nmb.setBackground(QColor(240, 240, 240))
                item_nmb.setTextAlignment(Qt.AlignCenter)
                self.table_pr.setItem(i, 0, item_nmb)

                # Название продукта
                item_name = QTableWidgetItem(str(row.get("pr_name") or ""))
                item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
                item_name.setBackground(QColor(240, 240, 240))
                self.table_pr.setItem(i, 1, item_name)

                # Ток
                item_c = QTableWidgetItem(format_val(row["current"]))
                item_c.setTextAlignment(Qt.AlignCenter)
                self.table_pr.setItem(i, 2, item_c)

                # Напряжение
                item_v = QTableWidgetItem(format_val(row["voltage"]))
                item_v.setTextAlignment(Qt.AlignCenter)
                self.table_pr.setItem(i, 3, item_v)

                # Время
                item_t = QTableWidgetItem(format_val(row["time"]))
                item_t.setTextAlignment(Qt.AlignCenter)
                self.table_pr.setItem(i, 4, item_t)

        except Exception as e:
            print(f"Ошибка загрузки pr_set: {e}")

        # Загрузка таблицы Реперов
        try:
            query_rf = """
            SELECT id, ac_nmb, [current], [voltage], [time]
            FROM rf_set
            ORDER BY ac_nmb
            """
            data_rf = self.db.fetch_all(query_rf)
            self.table_rf.setRowCount(len(data_rf))

            for i, row in enumerate(data_rf):
                # Анализатор
                item_ac = QTableWidgetItem(f"Анализатор {row['ac_nmb']}")
                item_ac.setFlags(item_ac.flags() & ~Qt.ItemIsEditable)
                item_ac.setData(Qt.UserRole, {"id": row["id"]})
                item_ac.setBackground(QColor(240, 240, 240))
                item_ac.setTextAlignment(Qt.AlignCenter)
                self.table_rf.setItem(i, 0, item_ac)

                # Ток
                item_c = QTableWidgetItem(format_val(row["current"]))
                item_c.setTextAlignment(Qt.AlignCenter)
                self.table_rf.setItem(i, 1, item_c)

                # Напряжение
                item_v = QTableWidgetItem(format_val(row["voltage"]))
                item_v.setTextAlignment(Qt.AlignCenter)
                self.table_rf.setItem(i, 2, item_v)

                # Время
                item_t = QTableWidgetItem(format_val(row["time"]))
                item_t.setTextAlignment(Qt.AlignCenter)
                self.table_rf.setItem(i, 3, item_t)

        except Exception as e:
            print(f"Ошибка загрузки rf_set: {e}")

    def save_data(self):
        updated = 0
        try:
            # 1. Сохранение таблицы Продуктов
            for i in range(self.table_pr.rowCount()):
                item_nmb = self.table_pr.item(i, 0)
                if not item_nmb: continue
                meta = item_nmb.data(Qt.UserRole)
                if not meta: continue

                pr_id = meta["id"]
                current = self.table_pr.item(i, 2).text().strip()
                voltage = self.table_pr.item(i, 3).text().strip()
                time_val = self.table_pr.item(i, 4).text().strip()

                params = [
                    float(current.replace(',', '.')) if current else None,
                    float(voltage.replace(',', '.')) if voltage else None,
                    float(time_val.replace(',', '.')) if time_val else None,
                    pr_id
                ]
                self.db.execute("UPDATE pr_set SET [current]=?, [voltage]=?, [time]=? WHERE id=?", params)
                updated += 1

            # 2. Сохранение таблицы Реперов
            for i in range(self.table_rf.rowCount()):
                item_ac = self.table_rf.item(i, 0)
                if not item_ac: continue
                meta = item_ac.data(Qt.UserRole)
                if not meta: continue

                rf_id = meta["id"]
                current = self.table_rf.item(i, 1).text().strip()
                voltage = self.table_rf.item(i, 2).text().strip()
                time_val = self.table_rf.item(i, 3).text().strip()

                params = [
                    float(current.replace(',', '.')) if current else None,
                    float(voltage.replace(',', '.')) if voltage else None,
                    float(time_val.replace(',', '.')) if time_val else None,
                    rf_id
                ]
                self.db.execute("UPDATE rf_set SET [current]=?, [voltage]=?, [time]=? WHERE id=?", params)
                updated += 1

            if updated > 0:
                QMessageBox.information(self, "Успех", "Параметры успешно сохранены!")
                self.load_data()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения параметров: {e}")
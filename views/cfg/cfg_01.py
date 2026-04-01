from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QComboBox, QLabel,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from database.db import Database


class Cfg01Page(QWidget):
    """Страница конфигурации схемы измерений (Таблица CFG01)"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_devices()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Первая строка: Выбор прибора
        ac_row = QHBoxLayout()
        ac_row.addWidget(QLabel("Прибор:"))
        self.ac_combo = QComboBox()
        self.ac_combo.setFixedWidth(200)
        self.ac_combo.currentIndexChanged.connect(self.load_measurements)
        ac_row.addWidget(self.ac_combo)
        ac_row.addStretch()
        layout.addLayout(ac_row)

        # Вторая строка: Кнопки под комбобоксом
        btn_row = QHBoxLayout()
        self.apply_btn = QPushButton("Сохранить")
        self.apply_btn.setFixedWidth(120)
        self.apply_btn.clicked.connect(self.save_data)
        btn_row.addWidget(self.apply_btn)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setFixedWidth(150)
        self.refresh_btn.clicked.connect(self.load_measurements)
        btn_row.addWidget(self.refresh_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "№ Изм.",
            "Кювета",
            "Продукт",
            "Отборник"
        ])

        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    def load_devices(self):
        """Загрузка списка приборов"""
        try:
            res = self.db.fetch_one("SELECT ac_nmb FROM SET00")
            count = res['ac_nmb'] if res else 1

            self.ac_combo.clear()
            for i in range(1, count + 1):
                # Формат как на скриншоте: Прибор №1
                self.ac_combo.addItem(f"Прибор №{i}", i)
        except Exception as e:
            print(f"Ошибка загрузки списка AC: {e}")

    def load_measurements(self):
        """Загрузка данных из CFG01"""
        ac_nmb = self.ac_combo.currentData()
        if not ac_nmb: return

        query = """
            SELECT meas_nmb, cuv_nmb, pr_nmb, sp_nmb 
            FROM CFG01 
            WHERE ac_nmb = ? 
            ORDER BY meas_nmb
        """
        data = self.db.fetch_all(query, (ac_nmb,))
        products = self.db.fetch_all("SELECT pr_nmb, pr_name FROM CFG02 ORDER BY pr_nmb")

        self.table.setRowCount(len(data))

        for i, row in enumerate(data):
            # № Изм. (1, 2, 3...)
            display_nmb = row['meas_nmb'] % 100
            it_meas = QTableWidgetItem(str(display_nmb))
            it_meas.setData(Qt.UserRole, row['meas_nmb'])
            it_meas.setFlags(it_meas.flags() ^ Qt.ItemIsEditable)
            it_meas.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 0, it_meas)

            # Кювета
            it_cuv = QTableWidgetItem(str(row['cuv_nmb']))
            it_cuv.setFlags(it_cuv.flags() ^ Qt.ItemIsEditable)
            it_cuv.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 1, it_cuv)

            # Продукт (ComboBox с "---")
            combo_pr = QComboBox()
            combo_pr.addItem("---", 0)
            for p in products:
                combo_pr.addItem(f"{p['pr_nmb']}: {p['pr_name']}", p['pr_nmb'])

            current_pr = row['pr_nmb'] if row['pr_nmb'] is not None else 0
            idx = combo_pr.findData(current_pr)
            if idx >= 0: combo_pr.setCurrentIndex(idx)

            combo_pr.currentIndexChanged.connect(lambda _, r=i: self.update_sp_value(r))
            self.table.setCellWidget(i, 2, combo_pr)

            # Отборник
            sp_val = row['sp_nmb']
            display_sp = str(sp_val) if (sp_val and current_pr != 0) else "-"

            it_sp = QTableWidgetItem(display_sp)
            it_sp.setFlags(it_sp.flags() ^ Qt.ItemIsEditable)
            it_sp.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 3, it_sp)

    def update_sp_value(self, row_idx):
        pr_nmb = self.table.cellWidget(row_idx, 2).currentData()
        if pr_nmb == 0:
            self.table.item(row_idx, 3).setText("-")
        else:
            res = self.db.fetch_one("SELECT sp_nmb FROM CFG03 WHERE pr_nmb = ?", (pr_nmb,))
            sp_val = str(res['sp_nmb']) if res else "0"
            self.table.item(row_idx, 3).setText(sp_val)

    def save_data(self):
        ac_nmb = self.ac_combo.currentData()
        try:
            for i in range(self.table.rowCount()):
                real_meas_nmb = self.table.item(i, 0).data(Qt.UserRole)
                pr_nmb = self.table.cellWidget(i, 2).currentData()
                sp_text = self.table.item(i, 3).text()
                sp_nmb = int(sp_text) if sp_text.isdigit() else 0

                query = "UPDATE CFG01 SET pr_nmb = ?, sp_nmb = ? WHERE ac_nmb = ? AND meas_nmb = ?"
                self.db.execute(query, (pr_nmb, sp_nmb, ac_nmb, real_meas_nmb))

            QMessageBox.information(self, "Успех", "Данные сохранены")
            self.load_measurements()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")
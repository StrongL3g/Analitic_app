from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QPushButton, QComboBox, QMessageBox, QLineEdit)
from PySide6.QtCore import Qt
from database.db import Database


class ModelsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_devices()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Панель выбора прибора
        ctrl_layout = QHBoxLayout()
        self.ac_combo = QComboBox()
        self.ac_combo.currentIndexChanged.connect(self.load_data)
        ctrl_layout.addWidget(QLabel("Прибор:"))
        ctrl_layout.addWidget(self.ac_combo)
        ctrl_layout.addStretch()

        self.save_btn = QPushButton("Сохранить изменения")
        self.save_btn.clicked.connect(self.save_data)
        ctrl_layout.addWidget(self.save_btn)
        layout.addLayout(ctrl_layout)

        # Основная таблица
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Продукт", "Модель К1", "Описание К1", " ", "Продукт", "Модель К2", "Описание К2"
        ])

        # 1. Настройка колонок:
        # Продукты (0 и 4) и Модели (1 и 5) — под контент
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

        # Разделитель (3) — фиксированный
        self.table.setColumnWidth(3, 20)

        # 2. Описание К1 (2) и Описание К2 (6) — увеличиваем и растягиваем
        # Устанавливаем базовую ширину 250px (увеличенная в 2.5 раза от стандартных 100)
        self.table.setColumnWidth(2, 250)
        self.table.setColumnWidth(6, 250)

        # Разрешаем этим колонкам растягиваться, если окно расширят
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.Stretch)

        layout.addWidget(self.table)

    def load_devices(self):
        ac_list = self.db.fetch_all("SELECT ac_nmb FROM cfg00 ORDER BY ac_nmb")
        for row in ac_list:
            self.ac_combo.addItem(f"Прибор {row['ac_nmb']}", row['ac_nmb'])

    def load_data(self):
        ac_nmb = self.ac_combo.currentData()
        if not ac_nmb: return

        # Получаем данные: 6 пар (К1 и К2)
        items = self.db.fetch_all("""
            SELECT c.pr_nmb, c.cuv_nmb, m.mdl_nmb, m.mdl_desc, m.id 
            FROM cfg01 c
            JOIN mdl_set m ON c.pr_nmb = m.pr_nmb AND m.active_model = 1
            WHERE c.ac_nmb = ?
            ORDER BY c.cuv_nmb, c.pr_nmb
        """, [ac_nmb])

        if len(items) < 12:
            return

        self.table.setRowCount(6)
        for i in range(6):
            k1_row = items[i]
            k2_row = items[i + 6]

            # К1 (левая часть)
            self.table.setItem(i, 0, QTableWidgetItem(f"Прод. {k1_row['pr_nmb']}"))
            self._fill_row_data(i, 1, k1_row)

            # К2 (правая часть)
            self.table.setItem(i, 4, QTableWidgetItem(f"Прод. {k2_row['pr_nmb']}"))
            self._fill_row_data(i, 5, k2_row)

    def _fill_row_data(self, row_idx, col_start, data):
        combo = QComboBox()
        combo.addItems(["1", "2", "3"])
        combo.setCurrentText(str(data['mdl_nmb']))
        combo.setProperty("row_id", data['id'])
        combo.currentTextChanged.connect(lambda text, r=row_idx, c=col_start: self.on_model_changed(text, r, c))
        self.table.setCellWidget(row_idx, col_start, combo)

        desc = QLineEdit(data['mdl_desc'] or "")
        self.table.setCellWidget(row_idx, col_start + 1, desc)

    def on_model_changed(self, text, row, col_idx):
        col_product = 0 if col_idx == 1 else 4
        pr_item = self.table.item(row, col_product)
        if not pr_item: return

        pr_nmb = int(pr_item.text().replace("Прод. ", ""))
        new_desc = self.db.fetch_one("SELECT mdl_desc FROM mdl_set WHERE pr_nmb = ? AND mdl_nmb = ?",
                                     [pr_nmb, int(text)])

        if new_desc:
            desc_edit = self.table.cellWidget(row, col_idx + 1)
            if desc_edit: desc_edit.setText(new_desc['mdl_desc'] or "")

    def save_data(self):
        try:
            for i in range(self.table.rowCount()):
                for col_idx in [1, 5]:
                    combo = self.table.cellWidget(i, col_idx)
                    desc_edit = self.table.cellWidget(i, col_idx + 1)
                    if combo:
                        pr_nmb = int(self.table.item(i, 0 if col_idx == 1 else 4).text().replace("Прод. ", ""))
                        new_mdl = int(combo.currentText())
                        new_desc = desc_edit.text()

                        self.db.execute("UPDATE mdl_set SET active_model = 0 WHERE pr_nmb = ?", [pr_nmb])
                        self.db.execute(
                            "UPDATE mdl_set SET active_model = 1, mdl_desc = ? WHERE pr_nmb = ? AND mdl_nmb = ?",
                            [new_desc, pr_nmb, new_mdl])
            QMessageBox.information(self, "Успех", "Данные сохранены!")
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")
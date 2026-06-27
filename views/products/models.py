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
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

        # Разделитель (3) — фиксированный
        self.table.setColumnWidth(3, 20)

        # 2. Описание К1 (2) и Описание К2 (6) — увеличиваем и растягиваем
        self.table.setColumnWidth(2, 250)
        self.table.setColumnWidth(6, 250)
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

        # ИСПОЛЬЗУЕМ LEFT JOIN, чтобы строки с pr_nmb = -1 не терялись
        # Сортируем по meas_nmb, чтобы порядок 1-6 (К1) и 7-12 (К2) был железным
        items = self.db.fetch_all("""
            SELECT c.meas_nmb, c.pr_nmb, c.cuv_nmb, m.mdl_nmb, m.mdl_desc, m.id 
            FROM cfg01 c
            LEFT JOIN mdl_set m ON c.pr_nmb = m.pr_nmb AND m.active_model = 1
            WHERE c.ac_nmb = ?
            ORDER BY c.cuv_nmb, c.meas_nmb
        """, [ac_nmb])

        # Если в cfg01 нет 12 строк, значит конфигуратор не заполнен, прерываем
        if len(items) < 12:
            self.table.setRowCount(0)
            return

        self.table.setRowCount(6)
        for i in range(6):
            k1_row = items[i]  # Первые 6 строк - Кювета 1
            k2_row = items[i + 6]  # Вторые 6 строк - Кювета 2

            # К1 (левая часть)
            if k1_row['pr_nmb'] == -1:
                self.table.setItem(i, 0, QTableWidgetItem("Нет продукта"))
                self._fill_empty_row(i, 1)
            else:
                self.table.setItem(i, 0, QTableWidgetItem(f"Прод. {k1_row['pr_nmb']}"))
                self._fill_row_data(i, 1, k1_row)

            # К2 (правая часть)
            if k2_row['pr_nmb'] == -1:
                self.table.setItem(i, 4, QTableWidgetItem("Нет продукта"))
                self._fill_empty_row(i, 5)
            else:
                self.table.setItem(i, 4, QTableWidgetItem(f"Прод. {k2_row['pr_nmb']}"))
                self._fill_row_data(i, 5, k2_row)

    def _fill_empty_row(self, row_idx, col_start):
        """Создает заблокированные виджеты для пустых слотов (-1)"""
        combo = QComboBox()
        combo.addItem("---", -1)
        combo.setEnabled(False)  # Блокируем
        self.table.setCellWidget(row_idx, col_start, combo)

        desc = QLineEdit("")
        desc.setEnabled(False)  # Блокируем
        self.table.setCellWidget(row_idx, col_start + 1, desc)

    def _fill_row_data(self, row_idx, col_start, data):
        combo = QComboBox()
        combo.addItems(["1", "2", "3"])

        current_mdl = str(data['mdl_nmb']) if data['mdl_nmb'] else "1"
        combo.setCurrentText(current_mdl)

        combo.setProperty("row_id", data['id'])
        combo.currentTextChanged.connect(lambda text, r=row_idx, c=col_start: self.on_model_changed(text, r, c))
        self.table.setCellWidget(row_idx, col_start, combo)

        desc = QLineEdit(data['mdl_desc'] or "")
        self.table.setCellWidget(row_idx, col_start + 1, desc)

    def on_model_changed(self, text, row, col_idx):
        if not text or text == "---": return

        col_product = 0 if col_idx == 1 else 4
        pr_item = self.table.item(row, col_product)
        if not pr_item or "Прод." not in pr_item.text(): return

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

                    # Сохраняем только активные (разблокированные) комбобоксы
                    if combo and combo.isEnabled():
                        pr_text = self.table.item(i, 0 if col_idx == 1 else 4).text()
                        if "Прод." in pr_text:
                            pr_nmb = int(pr_text.replace("Прод. ", ""))
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
# views/measurement/criteria.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from database.db import Database
import config


class CriteriaPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.set04_data = None
        self.current_ac_nmb = 1
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Критерии проверок приборов")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Выбор прибора ---
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Прибор:"))

        self.ac_selector = QComboBox()
        for i in range(1, config.AC_COUNT + 1):
            self.ac_selector.addItem(f"Прибор {i}", i)
        self.ac_selector.currentIndexChanged.connect(self.on_ac_changed)
        selector_layout.addWidget(self.ac_selector)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setFixedWidth(120)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_data)
        save_btn.setFixedWidth(120)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Таблица критериев проверок ---
        self.table = QTableWidget()
        self.table.setRowCount(5)  # 1 строка заголовок + 4 строки параметров (без SD)
        self.table.setColumnCount(2)  # Название, Значение
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)

        self.table.setColumnWidth(0, 250)  # Название параметра
        self.table.setColumnWidth(1, 150)  # Значение поля ввода
        for row in range(5):
            self.table.setRowHeight(row, 30)

        layout.addWidget(self.table)
        self.setLayout(layout)

        if self.ac_selector.count() > 0:
            self.ac_selector.setCurrentIndex(0)
            self.current_ac_nmb = self.ac_selector.currentData()

        if self.current_ac_nmb is not None:
            self.load_data()

    def on_ac_changed(self, index):
        if index >= 0:
            self.current_ac_nmb = self.ac_selector.currentData()
            self.load_data()

    def load_data(self):
        def format_val(val):
            if val is None: return ""
            return str(int(val)) if val == int(val) else str(val)

        try:
            # Исключили SD из запроса, оставили только существующие колонки
            query = "SELECT id, i_def, i_b, k_d_def, sr FROM set04 WHERE ac_nmb = ?"
            data_list = self.db.fetch_all(query, [self.current_ac_nmb])

            if not data_list:
                print(f"Нет данных в SET04 для прибора {self.current_ac_nmb}")
                self.table.clearContents()
                self.set04_data = None
                return

            self.set04_data = data_list[0]

            # Приводим к нижнему регистру для надежности
            row_data = {k.lower(): v for k, v in self.set04_data.items()}

            # Заголовки таблицы
            self.table.setItem(0, 0, QTableWidgetItem("Параметр"))
            self.table.setItem(0, 1, QTableWidgetItem("Значение"))
            for col in range(2):
                self.table.item(0, col).setTextAlignment(Qt.AlignCenter)
                self.table.item(0, col).setFlags(self.table.item(0, col).flags() & ~Qt.ItemIsEditable)
                self.table.item(0, col).setBackground(Qt.gray)

            # Список отображаемых параметров
            params = [
                ("σтек, %", "i_def"),
                ("Опорная Iреп, имп/с", "i_b"),
                ("σоп, %", "k_d_def"),
                ("SR (Спектры)", "sr")
            ]

            for i, (param_name, param_key) in enumerate(params):
                table_row = i + 1

                # Название критерия
                item_name = QTableWidgetItem(param_name)
                item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(table_row, 0, item_name)

                # Значение критерия
                val_item = QTableWidgetItem(format_val(row_data.get(param_key)))
                val_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(table_row, 1, val_item)

        except Exception as e:
            print(f"Ошибка при загрузке критериев проверок: {e}")

    def save_data(self):
        if not self.set04_data:
            QMessageBox.warning(self, "Внимание", "Нет данных для сохранения")
            return

        try:
            # Считываем данные из таблицы построчно
            i_def = self.table.item(1, 1).text().strip() if self.table.item(1, 1) else ""
            i_b = self.table.item(2, 1).text().strip() if self.table.item(2, 1) else ""
            k_d_def = self.table.item(3, 1).text().strip() if self.table.item(3, 1) else ""
            sr = self.table.item(4, 1).text().strip() if self.table.item(4, 1) else ""

            record_id = self.set04_data.get("id") or self.set04_data.get("ID")

            params = [
                float(i_def.replace(',', '.')) if i_def else None,
                float(i_b.replace(',', '.')) if i_b else None,
                float(k_d_def.replace(',', '.')) if k_d_def else None,
                float(sr.replace(',', '.')) if sr else None,
                record_id
            ]

            # Исключили SD из UPDATE структуры
            query = """
            UPDATE set04
            SET i_def = ?, i_b = ?, k_d_def = ?, sr = ?
            WHERE id = ?
            """
            self.db.execute(query, params)
            QMessageBox.information(self, "Успех", f"Критерии проверок для прибора успешно сохранены!")
            self.load_data()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении критериев: {e}")
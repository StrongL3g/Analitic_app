# views/products/params.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QComboBox
)
from PySide6.QtCore import Qt
from database.db import Database
from config import get_config


class ParamsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.table = None
        self.record_id = None
        self.ac_selector = None
        self.current_ac_nmb = 1
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Параметры измерения")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Выбор прибора ---
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Прибор:"))

        self.ac_selector = QComboBox()
        # ПОЛУЧАЕМ КОЛИЧЕСТВО ПРИБОРОВ ИЗ КОНФИГА
        ac_count = int(get_config("AC_COUNT", 1))
        for i in range(1, ac_count + 1):
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

        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_data)
        save_btn.setFixedWidth(120)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # --- Таблица с параметрами ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setRowCount(9)

        # УБИРАЕМ ЗАГОЛОВКИ СТРОК
        self.table.verticalHeader().setVisible(False)

        headers = ["№", "I, мкА", "U, кВ", "Время, сек", "Кратность"]
        self.table.setHorizontalHeaderLabels(headers)

        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_data()

    def on_ac_changed(self, index):
        self.current_ac_nmb = self.ac_selector.currentData()
        self.load_data()

    def load_data(self):
        query = """
        SELECT id,
               current_00, current_01, current_02, current_03, current_04,
               current_05, current_06, current_07, current_08,
               voltage_00, voltage_01, voltage_02, voltage_03, voltage_04,
               voltage_05, voltage_06, voltage_07, voltage_08,
               time_00, time_01, time_02, time_03, time_04,
               time_05, time_06, time_07, time_08
        FROM SET04
        WHERE ac_nmb = ?
        """

        try:
            data = self.db.fetch_all(query, [self.current_ac_nmb])
            if not data:
                print(f"Нет данных в SET04 для прибора {self.current_ac_nmb}")
                return

            row_data = data[0]
            self.record_id = row_data.get("id")

            self.table.setRowCount(9)

            for row in range(9):
                # Номер строки
                item = QTableWidgetItem(str(row))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 0, item)

                # Ток (I, мкА)
                current_field = f"current_{row:02d}"
                value = row_data.get(current_field)
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, item)

                # Напряжение (U, кВ)
                voltage_field = f"voltage_{row:02d}"
                value = row_data.get(voltage_field)
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, item)

                # Время (сек)
                time_field = f"time_{row:02d}"
                value = row_data.get(time_field)
                item = QTableWidgetItem(str(value) if value is not None else "")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, item)

                # Кратность
                if row == 0:
                    item = QTableWidgetItem("1")
                else:
                    item = QTableWidgetItem("4")
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row, 4, item)

            self.table.resizeColumnsToContents()

        except Exception as e:
            print(f"Ошибка при загрузке параметров измерения: {e}")

    def save_data(self):
        if not self.record_id:
            print("Нет ID записи для обновления")
            return

        try:
            fields = []
            params = []

            for row in range(9):
                # Ток
                current_field = f"current_{row:02d}"
                item = self.table.item(row, 1)
                if item:
                    value = item.text().strip()
                    fields.append(current_field)
                    params.append(value if value else None)

                # Напряжение
                voltage_field = f"voltage_{row:02d}"
                item = self.table.item(row, 2)
                if item:
                    value = item.text().strip()
                    fields.append(voltage_field)
                    params.append(value if value else None)

                # Время
                time_field = f"time_{row:02d}"
                item = self.table.item(row, 3)
                if item:
                    value = item.text().strip()
                    fields.append(time_field)
                    params.append(value if value else None)

            if not fields:
                print("Нет данных для обновления")
                return

            set_parts = []
            query_params = []

            for field, value in zip(fields, params):
                if value is None:
                    set_parts.append(f"{field} = NULL")
                else:
                    set_parts.append(f"{field} = ?")
                    query_params.append(value)

            query = f"""
            UPDATE SET04
            SET {', '.join(set_parts)}
            WHERE id = ? AND ac_nmb = ?
            """
            query_params.extend([self.record_id, self.current_ac_nmb])

            self.db.execute(query, query_params)
            print(f"Данные успешно сохранены для прибора {self.current_ac_nmb}")

        except Exception as e:
            print(f"Ошибка при сохранении параметров измерения: {e}")

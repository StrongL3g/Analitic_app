# views/measurement/criteria.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QComboBox
)
from PySide6.QtCore import Qt
from database.db import Database
from utils.helpers import get_ln_name
from config import AC_COUNT


class CriteriaPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.table = None
        self.set04_data = None
        self.ac_selector = None
        self.current_ac_nmb = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Критерии проверок")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Выбор прибора ---
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Прибор:"))

        self.ac_selector = QComboBox()
        for i in range(1, AC_COUNT + 1):
            self.ac_selector.addItem(f"Прибор {i}", i)
        self.ac_selector.currentIndexChanged.connect(self.on_ac_changed)
        selector_layout.addWidget(self.ac_selector)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # --- Кнопки (слева) ---
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

        # --- Таблица (оставляем только правую) ---
        self.table = QTableWidget()
        self.table.setRowCount(5)   # 1 заголовок + 4 параметра
        self.table.setColumnCount(2) # Название, Значение
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)

        # Настройка размеров таблицы
        self.table.setColumnWidth(0, 150)  # Название параметра
        self.table.setColumnWidth(1, 100)  # Значение
        for row in range(5):
            self.table.setRowHeight(row, 25)

        layout.addWidget(self.table)
        self.setLayout(layout)
        #self.load_data()

         # После создания комбобокса устанавливаем текущее значение
        if self.ac_selector.count() > 0:
            self.ac_selector.setCurrentIndex(0)
            self.current_ac_nmb = self.ac_selector.currentData()

        layout.addWidget(self.table)
        self.setLayout(layout)

        # Загружаем данные только если есть что загружать
        if self.current_ac_nmb is not None:
            self.load_data()

    def on_ac_changed(self, index):
        """Обработчик изменения выбора прибора"""
        if index >= 0:  # проверяем валидный индекс
            self.current_ac_nmb = self.ac_selector.currentData()
            self.load_data()
        else:
            self.current_ac_nmb = None
            self.clear_table()  # очищаем таблицу если ничего не выбрано

    def load_data(self):
        """Загружает данные из SET04"""
        try:
            # === Загружаем данные из SET04 ===
            query_set04 = f"""
            SELECT i_def, i_b, k_d_def, sd
            FROM SET04
            WHERE ac_nmb = ?
            """

            set04_data_list = self.db.fetch_all(query_set04, [self.current_ac_nmb])

            if not set04_data_list:
                print(f"Нет данных в SET04 для прибора {self.current_ac_nmb}")
                return

            self.set04_data = set04_data_list[0]  # Сохраняем для обновления

            # Детальный вывод каждого поля
            for key in ['i_def', 'i_b', 'k_d_def', 'sd']:
                value = self.set04_data.get(key, 'NOT FOUND')

            # === Заполняем таблицу ===
            # Заголовки
            headers = ["Параметр", "Значение"]
            for col, header in enumerate(headers):
                item = QTableWidgetItem(header)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(Qt.gray)
                self.table.setItem(0, col, item)

            # Параметры
            params = [
                ("σтек, %", "i_def"),
                ("Опорная Iреп, имп/с", "i_b"),
                ("σоп, %", "k_d_def"),
                ("СКО", "sd")
            ]

            for i, (param_name, param_key) in enumerate(params):
                table_row = i + 1

                # Название параметра
                item_name = QTableWidgetItem(param_name)
                item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(table_row, 0, item_name)

                # Значение параметра
                param_value = self.set04_data.get(param_key, "")
                item_value = QTableWidgetItem(str(param_value))
                item_value.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(table_row, 1, item_value)

        except Exception as e:
            print(f"Ошибка при загрузке данных для 'Критерии проверок': {e}")
            import traceback
            traceback.print_exc()

    def save_data(self):
        """Сохраняет изменения в SET04"""
        try:
            if not self.set04_data:
                print("Нет данных для сохранения")
                return

            # Собираем изменения из таблицы
            updates = {}
            params_mapping = {
                1: "i_def",
                2: "i_b",
                3: "k_d_def",
                4: "sd"
            }

            for row, param_key in params_mapping.items():
                item_value = self.table.item(row, 1)
                if item_value:
                    updates[param_key] = item_value.text()

            # Формируем SQL запрос на обновление
            if updates:
                set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
                values = list(updates.values())

                query = f"""
                UPDATE SET04
                SET {set_clause}
                WHERE ac_nmb = ?
                """
                print(query)
                values.append(self.current_ac_nmb)

                self.db.execute(query, values)
                print(f"Сохранено {len(updates)} изменений для прибора {self.current_ac_nmb}")

                # Обновляем локальные данные
                for key, value in updates.items():
                    self.set04_data[key] = value

        except Exception as e:
            print(f"Ошибка при сохранении данных: {e}")
            import traceback
            traceback.print_exc()

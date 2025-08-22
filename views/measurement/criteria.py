# views/measurement/criteria.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QComboBox
)
from PySide6.QtCore import Qt
from database.db import Database
from utils.helpers import get_ln_name
from config import get_config


class CriteriaPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.table = None
        self.set04_data = None
        self.ac_selector = None
        self.current_ac_nmb = 1
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
        ac_count = int(get_config("AC_COUNT", 1))
        for i in range(1, ac_count + 1):
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
        self.load_data()

    def on_ac_changed(self, index):
        """Обработчик изменения выбора прибора"""
        self.current_ac_nmb = self.ac_selector.currentData()
        self.load_data()

    def load_data(self):
        """Загружает данные из SET04"""
        try:
            # === Загружаем данные из SET04 ===
            query_set04 = f"""
            SELECT
                [I_DEF], [I_B], [K_D_DEF], [SD]
            FROM [{self.db.database_name}].[dbo].[SET04]
            WHERE [ac_nmb] = ?
            """
            set04_data_list = self.db.fetch_all(query_set04, [self.current_ac_nmb])

            if not set04_data_list:
                print(f"Нет данных в SET04 для прибора {self.current_ac_nmb}")
                return

            self.set04_data = set04_data_list[0]  # Сохраняем для обновления

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
                ("σтек, %", "SD"),
                ("Опорная Iреп, имп/с", "I_DEF"),
                ("σоп, %", "K_D_DEF"),
                ("СКО", "I_B")
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
                1: "SD",
                2: "I_DEF",
                3: "K_D_DEF",
                4: "I_B"
            }

            for row, param_key in params_mapping.items():
                item_value = self.table.item(row, 1)
                if item_value:
                    updates[param_key] = item_value.text()

            # Формируем SQL запрос на обновление
            if updates:
                set_clause = ", ".join([f"[{key}] = ?" for key in updates.keys()])
                values = list(updates.values())

                query = f"""
                UPDATE [{self.db.database_name}].[dbo].[SET04]
                SET {set_clause}
                WHERE [ac_nmb] = ?
                """
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

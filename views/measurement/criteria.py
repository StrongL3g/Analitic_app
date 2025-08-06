# views/measurement/criteria.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QGridLayout, QHeaderView
)
from PySide6.QtCore import Qt
from database.db import Database
from utils.helpers import get_ln_name  # Импортируем функцию


class CriteriaPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.table1 = None
        self.table2 = None
        self.set04_data = None  # Сохраняем данные SET04 для обновления
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Критерии проверок")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Создаем сетку для размещения двух таблиц
        grid_layout = QGridLayout()

        # Первая таблица 3x21 (заголовок + 20 строк данных)
        self.table1 = QTableWidget()
        self.table1.setRowCount(21)  # 1 заголовок + 20 данных
        self.table1.setColumnCount(3)  # LN_Name, Imin, Imax
        self.table1.horizontalHeader().setVisible(False)
        self.table1.verticalHeader().setVisible(False)

        # Настройка размеров первой таблицы
        self.table1.setColumnWidth(0, 120)  # LN_Name
        self.table1.setColumnWidth(1, 100)  # Imin
        self.table1.setColumnWidth(2, 100)  # Imax
        for row in range(21):
            self.table1.setRowHeight(row, 25)

        # Вторая таблица 2x5 (заголовок + 4 параметра)
        self.table2 = QTableWidget()
        self.table2.setRowCount(5)   # 1 заголовок + 4 параметра
        self.table2.setColumnCount(2) # Название, Значение
        self.table2.horizontalHeader().setVisible(False)
        self.table2.verticalHeader().setVisible(False)

        # Настройка размеров второй таблицы
        self.table2.setColumnWidth(0, 150)  # Название параметра
        self.table2.setColumnWidth(1, 100)  # Значение
        for row in range(5):
            self.table2.setRowHeight(row, 25)

        # Добавляем таблицы в сетку
        grid_layout.addWidget(self.table1, 0, 0)
        grid_layout.addWidget(self.table2, 0, 1)

        layout.addLayout(grid_layout)

        # Кнопки - выравниваем по левому краю
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_data)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()  # Добавляем растягивающийся элемент справа
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Загружаем данные при инициализации
        self.load_data()

    def load_data(self):
        """Загружает данные из SET04 и SET02 и заполняет таблицы"""
        try:
            # === Загружаем данные из SET04 ===
            query_set04 = """
            SELECT
                [I_DEF], [I_B], [K_D_DEF], [SD],
                [I_MIN_01], [I_MIN_02], [I_MIN_03], [I_MIN_04], [I_MIN_05],
                [I_MIN_06], [I_MIN_07], [I_MIN_08], [I_MIN_09], [I_MIN_10],
                [I_MIN_11], [I_MIN_12], [I_MIN_13], [I_MIN_14], [I_MIN_15],
                [I_MIN_16], [I_MIN_17], [I_MIN_18], [I_MIN_19], [I_MIN_20],
                [I_MAX_01], [I_MAX_02], [I_MAX_03], [I_MAX_04], [I_MAX_05],
                [I_MAX_06], [I_MAX_07], [I_MAX_08], [I_MAX_09], [I_MAX_10],
                [I_MAX_11], [I_MAX_12], [I_MAX_13], [I_MAX_14], [I_MAX_15],
                [I_MAX_16], [I_MAX_17], [I_MAX_18], [I_MAX_19], [I_MAX_20]
            FROM [AMMKASAKDB01].[dbo].[SET04]
            WHERE [ak_nmb] = 1
            """
            set04_data_list = self.db.fetch_all(query_set04)

            if not set04_data_list:
                print("Нет данных в SET04")
                return

            self.set04_data = set04_data_list[0]  # Сохраняем для обновления

            # === Загружаем номера линий из SET02 ===
            query_set02 = """
            SELECT [ln_nmb]
            FROM [AMMKASAKDB01].[dbo].[SET02]
            WHERE [ID] > 1
            ORDER BY [ID]
            """
            set02_data = self.db.fetch_all(query_set02)

            # Создаем список ln_nmb в порядке ID
            ordered_ln_nmbs = [row['ln_nmb'] for row in set02_data]

            # === Заполняем первую таблицу ===
            # Заголовки
            headers1 = ["LN_Name", "Imin", "Imax"]
            for col, header in enumerate(headers1):
                item = QTableWidgetItem(header)
                item.setTextAlignment(Qt.AlignCenter)
                # Сделаем заголовки немного темнее
                if col == 0:
                    item.setBackground(Qt.lightGray)
                else:
                    item.setBackground(Qt.gray)
                self.table1.setItem(0, col, item)

            # Данные
            for i in range(20):  # Всегда 20 строк
                table_row = i + 1

                # Получаем ln_nmb для этой строки из упорядоченного списка
                if i < len(ordered_ln_nmbs):
                    ln_nmb = ordered_ln_nmbs[i]
                    # Получаем имя линии через нашу функцию
                    ln_name = get_ln_name(ln_nmb)
                else:
                    ln_nmb = "-1"
                    ln_name = "-1"

                # LN_Name
                item_name = QTableWidgetItem(ln_name)
                item_name.setTextAlignment(Qt.AlignCenter)
                self.table1.setItem(table_row, 0, item_name)

                # Imin и Imax - берем по порядку из SET04
                # I_MIN_01/I_MAX_01 для первой строки, I_MIN_02/I_MAX_02 для второй и т.д.
                min_key = f"I_MIN_{i+1:02d}"
                max_key = f"I_MAX_{i+1:02d}"

                min_value = self.set04_data.get(min_key, "")
                max_value = self.set04_data.get(max_key, "")

                # Imin
                item_min = QTableWidgetItem(str(min_value))
                item_min.setTextAlignment(Qt.AlignCenter)
                self.table1.setItem(table_row, 1, item_min)

                # Imax
                item_max = QTableWidgetItem(str(max_value))
                item_max.setTextAlignment(Qt.AlignCenter)
                self.table1.setItem(table_row, 2, item_max)

            # === Заполняем вторую таблицу ===
            # Заголовки
            headers2 = ["Параметр", "Значение"]
            for col, header in enumerate(headers2):
                item = QTableWidgetItem(header)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(Qt.gray)
                self.table2.setItem(0, col, item)

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
                self.table2.setItem(table_row, 0, item_name)

                # Значение параметра
                param_value = self.set04_data.get(param_key, "")
                item_value = QTableWidgetItem(str(param_value))
                item_value.setTextAlignment(Qt.AlignCenter)
                self.table2.setItem(table_row, 1, item_value)

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

            # Собираем изменения из первой таблицы
            updates = {}

            # Для первой таблицы (I_MIN_XX, I_MAX_XX)
            for i in range(20):  # 20 строк данных
                table_row = i + 1

                # Получаем значения из таблицы
                item_min = self.table1.item(table_row, 1)
                item_max = self.table1.item(table_row, 2)

                if item_min:
                    min_key = f"I_MIN_{i+1:02d}"
                    updates[min_key] = item_min.text()

                if item_max:
                    max_key = f"I_MAX_{i+1:02d}"
                    updates[max_key] = item_max.text()

            # Собираем изменения из второй таблицы
            params_mapping = {
                1: "SD",
                2: "I_DEF",
                3: "K_D_DEF",
                4: "I_B"
            }

            for row, param_key in params_mapping.items():
                item_value = self.table2.item(row, 1)
                if item_value:
                    updates[param_key] = item_value.text()

            # Формируем SQL запрос на обновление
            if updates:
                set_clause = ", ".join([f"[{key}] = ?" for key in updates.keys()])
                values = list(updates.values())

                query = f"""
                UPDATE [AMMKASAKDB01].[dbo].[SET04]
                SET {set_clause}
                WHERE [ak_nmb] = 1
                """

                self.db.execute(query, values)
                print(f"Сохранено {len(updates)} изменений")

                # Обновляем локальные данные
                for key, value in updates.items():
                    self.set04_data[key] = value

        except Exception as e:
            print(f"Ошибка при сохранении данных: {e}")
            import traceback
            traceback.print_exc()

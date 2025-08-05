# views/products/params.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout
)
from PySide6.QtCore import Qt
from database.db import Database


class ParamsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.table = None
        self.record_id = None  # Сохраняем ID записи для обновления
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Параметры измерения (SET04)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Таблица с параметрами
        self.table = QTableWidget()
        self.table.setColumnCount(5)  # 5 колонок: №, I, U, время, кратность
        self.table.setRowCount(9)  # 9 строк данных (0-8)

        # Заголовки столбцов
        headers = ["№", "I, мкА", "U, кВ", "Время, сек", "Кратность"]
        self.table.setHorizontalHeaderLabels(headers)

        # Настройка ширины столбцов
        for col in range(5):
            self.table.resizeColumnToContents(col)

        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_data)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        """Загружает параметры измерения из SET04"""
        query = """
        SELECT [id],
               [current_00], [current_01], [current_02], [current_03], [current_04],
               [current_05], [current_06], [current_07], [current_08],
               [voltage_00], [voltage_01], [voltage_02], [voltage_03], [voltage_04],
               [voltage_05], [voltage_06], [voltage_07], [voltage_08],
               [time_00], [time_01], [time_02], [time_03], [time_04],
               [time_05], [time_06], [time_07], [time_08]
        FROM [AMMKASAKDB01].[dbo].[SET04]
        WHERE [ak_nmb] = 1
        """

        try:
            data = self.db.fetch_all(query)
            if not data:
                print("Нет данных в SET04")
                return

            # Берем первую запись (предполагаем, что она одна)
            row_data = data[0]
            self.record_id = row_data.get("id")  # Сохраняем ID для последующего обновления

            # Устанавливаем количество строк
            self.table.setRowCount(9)

            # Заполняем таблицу
            for row in range(9):
                # Номер строки (только для отображения, не редактируется)
                item = QTableWidgetItem(str(row))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                self.table.setItem(row, 0, item)

                # Ток (I, мкА)
                current_field = f"current_{row:02d}"
                value = row_data.get(current_field)
                if value is not None:
                    item = QTableWidgetItem(str(value))
                else:
                    item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 1, item)

                # Напряжение (U, кВ)
                voltage_field = f"voltage_{row:02d}"
                value = row_data.get(voltage_field)
                if value is not None:
                    item = QTableWidgetItem(str(value))
                else:
                    item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 2, item)

                # Время (сек)
                time_field = f"time_{row:02d}"
                value = row_data.get(time_field)
                if value is not None:
                    item = QTableWidgetItem(str(value))
                else:
                    item = QTableWidgetItem("")
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, 3, item)

                # Кратность (только для отображения, не редактируется)
                if row == 0:
                    item = QTableWidgetItem("1")
                else:
                    item = QTableWidgetItem("4")
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                self.table.setItem(row, 4, item)

            # Автоматическое выравнивание ширины столбцов
            self.table.resizeColumnsToContents()

        except Exception as e:
            print(f"Ошибка при загрузке параметров измерения: {e}")

    def save_data(self):
        """Сохраняет изменения в БД"""
        if not self.record_id:
            print("Нет ID записи для обновления")
            return

        try:
            # Подготавливаем список изменяемых полей
            fields = []
            params = []

            # Проходим по всем 9 строкам и собираем значения из редактируемых столбцов
            for row in range(9):
                # Ток (I, мкА) - столбец 1
                current_field = f"current_{row:02d}"
                item = self.table.item(row, 1)
                if item:
                    value = item.text().strip()
                    fields.append(current_field)
                    if value == "":
                        params.append(None)  # Будет преобразовано в NULL
                    else:
                        params.append(value)

                # Напряжение (U, кВ) - столбец 2
                voltage_field = f"voltage_{row:02d}"
                item = self.table.item(row, 2)
                if item:
                    value = item.text().strip()
                    fields.append(voltage_field)
                    if value == "":
                        params.append(None)  # Будет преобразовано в NULL
                    else:
                        params.append(value)

                # Время (сек) - столбец 3
                time_field = f"time_{row:02d}"
                item = self.table.item(row, 3)
                if item:
                    value = item.text().strip()
                    fields.append(time_field)
                    if value == "":
                        params.append(None)  # Будет преобразовано в NULL
                    else:
                        params.append(value)

            if not fields:
                print("Нет данных для обновления")
                return

            # Формируем SET часть запроса
            set_parts = []
            query_params = []

            for field, value in zip(fields, params):
                if value is None:
                    set_parts.append(f"[{field}] = NULL")
                else:
                    set_parts.append(f"[{field}] = ?")
                    query_params.append(value)

            # Формируем и выполняем запрос
            query = f"""
            UPDATE [AMMKASAKDB01].[dbo].[SET04]
            SET {', '.join(set_parts)}
            WHERE [id] = ? AND [ak_nmb] = 1
            """
            query_params.append(self.record_id)

            self.db.execute(query, query_params)
            print("Данные успешно сохранены")

        except Exception as e:
            print(f"Ошибка при сохранении параметров измерения: {e}")

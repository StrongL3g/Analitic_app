# views/measurement/elements.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout
)
from PySide6.QtCore import Qt
from database.db import Database


class ElementsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}  # Сохраняем оригинальные данные для сравнения
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Элементы (SET05, ak_nmb = 1)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["ID", "Номер", "Название"])
        self.table.setEditTriggers(QTableWidget.DoubleClicked)  # Редактирование по двойному клику
        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)

        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_data)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Загружаем данные при открытии
        self.load_data()

    def load_data(self):
        """Загружает элементы из SET05 где ak_nmb = 1"""
        query = """
        SELECT [id], [el_nmb], [el_name]
        FROM [AMMKASAKDB01].[dbo].[SET05]
        WHERE [ak_nmb] = 1
        ORDER BY [el_nmb]
        """
        try:
            data = self.db.fetch_all(query)
            self.table.setRowCount(0)
            self.original_data.clear()

            for row_data in data:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)

                # ID
                item_id = QTableWidgetItem(str(row_data["id"]))
                item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                self.table.setItem(row_pos, 0, item_id)

                # Номер
                item_nmb = QTableWidgetItem(str(row_data["el_nmb"]))
                item_nmb.setFlags(item_nmb.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_pos, 1, item_nmb)

                # Название
                self.table.setItem(row_pos, 2, QTableWidgetItem(row_data["el_name"]))

                # Сохраняем оригинальное значение
                self.original_data[row_data["id"]] = row_data["el_name"]

        except Exception as e:
            print(f"Ошибка при загрузке данных: {e}")

    def save_data(self):
        """Сохраняет изменения в БД"""
        updated_count = 0
        for row in range(self.table.rowCount()):
            item_id = self.table.item(row, 0)
            item_name = self.table.item(row, 2)

            if not item_id or not item_name:
                continue

            row_id = int(item_id.text())
            new_name = item_name.text().strip()
            old_name = self.original_data.get(row_id, "")

            if new_name and new_name != old_name:
                try:
                    query = """
                    UPDATE [AMMKASAKDB01].[dbo].[SET05]
                    SET [el_name] = ?
                    WHERE [id] = ?
                    """
                    self.db.execute(query, [new_name, row_id])
                    self.original_data[row_id] = new_name  # Обновляем оригинал
                    updated_count += 1
                except Exception as e:
                    print(f"Ошибка при обновлении строки ID={row_id}: {e}")

        if updated_count > 0:
            print(f"Сохранено: {updated_count} строк")
        else:
            print("Изменений не было")

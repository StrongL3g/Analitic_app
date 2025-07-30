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
        layout.addWidget(self.table)

        # Кнопка "Обновить"
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        btn_layout.addWidget(refresh_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Автоматически загружаем данные при открытии
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
            self.table.setRowCount(0)  # Очищаем таблицу
            for row_data in data:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)
                self.table.setItem(row_pos, 0, QTableWidgetItem(str(row_data["id"])))
                self.table.setItem(row_pos, 1, QTableWidgetItem(str(row_data["el_nmb"])))
                self.table.setItem(row_pos, 2, QTableWidgetItem(row_data["el_name"]))
        except Exception as e:
            print(f"Ошибка при загрузке данных: {e}")

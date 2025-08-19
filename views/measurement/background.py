# views/measurement/background.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.db import Database


class BackgroundPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.table = None
        self.meta_rows = []  # Сохраним для использования в save_data
        self.ordered_ln_nmbs = []  # Сохраним для использования в save_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Фон и наложения")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Таблица: без лейблов, заголовки в самой таблице + данные
        self.table = QTableWidget()
        self.table.setRowCount(21) # имя + данные 20строк
        self.table.setColumnCount(41) # имя + данные 40 строк
        self.table.setHorizontalHeaderLabels([""] * 41)
        self.table.setVerticalHeaderLabels([""] * 21)
        # Отключаем стандартные границы, будем рисовать вручную при необходимости
        self.table.setGridStyle(Qt.NoPen)

        # Настройка ширины столбцов и высоты строк
        for col in range(41):
            # Ширина для столбцов с данными
            self.table.setColumnWidth(col, 60)
        for row in range(21):
            self.table.setRowHeight(row, 30)

        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        refresh_btn = QPushButton("Обновить")
        save_btn = QPushButton("Сохранить")
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)



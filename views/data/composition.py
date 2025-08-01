from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QCheckBox, QListWidget, QListWidgetItem, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from database.db import Database

class CompositionPage(QWidget):
    def __init__(self,  db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}  # Сохраняем оригинальные данные для сравнения
        self.init_ui()

    def on_checkbox_change(self, state):
        # state == 2 (Qt.Checked) — включен, 0 (Qt.Unchecked) — выключен
        if state == 2:
            print("Чекбокс включен")
        else:
            print("Чекбокс выключен")

    def init_ui(self):
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Hello World")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        #Чекбоксы
        #Ручное измерение
        self.check_man = QCheckBox("Ручное измерение")
        self.check_man.stateChanged.connect(self.on_checkbox_change)
        layout.addWidget(self.check_man)
        #Наличие химии
        self.check_chem = QCheckBox("Наличие химии")
        layout.addWidget(self.check_chem)
        #Интенсивности
        self.check_inten = QCheckBox("Интенсивности")
        layout.addWidget(self.check_inten)

        # Создаем листбокс с продуктами
        self.product_combo = QComboBox()
        # Заполняем список продуктов
        products = [f"Продукт {i}" for i in range(1, 9)]  # Продукт 1...Продукт 8
        self.product_combo.addItems(products)
        layout.addWidget(self.product_combo)

        # Настраиваем размер
        self.product_combo.setMinimumContentsLength(10)  # Ширина по содержимому
        self.product_combo.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)

        # Устанавливаем фиксированную ширину (можно регулировать)
        self.product_combo.setMinimumWidth(120)

        # Направление раскрывания - только вниз
        self.product_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.product_combo.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)


        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(["ID", "Номер", "Название"])
        self.table.setEditTriggers(QTableWidget.DoubleClicked)  # Редактирование по двойному клику
        layout.addWidget(self.table)


        self.setLayout(layout)




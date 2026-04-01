from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLineEdit, QLabel,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from database.db import Database


class Cfg02Page(QWidget):
    """Страница справочника продуктов (Таблица CFG02)"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Поле поиска
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск продукта (№):"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Введите номер продукта")
        self.filter_edit.setFixedWidth(200)
        self.filter_edit.textChanged.connect(self.apply_filter)
        search_layout.addWidget(self.filter_edit)
        search_layout.addStretch()
        layout.addLayout(search_layout)

        # 2. Ряд кнопок под поиском
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setFixedWidth(120)
        self.save_btn.clicked.connect(self.save_data)
        btn_layout.addWidget(self.save_btn)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setFixedWidth(120)
        self.refresh_btn.clicked.connect(self.load_data)
        btn_layout.addWidget(self.refresh_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 3. Таблица продуктов
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "Номер продукта",
            "Продукт",
            "Описание"
        ])

        # Убираем нумерацию строк слева
        self.table.verticalHeader().setVisible(False)

        # Настройка ширины колонок
        header = self.table.horizontalHeader()
        # Номер продукта — по контенту (узкий)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # Продукт — фиксированный (примерно под Продукт №XXXX)
        self.table.setColumnWidth(1, 150)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        # Описание — всё остальное
        header.setSectionResizeMode(2, QHeaderView.Stretch)

        layout.addWidget(self.table)

    def load_data(self):
        """Загрузка всех продуктов из базы"""
        try:
            data = self.db.fetch_all("SELECT pr_nmb, pr_name, pr_desc FROM CFG02 ORDER BY pr_nmb")
            self.table.setRowCount(len(data))

            for i, row in enumerate(data):
                # Номер продукта (только чтение)
                it_nmb = QTableWidgetItem(str(row['pr_nmb']))
                it_nmb.setFlags(it_nmb.flags() ^ Qt.ItemIsEditable)
                it_nmb.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, it_nmb)

                # Продукт (Редактируемый)
                self.table.setItem(i, 1, QTableWidgetItem(str(row['pr_name'] if row['pr_name'] else "")))

                # Описание (Редактируемое)
                self.table.setItem(i, 2, QTableWidgetItem(str(row['pr_desc'] if row['pr_desc'] else "")))

        except Exception as e:
            print(f"Ошибка загрузки CFG02: {e}")

    def apply_filter(self, text):
        """Фильтрация строк по вводу в поиск"""
        for i in range(self.table.rowCount()):
            item = self.table.item(i, 0)
            if item:
                should_hide = text not in item.text() if text else False
                self.table.setRowHidden(i, should_hide)

    def save_data(self):
        """Сохранение изменений в БД"""
        try:
            for i in range(self.table.rowCount()):
                pr_nmb = int(self.table.item(i, 0).text())
                pr_name = self.table.item(i, 1).text().strip()
                pr_desc = self.table.item(i, 2).text().strip()

                query = "UPDATE CFG02 SET pr_name = ?, pr_desc = ? WHERE pr_nmb = ?"
                self.db.execute(query, (pr_name, pr_desc, pr_nmb))

            QMessageBox.information(self, "Успех", "Данные сохранены")
            self.load_data()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {e}")
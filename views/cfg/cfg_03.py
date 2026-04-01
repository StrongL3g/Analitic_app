from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QComboBox,
                               QPushButton, QMessageBox, QLabel)
from PySide6.QtCore import Qt
from database.db import Database


class Cfg03Page(QWidget):
    """Страница связей Продукт <-> Пробоотборник (Таблица CFG03)"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Панель управления (Кнопки сверху слева)
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

        # 2. Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels([
            "Номер пробоотборника",
            "Продукт"
        ])

        # Убираем нумерацию строк
        self.table.verticalHeader().setVisible(False)

        # Настройка колонок
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # По тексту заголовка
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # На всю ширину

        layout.addWidget(self.table)

    def load_data(self):
        """Загрузка данных из CFG03 с сортировкой по пробоотборнику"""
        try:
            # Берем данные, сортируем по sp_nmb (отборник слева)
            data = self.db.fetch_all("SELECT sp_nmb, pr_nmb FROM CFG03 ORDER BY sp_nmb")
            # Список всех доступных продуктов для комбобокса
            products = self.db.fetch_all("SELECT pr_nmb, pr_name FROM CFG02 ORDER BY pr_nmb")

            self.table.setRowCount(len(data))

            for i, row in enumerate(data):
                # 1. Номер пробоотборника (Только чтение)
                it_sp = QTableWidgetItem(str(row['sp_nmb']))
                it_sp.setFlags(it_sp.flags() ^ Qt.ItemIsEditable)
                it_sp.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, it_sp)

                # 2. Выбор продукта (ComboBox)
                combo_pr = QComboBox()
                combo_pr.addItem("---", 0)  # Для пустой связи
                for p in products:
                    combo_pr.addItem(f"{p['pr_nmb']}: {p['pr_name']}", p['pr_nmb'])

                # Устанавливаем текущий привязанный продукт
                current_pr = row['pr_nmb'] if row['pr_nmb'] is not None else 0
                idx = combo_pr.findData(current_pr)
                if idx >= 0:
                    combo_pr.setCurrentIndex(idx)

                self.table.setCellWidget(i, 1, combo_pr)

        except Exception as e:
            print(f"Ошибка загрузки CFG03: {e}")

    def save_data(self):
        """Сохранение связей и синхронизация с основной таблицей CFG01"""
        try:
            for i in range(self.table.rowCount()):
                sp_nmb = int(self.table.item(i, 0).text())
                pr_nmb = self.table.cellWidget(i, 1).currentData()

                # 1. Обновляем справочник связей
                self.db.execute(
                    "UPDATE CFG03 SET pr_nmb = ? WHERE sp_nmb = ?",
                    (pr_nmb, sp_nmb)
                )

                # 2. Синхронизируем с CFG01: если продукт привязан к этому отборнику,
                # обновляем sp_nmb во всех измерениях, где выбран этот продукт.
                # Это гарантирует, что на первой странице данные обновятся сами.
                if pr_nmb != 0:
                    self.db.execute(
                        "UPDATE CFG01 SET sp_nmb = ? WHERE pr_nmb = ?",
                        (sp_nmb, pr_nmb)
                    )
                else:
                    # Если связь разорвана (выбрано ---), можно обнулить sp_nmb в CFG01
                    # для этого отборника, если логика проекта это предполагает.
                    pass

            QMessageBox.information(self, "Успех", "Связи продуктов и отборников сохранены")
            self.load_data()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении связей: {e}")
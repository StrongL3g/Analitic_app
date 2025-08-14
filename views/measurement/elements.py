# views/measurement/elements.py
import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QComboBox, QHeaderView,
    QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.db import Database


class ElementsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}
        self.first_load = True  # Флаг для отслеживания первого открытия
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)  # Отступы вокруг
        layout.setSpacing(15)  # Расстояние между элементами

        title = QLabel("Элементы")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Кнопки - теперь в начале, под заголовком
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)  # Расстояние между кнопками

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setFixedWidth(120)

        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_data)
        save_btn.setFixedWidth(180)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()  # Отступ справа
        layout.insertLayout(1, btn_layout)  # Вставляем кнопки после заголовка

        # Создаем контейнер для таблицы с фиксированным размером
        self.table_container = QWidget()
        table_layout = QVBoxLayout(self.table_container)
        table_layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Номер", "Название"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # Запрещаем стандартное редактирование
        self.table.verticalHeader().setVisible(False)

        # Настройка заголовков
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Номер - по содержимому
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Название - растягивается

        # Высота строк
        self.table.verticalHeader().setDefaultSectionSize(30)

        table_layout.addWidget(self.table)
        layout.addWidget(self.table_container)

        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        """Загружает элементы из SET05"""
        query = f"""
        SELECT [id], [el_nmb], [el_name]
        FROM [{self.db.database_name}].[dbo].[SET05]
        ORDER BY [el_nmb]
        """
        try:
            data = self.db.fetch_all(query)
            self.table.setRowCount(0)
            self.original_data.clear()

            for row_data in data:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)

                # Номер (не редактируется)
                item_nmb = QTableWidgetItem(str(row_data["el_nmb"]))
                item_nmb.setTextAlignment(Qt.AlignCenter)
                item_nmb.setFlags(item_nmb.flags() & ~Qt.ItemIsEditable)
                # Цвет фона для номера
                item_nmb.setBackground(QColor(240, 240, 240))
                self.table.setItem(row_pos, 0, item_nmb)

                # Название (редактируется через комбо-бокс)
                combo = QComboBox()
                combo.addItems(["-", "INT", "ТФ", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr", "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th", "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"])

                # Устанавливаем текущее значение
                current_value = row_data["el_name"]
                index = combo.findText(current_value)
                if index >= 0:
                    combo.setCurrentIndex(index)
                else:
                    combo.setCurrentText(current_value)

                self.table.setCellWidget(row_pos, 1, combo)

                # Сохраняем оригинальные данные
                self.original_data[row_data["id"]] = {
                    "el_nmb": row_data["el_nmb"],
                    "el_name": current_value
                }

            # Формируем JSON после загрузки
            self.export_to_json()

            # Показываем сообщение об успешной загрузке только если это не первое открытие
            if not self.first_load:
                QMessageBox.information(self, "Успех", f"Загружено {len(data)} элементов")
            else:
                self.first_load = False  # Сбрасываем флаг после первого открытия

        except Exception as e:
            error_msg = f"Ошибка при загрузке данных: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def save_data(self):
        """Сохраняет изменения в БД"""
        try:
            updated_count = 0
            for row in range(self.table.rowCount()):
                # Получаем номер из таблицы
                item_nmb = self.table.item(row, 0)
                # Получаем значение из комбо-бокса
                combo = self.table.cellWidget(row, 1)

                if not item_nmb or not combo:
                    continue

                el_nmb = int(item_nmb.text())
                new_name = combo.currentText().strip()

                # Ищем оригинальные данные по el_nmb
                original_entry = None
                row_id = None
                for id_key, data in self.original_data.items():
                    if data["el_nmb"] == el_nmb:
                        original_entry = data
                        row_id = id_key
                        break

                if original_entry and new_name and new_name != original_entry["el_name"]:
                    query = f"""
                    UPDATE [{self.db.database_name}].[dbo].[SET05]
                    SET [el_name] = ?
                    WHERE [id] = ?
                    """
                    self.db.execute(query, [new_name, row_id])
                    # Обновляем оригинальные данные
                    self.original_data[row_id]["el_name"] = new_name
                    updated_count += 1

            if updated_count > 0:
                print(f"Сохранено: {updated_count} строк")
                # После сохранения обновляем JSON
                self.export_to_json()
                # Показываем сообщение об успешном сохранении
                QMessageBox.information(self, "Успех", f"Сохранено {updated_count} изменений")
            else:
                print("Изменений не было")
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения")

        except Exception as e:
            error_msg = f"Ошибка при сохранении данных: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def export_to_json(self):
        """Формирует и сохраняет JSON-файл по пути Analitic_app/config/elements.json"""
        try:
            rows = []
            for row in range(self.table.rowCount()):
                item_nmb = self.table.item(row, 0)
                combo = self.table.cellWidget(row, 1)

                if item_nmb and combo:
                    rows.append({
                        "number": int(item_nmb.text()),
                        "name": combo.currentText()
                    })

            # Определяем путь к файлу относительно текущего скрипта
            base_dir = os.path.dirname(os.path.abspath(__file__))  # Путь к папке views/measurement
            config_dir = os.path.join(base_dir, "..", "..", "config")  # Поднимаемся к Analitic_app/config
            os.makedirs(config_dir, exist_ok=True)  # Создаём папку, если её нет
            json_path = os.path.join(config_dir, "elements.json")

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=4)

            print(f"JSON успешно сохранён: {json_path}")

        except Exception as e:
            error_msg = f"Ошибка при экспорте в JSON: {e}"
            print(error_msg)

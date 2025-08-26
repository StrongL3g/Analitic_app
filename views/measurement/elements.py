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
            # Обновляем JSON с математическими взаимодействиями
            self.generate_math_interactions_json()
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
                # Обновляем JSON с математическими взаимодействиями
                self.generate_math_interactions_json()
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

    def generate_math_interactions_json(self):
        """Генерирует JSON-файл с математическими взаимодействиями элементов"""
        try:
            # Получаем активные элементы (исключая "-" и "INT")
            active_elements = []
            for row in range(self.table.rowCount()):
                item_nmb = self.table.item(row, 0)
                combo = self.table.cellWidget(row, 1)

                if item_nmb and combo:
                    element_name = combo.currentText()
                    if element_name != "-" and element_name != "INT":
                        # Нумерация начинается с 0
                        adjusted_number = int(item_nmb.text()) - 1
                        active_elements.append({
                            "original_number": int(item_nmb.text()),
                            "adjusted_number": adjusted_number,
                            "name": element_name
                        })

            # Создаем структуру данных для математических взаимодействий
            math_interactions = []

            # Операции: 0=пустая строка, 1=элемент, 2=умножение, 3=деление, 4=возведение в квадрат,
            # 5=обратное значение, 6=деление на квадрат, 7=обратное значение квадрата
            operations = [
                {"code": 0, "description": "Пустая строка"},
                {"code": 1, "description": "Элемент"},
                {"code": 2, "description": "Умножение"},
                {"code": 3, "description": "Деление"},
                {"code": 4, "description": "Квадрат"},
                {"code": 5, "description": "Обратное значение"},
                {"code": 6, "description": "Деление на квадрат"},
                {"code": 7, "description": "Обратное значение квадрата"}
            ]

            # Для каждого активного элемента создаем набор взаимодействий
            for i, element in enumerate(active_elements):
                element_set = {
                    "element_name": element["name"],
                    "element_original_number": element["original_number"],
                    "element_adjusted_number": element["adjusted_number"],
                    "interactions": []
                }

                # 0. Пустая строка (первая всегда)
                element_set["interactions"].append({
                    "description": "",
                    "x1": 0,
                    "x2": 0,
                    "op": 0
                })

                # 1. Элементы (кроме текущего)
                for other_element in active_elements:
                    if other_element["adjusted_number"] != element["adjusted_number"]:
                        element_set["interactions"].append({
                            "description": other_element["name"],
                            "x1": other_element["adjusted_number"],
                            "x2": 0,
                            "op": 1
                        })

                # 2. Умножение с другими элементами
                for other_element1 in active_elements:
                    for other_element2 in active_elements:
                        if (other_element1["adjusted_number"] != element["adjusted_number"] and
                            other_element2["adjusted_number"] != element["adjusted_number"]):
                            # Исключаем умножение элемента на самого себя
                            if other_element1["adjusted_number"] != other_element2["adjusted_number"]:
                                element_set["interactions"].append({
                                    "description": f"{other_element1['name']} * {other_element2['name']}",
                                    "x1": other_element1["adjusted_number"],
                                    "x2": other_element2["adjusted_number"],
                                    "op": 2
                                })

                # 3. Деление элементов
                for other_element1 in active_elements:
                    for other_element2 in active_elements:
                        if (other_element1["adjusted_number"] != element["adjusted_number"] and
                            other_element2["adjusted_number"] != element["adjusted_number"]):
                            # Исключаем деление элемента на самого себя
                            if other_element1["adjusted_number"] != other_element2["adjusted_number"]:
                                element_set["interactions"].append({
                                    "description": f"{other_element1['name']} / {other_element2['name']}",
                                    "x1": other_element1["adjusted_number"],
                                    "x2": other_element2["adjusted_number"],
                                    "op": 3
                                })

                # 4. Квадраты элементов (кроме текущего)
                for other_element in active_elements:
                    if other_element["adjusted_number"] != element["adjusted_number"]:
                        element_set["interactions"].append({
                            "description": f"{other_element['name']} ^ 2",
                            "x1": other_element["adjusted_number"],
                            "x2": 0,
                            "op": 4
                        })

                # 5. Обратные значения элементов (кроме текущего)
                for other_element in active_elements:
                    if other_element["adjusted_number"] != element["adjusted_number"]:
                        element_set["interactions"].append({
                            "description": f"1 / {other_element['name']}",
                            "x1": other_element["adjusted_number"],
                            "x2": 0,
                            "op": 5
                        })

                # 6. Деление на квадраты элементов
                for other_element1 in active_elements:
                    for other_element2 in active_elements:
                        if (other_element1["adjusted_number"] != element["adjusted_number"] and
                            other_element2["adjusted_number"] != element["adjusted_number"]):
                            # Исключаем деление элемента на свой собственный квадрат
                            if other_element1["adjusted_number"] != other_element2["adjusted_number"]:
                                element_set["interactions"].append({
                                    "description": f"{other_element1['name']} / {other_element2['name']} ^ 2",
                                    "x1": other_element1["adjusted_number"],
                                    "x2": other_element2["adjusted_number"],
                                    "op": 6
                                })

                # 7. Обратные значения квадратов элементов (кроме текущего)
                for other_element in active_elements:
                    if other_element["adjusted_number"] != element["adjusted_number"]:
                        element_set["interactions"].append({
                            "description": f"1 / {other_element['name']} ^ 2",
                            "x1": other_element["adjusted_number"],
                            "x2": 0,
                            "op": 7
                        })

                math_interactions.append(element_set)

            # Сохраняем в файл
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(base_dir, "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            json_path = os.path.join(config_dir, "math_interactions.json")

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "operations": operations,
                    "elements": active_elements,
                    "interactions": math_interactions
                }, f, ensure_ascii=False, indent=4)

            print(f"JSON математических взаимодействий сохранён: {json_path}")
            print(f"Создано {len(math_interactions)} наборов взаимодействий")
            if math_interactions:
                print(f"Всего операций в каждом наборе: {len(math_interactions[0]['interactions'])}")

        except Exception as e:
            error_msg = f"Ошибка при генерации JSON математических взаимодействий: {e}"
            print(error_msg)

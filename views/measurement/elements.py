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
from utils.path_manager import get_config_path


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
        SELECT id, el_nmb, el_name
        FROM SET05
        ORDER BY el_nmb
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
                combo.addItems(
                    ["-", "INT", "ТФ", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe",
                     "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr", "Nb", "Mo",
                     "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn", "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce",
                     "Pr", "Nd", "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb", "Lu", "Hf", "Ta", "W",
                     "Re", "Os", "Ir", "Pt", "Au", "Hg", "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
                     "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm", "Md", "No", "Lr", "Rf", "Db", "Sg",
                     "Bh", "Hs", "Mt", "Ds", "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"])

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

            if not self.first_load:
                QMessageBox.information(self, "Успех", f"Загружено {len(data)} элементов")
            else:
                self.first_load = False

        except Exception as e:
            error_msg = f"Ошибка при загрузке данных: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def sync_set08_database(self) -> tuple[int, int]:
        """Синхронизирует таблицу set08: добавляет недостающие и удаляет лишние."""
        try:
            # 1. Получаем все существующие продукты
            products = self.db.fetch_all("SELECT pr_nmb FROM cfg02")
            if not products:
                return 0, 0
            pr_nmbs = [p['pr_nmb'] for p in products]

            # 2. Получаем все элементы, которые сейчас настроены (не пустышки)
            active_elements = []
            for row in range(self.table.rowCount()):
                item_nmb = self.table.item(row, 0)
                combo = self.table.cellWidget(row, 1)
                if item_nmb and combo:
                    el_name = combo.currentText().strip()
                    if el_name and el_name not in ("-", "INT"):
                        active_elements.append(int(item_nmb.text()))

            # 3. Читаем что есть в set08
            existing = self.db.fetch_all("SELECT id, pr_nmb, el_nmb FROM set08")
            existing_pairs = set()
            to_delete_ids = []

            for row in existing:
                # Если элемент больше не активен ИЛИ продукт был удален
                if row['el_nmb'] not in active_elements or row['pr_nmb'] not in pr_nmbs:
                    to_delete_ids.append(row['id'])
                else:
                    existing_pairs.add((row['pr_nmb'], row['el_nmb']))

            # 4. Удаляем неактуальные строки
            deleted_count = len(to_delete_ids)
            for del_id in to_delete_ids:
                self.db.execute("DELETE FROM set08 WHERE id = ?", [del_id])

            # 5. Добавляем то, чего не хватает
            added_count = 0
            if active_elements:
                for pr in pr_nmbs:
                    for el in active_elements:
                        if (pr, el) not in existing_pairs:
                            self.db.execute(
                                "INSERT INTO set08 (pr_nmb, el_nmb, delta_c_01, delta_c_02) VALUES (?, ?, 0, 0)",
                                [pr, el]
                            )
                            added_count += 1

            if added_count > 0 or deleted_count > 0:
                print(f"Синхронизация set08: добавлено {added_count}, удалено {deleted_count} нормативов.")

            return added_count, deleted_count

        except Exception as e:
            print(f"Ошибка при синхронизации set08: {e}")
            return 0, 0

    def save_data(self):
        """Сохраняет изменения в БД"""
        try:
            updated_count = 0
            for row in range(self.table.rowCount()):
                item_nmb = self.table.item(row, 0)
                combo = self.table.cellWidget(row, 1)

                if not item_nmb or not combo:
                    continue

                el_nmb = int(item_nmb.text())
                new_name = combo.currentText().strip()

                original_entry = None
                row_id = None
                for id_key, data in self.original_data.items():
                    if data["el_nmb"] == el_nmb:
                        original_entry = data
                        row_id = id_key
                        break

                if original_entry and new_name and new_name != original_entry["el_name"]:
                    query = """
                    UPDATE SET05
                    SET el_name = ?
                    WHERE id = ?
                    """
                    self.db.execute(query, [new_name, row_id])
                    self.original_data[row_id]["el_name"] = new_name
                    updated_count += 1

            # === АВТОМАТИЧЕСКАЯ СИНХРОНИЗАЦИЯ ТАБЛИЦЫ НОРМАТИВОВ ===
            added_normatives, deleted_normatives = self.sync_set08_database()

            if updated_count > 0 or added_normatives > 0 or deleted_normatives > 0:
                print(
                    f"Сохранено: {updated_count} строк элементов, добавлено {added_normatives} нормативов, удалено {deleted_normatives}.")
                self.export_to_json()
                self.generate_math_interactions_json()

                msg = []
                if updated_count > 0: msg.append(f"Обновлено {updated_count} элементов.")
                if added_normatives > 0: msg.append(f"Сгенерировано {added_normatives} недостающих нормативов.")
                if deleted_normatives > 0: msg.append(f"Удалено {deleted_normatives} неактуальных нормативов.")
                QMessageBox.information(self, "Успех", "\n".join(msg))
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

            config_dir = get_config_path()
            json_path = config_dir / "elements.json"

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=4)

            print(f"JSON успешно сохранён: {json_path}")

        except Exception as e:
            error_msg = f"Ошибка при экспорте в JSON: {e}"
            print(error_msg)

    def generate_math_interactions_json(self):
        """Генерирует JSON-файл с математическими взаимодействиями элементов"""
        try:
            active_elements = []
            for row in range(self.table.rowCount()):
                item_nmb = self.table.item(row, 0)
                combo = self.table.cellWidget(row, 1)

                if item_nmb and combo:
                    element_name = combo.currentText()
                    if element_name != "-" and element_name != "INT":
                        adjusted_number = int(item_nmb.text()) - 1
                        active_elements.append({
                            "original_number": int(item_nmb.text()),
                            "adjusted_number": adjusted_number,
                            "name": element_name
                        })

            math_interactions = []

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

            for i, element in enumerate(active_elements):
                element_set = {
                    "element_name": element["name"],
                    "element_original_number": element["original_number"],
                    "element_adjusted_number": element["adjusted_number"],
                    "interactions": []
                }

                # 0. Пустая строка
                element_set["interactions"].append({"description": "", "x1": 0, "x2": 0, "op": 0})

                # 1. Элементы
                for other_element in active_elements:
                    if other_element["adjusted_number"] != element["adjusted_number"]:
                        element_set["interactions"].append({
                            "description": other_element["name"],
                            "x1": other_element["adjusted_number"], "x2": 0, "op": 1
                        })

                # 2. Умножение
                for other_element1 in active_elements:
                    for other_element2 in active_elements:
                        if (other_element1["adjusted_number"] != element["adjusted_number"] and
                                other_element2["adjusted_number"] != element["adjusted_number"]):
                            if other_element1["adjusted_number"] != other_element2["adjusted_number"]:
                                element_set["interactions"].append({
                                    "description": f"{other_element1['name']} * {other_element2['name']}",
                                    "x1": other_element1["adjusted_number"], "x2": other_element2["adjusted_number"],
                                    "op": 2
                                })

                # 3. Деление
                for other_element1 in active_elements:
                    for other_element2 in active_elements:
                        if (other_element1["adjusted_number"] != element["adjusted_number"] and
                                other_element2["adjusted_number"] != element["adjusted_number"]):
                            if other_element1["adjusted_number"] != other_element2["adjusted_number"]:
                                element_set["interactions"].append({
                                    "description": f"{other_element1['name']} / {other_element2['name']}",
                                    "x1": other_element1["adjusted_number"], "x2": other_element2["adjusted_number"],
                                    "op": 3
                                })

                # 4. Квадраты
                for other_element in active_elements:
                    if other_element["adjusted_number"] != element["adjusted_number"]:
                        element_set["interactions"].append({
                            "description": f"{other_element['name']} ^ 2",
                            "x1": other_element["adjusted_number"], "x2": 0, "op": 4
                        })

                # 5. Обратные значения
                for other_element in active_elements:
                    if other_element["adjusted_number"] != element["adjusted_number"]:
                        element_set["interactions"].append({
                            "description": f"1 / {other_element['name']}",
                            "x1": other_element["adjusted_number"], "x2": 0, "op": 5
                        })

                # 6. Деление на квадраты
                for other_element1 in active_elements:
                    for other_element2 in active_elements:
                        if (other_element1["adjusted_number"] != element["adjusted_number"] and
                                other_element2["adjusted_number"] != element["adjusted_number"]):
                            if other_element1["adjusted_number"] != other_element2["adjusted_number"]:
                                element_set["interactions"].append({
                                    "description": f"{other_element1['name']} / {other_element2['name']} ^ 2",
                                    "x1": other_element1["adjusted_number"], "x2": other_element2["adjusted_number"],
                                    "op": 6
                                })

                # 7. Обратные значения квадратов
                for other_element in active_elements:
                    if other_element["adjusted_number"] != element["adjusted_number"]:
                        element_set["interactions"].append({
                            "description": f"1 / {other_element['name']} ^ 2",
                            "x1": other_element["adjusted_number"], "x2": 0, "op": 7
                        })

                math_interactions.append(element_set)

            config_dir = get_config_path()
            json_path = config_dir / "math_interactions.json"

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "operations": operations,
                    "elements": active_elements,
                    "interactions": math_interactions
                }, f, ensure_ascii=False, indent=4)

        except Exception as e:
            error_msg = f"Ошибка при генерации JSON математических взаимодействий: {e}"
            print(error_msg)
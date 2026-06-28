# views/measurement/ranges.py
import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QComboBox, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.db import Database
import config
from utils.path_manager import get_config_path


class RangesPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        # Формат: {ac_nmb: {id_строки_в_бд: {sq_nmb, ln_nmb, ln_ch_min, ln_ch_max}}}
        self.device_data = {i: {} for i in range(1, config.AC_COUNT + 1)}
        self.lines_names = {}  # ln_nmb -> name (из JSON)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Спектральные диапазоны")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setFixedWidth(120)

        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_data)
        save_btn.setFixedWidth(180)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Таблица (колонки будут динамическими в зависимости от кол-ва приборов)
        self.table = QTableWidget()
        self.update_column_headers()
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(30)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_data()

    def update_column_headers(self):
        """Устанавливает динамические заголовки столбцов для каждого прибора"""
        headers = ["№", "Название"]
        for ac in range(1, config.AC_COUNT + 1):
            headers.extend([f"Min (Пр.{ac})", f"Max (Пр.{ac})"])

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # Настройка ширины
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 150)
        for i in range(2, len(headers)):
            self.table.setColumnWidth(i, 90)

    def load_lines_names(self):
        try:
            config_dir = get_config_path()
            json_path = config_dir / "lines.json"
            if not os.path.exists(json_path):
                return

            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.lines_names.clear()
            for item in data:
                self.lines_names[item["number"]] = item["name"]
        except Exception as e:
            print(f"Ошибка при загрузке имен линий из JSON: {e}")
            self.lines_names.clear()

    def load_data(self):
        self.load_lines_names()
        self.update_column_headers()

        ac_count = config.AC_COUNT
        self.device_data = {i: {} for i in range(1, ac_count + 1)}
        self.table.setRowCount(0)

        try:
            query = f"""
            SELECT id, ac_nmb, sq_nmb, ln_nmb, ln_ch_min, ln_ch_max
            FROM SET02
            WHERE ac_nmb BETWEEN 1 AND ?
            ORDER BY ac_nmb, sq_nmb
            """
            all_data = self.db.fetch_all(query, [ac_count])

            for row_data in all_data:
                ac_nmb = row_data["ac_nmb"]
                row_id = row_data["id"]

                if ac_nmb not in self.device_data:
                    self.device_data[ac_nmb] = {}

                self.device_data[ac_nmb][row_id] = {
                    "sq_nmb": row_data["sq_nmb"],
                    "ln_nmb": row_data["ln_nmb"],
                    "ln_ch_min": "" if row_data["ln_ch_min"] is None else str(row_data["ln_ch_min"]),
                    "ln_ch_max": "" if row_data["ln_ch_max"] is None else str(row_data["ln_ch_max"])
                }

            # Для отрисовки структуры (строк) берем данные базового прибора (№1)
            base_data = self.device_data.get(1, {})
            sorted_base_items = sorted(base_data.items(), key=lambda item: item[1]['sq_nmb'])

            for base_row_id, base_row_data in sorted_base_items:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)
                sq_nmb = base_row_data["sq_nmb"]
                ln_nmb = base_row_data["ln_nmb"]

                # Колонка 0: Порядковый номер
                item_sq_nmb = QTableWidgetItem(str(sq_nmb))
                item_sq_nmb.setFlags(item_sq_nmb.flags() & ~Qt.ItemIsEditable)
                item_sq_nmb.setTextAlignment(Qt.AlignCenter)
                item_sq_nmb.setBackground(QColor(240, 240, 240))
                self.table.setItem(row_pos, 0, item_sq_nmb)

                # Колонка 1: Название
                if sq_nmb == 0:
                    item_name = QTableWidgetItem("None")
                    item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
                    item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.table.setItem(row_pos, 1, item_name)
                else:
                    combo_name = QComboBox()
                    display_names = [self.lines_names[nmb] for nmb in sorted(self.lines_names.keys())]
                    combo_name.addItems(display_names)

                    current_name = self.lines_names.get(ln_nmb, self.lines_names.get(-1, "-"))
                    index = combo_name.findText(current_name)
                    if index >= 0:
                        combo_name.setCurrentIndex(index)
                    else:
                        combo_name.addItem(current_name)
                        combo_name.setCurrentIndex(combo_name.count() - 1)

                    self.table.setCellWidget(row_pos, 1, combo_name)

                # Колонки 2+: Min и Max для каждого прибора
                for ac in range(1, ac_count + 1):
                    ac_col_base = 2 + (ac - 1) * 2

                    # Ищем данные конкретного прибора для текущей линии (sq_nmb)
                    ac_min, ac_max = "", ""
                    for ac_row_id, ac_data in self.device_data.get(ac, {}).items():
                        if ac_data["sq_nmb"] == sq_nmb:
                            ac_min = ac_data["ln_ch_min"]
                            ac_max = ac_data["ln_ch_max"]
                            break

                    item_min = QTableWidgetItem(ac_min)
                    item_min.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_pos, ac_col_base, item_min)

                    item_max = QTableWidgetItem(ac_max)
                    item_max.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_pos, ac_col_base + 1, item_max)

            self.export_ranges_to_json()
            self.generate_lines_math_interactions_json()

            if not self.validate_cross_table_consistency():
                QMessageBox.warning(self, "Внимание",
                                    "Обнаружены несоответствия между таблицами SET02, SET03 и SET07. "
                                    "Рекомендуется выполнить полную синхронизацию.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке спектральных диапазонов: {e}")

    def save_data(self):
        try:
            updated_count_total = 0
            ac_count = config.AC_COUNT

            validation_errors = []

            # 1. Валидация Min/Max для всех приборов
            for row in range(self.table.rowCount()):
                item_sq_nmb = self.table.item(row, 0)
                if not item_sq_nmb:
                    continue

                sq_nmb = int(item_sq_nmb.text())

                line_name = "Неизвестная линия"
                if sq_nmb == 0:
                    line_name = "None"
                else:
                    combo_name = self.table.cellWidget(row, 1)
                    if combo_name:
                        line_name = combo_name.currentText()

                for ac in range(1, ac_count + 1):
                    ac_col_base = 2 + (ac - 1) * 2
                    item_min = self.table.item(row, ac_col_base)
                    item_max = self.table.item(row, ac_col_base + 1)

                    if item_min and item_max:
                        min_val_str = item_min.text().strip()
                        max_val_str = item_max.text().strip()

                        if min_val_str and max_val_str:
                            try:
                                min_val = float(min_val_str.replace(',', '.'))
                                max_val = float(max_val_str.replace(',', '.'))
                                if max_val < min_val:
                                    validation_errors.append(
                                        f"Линия '{line_name}' (Пр. {ac}): Max ({max_val}) не может быть меньше Min ({min_val})")
                            except ValueError:
                                validation_errors.append(f"Линия '{line_name}' (Пр. {ac}): Некорректный формат числа")

            if validation_errors:
                QMessageBox.warning(self, "Ошибка валидации", "\n".join(validation_errors))
                return

            # 2. Обновление названий линий (ln_nmb) - синхронизируется для ВСЕХ приборов
            for row in range(self.table.rowCount()):
                item_sq_nmb = self.table.item(row, 0)
                if not item_sq_nmb:
                    continue

                sq_nmb = int(item_sq_nmb.text())
                if sq_nmb == 0:
                    continue

                combo_name = self.table.cellWidget(row, 1)
                if not combo_name:
                    continue

                new_display_name = combo_name.currentText()

                new_ln_nmb = None
                for nmb, name in self.lines_names.items():
                    if name == new_display_name:
                        new_ln_nmb = nmb
                        break

                if new_ln_nmb is None:
                    continue

                old_ln_nmb = None
                for data in self.device_data[1].values():
                    if data["sq_nmb"] == sq_nmb:
                        old_ln_nmb = data["ln_nmb"]
                        break

                if old_ln_nmb is None or new_ln_nmb == old_ln_nmb:
                    continue

                try:
                    updated_count = self.synchronize_line_changes(old_ln_nmb, new_ln_nmb, sq_nmb)
                    updated_count_total += updated_count

                    for ac_nmb in range(1, ac_count + 1):
                        for data in self.device_data[ac_nmb].values():
                            if data["sq_nmb"] == sq_nmb and data["ln_nmb"] == old_ln_nmb:
                                data["ln_nmb"] = new_ln_nmb
                except Exception as e:
                    print(f"Ошибка синхронизации для sq_nmb={sq_nmb}: {e}")

            # 3. Индивидуальное обновление Min/Max для КАЖДОГО прибора
            for row in range(self.table.rowCount()):
                item_sq_nmb = self.table.item(row, 0)
                if not item_sq_nmb:
                    continue

                sq_nmb = int(item_sq_nmb.text())

                for ac_nmb in range(1, ac_count + 1):
                    ac_col_base = 2 + (ac_nmb - 1) * 2
                    item_min = self.table.item(row, ac_col_base)
                    item_max = self.table.item(row, ac_col_base + 1)

                    new_min = item_min.text().strip() if item_min else ""
                    new_max = item_max.text().strip() if item_max else ""

                    target_id = None
                    for row_id, data in self.device_data.get(ac_nmb, {}).items():
                        if data["sq_nmb"] == sq_nmb:
                            target_id = row_id
                            break

                    if not target_id:
                        continue

                    # Проверяем и обновляем Min
                    old_min = self.device_data[ac_nmb][target_id]["ln_ch_min"]
                    if new_min != old_min:
                        try:
                            query = "UPDATE SET02 SET ln_ch_min = ? WHERE id = ? AND ac_nmb = ?"
                            if new_min == "":
                                self.db.execute(query, [None, target_id, ac_nmb])
                            else:
                                self.db.execute(query, [float(new_min.replace(',', '.')), target_id, ac_nmb])
                            self.device_data[ac_nmb][target_id]["ln_ch_min"] = new_min
                            updated_count_total += 1
                        except Exception as e:
                            print(f"Ошибка Min: {e}")

                    # Проверяем и обновляем Max
                    old_max = self.device_data[ac_nmb][target_id]["ln_ch_max"]
                    if new_max != old_max:
                        try:
                            query = "UPDATE SET02 SET ln_ch_max = ? WHERE id = ? AND ac_nmb = ?"
                            if new_max == "":
                                self.db.execute(query, [None, target_id, ac_nmb])
                            else:
                                self.db.execute(query, [float(new_max.replace(',', '.')), target_id, ac_nmb])
                            self.device_data[ac_nmb][target_id]["ln_ch_max"] = new_max
                            updated_count_total += 1
                        except Exception as e:
                            print(f"Ошибка Max: {e}")

            if updated_count_total > 0:
                QMessageBox.information(self, "Успех", f"Настройки успешно сохранены!")
                self.load_data()
                self.generate_lines_math_interactions_json()
            else:
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")

    def export_ranges_to_json(self):
        # Экспорт использует только колонку 0 и 1 (имена линий общие для всех приборов)
        try:
            range_data = []
            for row in range(self.table.rowCount()):
                item_sq_nmb = self.table.item(row, 0)
                if not item_sq_nmb:
                    continue

                try:
                    sq_nmb = int(item_sq_nmb.text())
                    if 1 <= sq_nmb <= 20:
                        combo_name = self.table.cellWidget(row, 1)
                        if combo_name:
                            selected_name = combo_name.currentText()
                            range_data.append({"number": sq_nmb, "name": selected_name})
                        else:
                            item_name = self.table.item(row, 1)
                            name = item_name.text() if item_name else f"Линия {sq_nmb}"
                            range_data.append({"number": sq_nmb, "name": name})
                except ValueError:
                    continue

            range_data.sort(key=lambda x: x["number"])
            config_dir = get_config_path()
            json_path = config_dir / "range.json"

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(range_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка при экспорте диапазонов в JSON: {e}")

    def synchronize_line_changes(self, old_ln_nmb, new_ln_nmb, sq_nmb):
        with self.db.connect() as conn:
            cursor = conn.cursor()
            updated_count = 0

            try:
                query_set02 = "UPDATE SET02 SET ln_nmb = ? WHERE sq_nmb = ? AND ln_nmb = ?"
                prepared_query, prepared_params = self.db._prepare_query_and_params(
                    query_set02, (new_ln_nmb, sq_nmb, old_ln_nmb)
                )
                cursor.execute(prepared_query, prepared_params or ())
                updated_count += cursor.rowcount

                query_set03 = "UPDATE SET03 SET ln_nmb = ? WHERE sq_nmb = ? AND ln_nmb = ?"
                prepared_query, prepared_params = self.db._prepare_query_and_params(
                    query_set03, (new_ln_nmb, sq_nmb, old_ln_nmb)
                )
                cursor.execute(prepared_query, prepared_params or ())
                updated_count += cursor.rowcount

                query_set07 = "UPDATE SET07 SET ln_nmb = ? WHERE sq_nmb = ? AND ln_nmb = ?"
                prepared_query, prepared_params = self.db._prepare_query_and_params(
                    query_set07, (new_ln_nmb, sq_nmb, old_ln_nmb)
                )
                cursor.execute(prepared_query, prepared_params or ())
                updated_count += cursor.rowcount

                conn.commit()
                return updated_count
            except Exception as e:
                conn.rollback()
                raise Exception(f"Ошибка синхронизации линий: {e}")

    def validate_cross_table_consistency(self):
        try:
            inconsistencies = []
            query_sq_nmb = "SELECT DISTINCT sq_nmb FROM SET02 WHERE sq_nmb != 0 ORDER BY sq_nmb"
            sq_nmb_list = [row["sq_nmb"] for row in self.db.fetch_all(query_sq_nmb)]

            for sq_nmb in sq_nmb_list:
                query_set02 = "SELECT DISTINCT ln_nmb FROM SET02 WHERE sq_nmb = ?"
                set02_data = self.db.fetch_all(query_set02, [sq_nmb])

                if len(set02_data) != 1:
                    continue

                expected_ln_nmb = set02_data[0]["ln_nmb"]

                query_set03 = "SELECT DISTINCT ln_nmb FROM SET03 WHERE sq_nmb = ?"
                set03_data = self.db.fetch_all(query_set03, [sq_nmb])

                if len(set03_data) == 0 or (len(set03_data) == 1 and set03_data[0]["ln_nmb"] != expected_ln_nmb):
                    inconsistencies.append(f"sq_nmb={sq_nmb}: конфликт SET02 и SET03")

                query_set07 = "SELECT DISTINCT ln_nmb FROM SET07 WHERE sq_nmb = ?"
                set07_data = self.db.fetch_all(query_set07, [sq_nmb])

                if len(set07_data) == 0 or (len(set07_data) == 1 and set07_data[0]["ln_nmb"] != expected_ln_nmb):
                    inconsistencies.append(f"sq_nmb={sq_nmb}: конфликт SET02 и SET07")

            if inconsistencies:
                print("Обнаружены несоответствия между таблицами:")
                for issue in inconsistencies:
                    print(f"  - {issue}")
                return False
            return True

        except Exception as e:
            print(f"Ошибка проверки согласованности: {e}")
            return False

    def generate_lines_math_interactions_json(self):
        try:
            config_dir = get_config_path()
            range_json_path = config_dir / "range.json"

            if not os.path.exists(range_json_path):
                return

            with open(range_json_path, "r", encoding="utf-8") as f:
                range_data = json.load(f)

            active_lines = []
            for line in range_data:
                if line["name"] != "-":
                    adjusted_number = line["number"] - 1
                    active_lines.append({
                        "original_number": line["number"],
                        "adjusted_number": adjusted_number,
                        "name": line["name"]
                    })

            interactions = []
            operations = [
                {"code": 0, "description": "Пустая строка"},
                {"code": 1, "description": "Линия"},
                {"code": 2, "description": "Умножение"},
                {"code": 3, "description": "Деление"},
                {"code": 4, "description": "Квадрат"},
                {"code": 5, "description": "Обратное значение"},
                {"code": 6, "description": "Деление на квадрат"},
                {"code": 7, "description": "Обратное значение квадрата"}
            ]

            interactions.append({"description": "", "x1": 0, "x2": 0, "op": 0})

            for line in active_lines:
                interactions.append({"description": line["name"], "x1": line["adjusted_number"], "x2": 0, "op": 1})

            for i, line1 in enumerate(active_lines):
                for j, line2 in enumerate(active_lines):
                    if i < j:
                        interactions.append(
                            {"description": f"{line1['name']} * {line2['name']}", "x1": line1["adjusted_number"],
                             "x2": line2["adjusted_number"], "op": 2})

            for line1 in active_lines:
                for line2 in active_lines:
                    if line1["adjusted_number"] != line2["adjusted_number"]:
                        interactions.append(
                            {"description": f"{line1['name']} / {line2['name']}", "x1": line1["adjusted_number"],
                             "x2": line2["adjusted_number"], "op": 3})

            for line in active_lines:
                interactions.append(
                    {"description": f"{line['name']} ^ 2", "x1": line["adjusted_number"], "x2": 0, "op": 4})

            for line in active_lines:
                interactions.append(
                    {"description": f"1 / {line['name']}", "x1": line["adjusted_number"], "x2": 0, "op": 5})

            for line1 in active_lines:
                for line2 in active_lines:
                    if line1["adjusted_number"] != line2["adjusted_number"]:
                        interactions.append(
                            {"description": f"{line1['name']} / {line2['name']} ^ 2", "x1": line1["adjusted_number"],
                             "x2": line2["adjusted_number"], "op": 6})

            for line in active_lines:
                interactions.append(
                    {"description": f"1 / {line['name']} ^ 2", "x1": line["adjusted_number"], "x2": 0, "op": 7})

            output_json_path = config_dir / "lines_math_interactions.json"

            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "operations": operations,
                    "lines": active_lines,
                    "interactions": interactions
                }, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"Ошибка при генерации JSON: {e}")
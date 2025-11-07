# views/measurement/ranges.py
import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QComboBox, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.db import Database
# Импортируем AC_COUNT из конфигурации
from config import get_config


class RangesPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        # Словарь для хранения данных по каждому ac_nmb
        # Формат: {ac_nmb: {id_строки_в_бд: {sq_nmb, ln_nmb, ln_ch_min, ln_ch_max}}}
        self.device_data = {i: {} for i in range(1, int(get_config("AC_COUNT", 1)) + 1)}
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

        # Кнопки - теперь сверху, слева
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
        btn_layout.addStretch()  # Отступ справа
        layout.addLayout(btn_layout)

        # Таблица
        self.table = QTableWidget()
        # Изначально создадим с 2 + 2*AC_COUNT столбцами
        ac_count = int(get_config("AC_COUNT", 1))
        self.table.setColumnCount(2 + 2 * ac_count)
        self.update_column_headers() # Установим заголовки
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        # Убираем нумерацию строк
        self.table.verticalHeader().setVisible(False)
        # Высота строк
        self.table.verticalHeader().setDefaultSectionSize(30)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_data()

    def update_column_headers(self):
        """Обновляет заголовки столбцов в зависимости от AC_COUNT"""
        ac_count = int(get_config("AC_COUNT", 1))
        headers = ["Порядковый №", "Название"]
        for i in range(1, ac_count + 1):
            headers.extend([f"Min (Прибор {i})", f"Max (Прибор {i})"])
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

    def load_lines_names(self):
        """Загружает имена линий из JSON файла"""
        try:
            # Определяем путь к JSON файлу
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(base_dir, "..", "..", "config")
            json_path = os.path.join(config_dir, "lines.json")

            # Проверяем существование файла
            if not os.path.exists(json_path):
                print(f"Файл {json_path} не найден")
                return

            # Читаем JSON
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Создаем словарь ln_nmb -> name
            self.lines_names.clear()
            for item in data:
                self.lines_names[item["number"]] = item["name"]

        except Exception as e:
            print(f"Ошибка при загрузке имен линий из JSON: {e}")
            self.lines_names.clear()

    def load_data(self):
        """Загружает диапазоны из SET02 для всех ac_nmb от 1 до AC_COUNT"""
        # Загружаем имена линий из JSON
        self.load_lines_names()

        # Обновляем заголовки столбцов
        self.update_column_headers()

        # Очищаем данные
        ac_count = int(get_config("AC_COUNT", 1))
        self.device_data = {i: {} for i in range(1, ac_count + 1)}
        self.table.setRowCount(0)

        try:
            # Загружаем данные для ВСЕХ групп ac_nmb одним запросом
            # ORDER BY важен: сначала по ac_nmb, потом по sq_nmb
            query = f"""
            SELECT id, ac_nmb, sq_nmb, ln_nmb, ln_ch_min, ln_ch_max
            FROM SET02
            WHERE ac_nmb BETWEEN 1 AND ?
            ORDER BY ac_nmb, sq_nmb
            """
            # Передаем ac_count как параметр в запрос
            all_data = self.db.fetch_all(query, [ac_count])

            # Организуем загруженные данные по группам ac_nmb
            for row_data in all_data:
                ac_nmb = row_data["ac_nmb"]
                row_id = row_data["id"]

                # Сохраняем данные в соответствующую группу
                if ac_nmb not in self.device_data:
                    self.device_data[ac_nmb] = {}

                self.device_data[ac_nmb][row_id] = {
                    "sq_nmb": row_data["sq_nmb"],
                    "ln_nmb": row_data["ln_nmb"],
                    "ln_ch_min": "" if row_data["ln_ch_min"] is None else str(row_data["ln_ch_min"]),
                    "ln_ch_max": "" if row_data["ln_ch_max"] is None else str(row_data["ln_ch_max"])
                }

            # Предполагаем, что структура (sq_nmb, ln_nmb) одинакова для всех ac_nmb
            # Берем данные для ac_nmb=1 как базовые для отображения в таблице
            base_data = self.device_data.get(1, {})

            # Заполняем таблицу на основе базовой структуры
            # Проходим по строкам базовой группы (ac_nmb=1)
            # Сортируем по sq_nmb для правильного порядка
            sorted_base_items = sorted(base_data.items(), key=lambda item: item[1]['sq_nmb'])

            for base_row_id, base_row_data in sorted_base_items:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)
                sq_nmb = base_row_data["sq_nmb"]
                ln_nmb = base_row_data["ln_nmb"]

                # Порядковый номер (sq_nmb) - только для чтения
                item_sq_nmb = QTableWidgetItem(str(sq_nmb))
                item_sq_nmb.setFlags(item_sq_nmb.flags() & ~Qt.ItemIsEditable)
                item_sq_nmb.setTextAlignment(Qt.AlignCenter)
                item_sq_nmb.setBackground(QColor(240, 240, 240))
                self.table.setItem(row_pos, 0, item_sq_nmb)

                # Название (общее для всех приборов)
                if sq_nmb == 0:
                    item_name = QTableWidgetItem("None")
                    item_name.setFlags(item_name.flags() & ~Qt.ItemIsEditable)
                    item_name.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    self.table.setItem(row_pos, 1, item_name)
                else:
                    # Для остальных - комбо-бокс
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

                # Min/Max для каждого прибора
                # Проходим по всем ac_nmb от 1 до AC_COUNT
                for i, ac_nmb in enumerate(range(1, ac_count + 1)):
                    # Находим соответствующую строку в данных этого прибора
                    device_row_data = None
                    device_row_id = None
                    # Ищем строку с тем же sq_nmb в группе данного прибора
                    for row_id, data in self.device_data[ac_nmb].items():
                        if data["sq_nmb"] == sq_nmb:
                            device_row_data = data
                            device_row_id = row_id
                            break

                    if device_row_data:
                        col_offset = 2 + i * 2 # Смещение для пары столбцов Min/Max

                        # Min
                        item_min = QTableWidgetItem(device_row_data.get("ln_ch_min", ""))
                        item_min.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row_pos, col_offset, item_min)

                        # Max
                        item_max = QTableWidgetItem(device_row_data.get("ln_ch_max", ""))
                        item_max.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row_pos, col_offset + 1, item_max)
                    else:
                        # Если для какого-то ac_nmb нет данных для этого sq_nmb
                        # (что не должно происходить при правильной настройке)
                        col_offset = 2 + i * 2
                        item_min = QTableWidgetItem("Н/Д")
                        item_min.setFlags(item_min.flags() & ~Qt.ItemIsEditable)
                        item_min.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row_pos, col_offset, item_min)
                        item_max = QTableWidgetItem("Н/Д")
                        item_max.setFlags(item_max.flags() & ~Qt.ItemIsEditable)
                        item_max.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row_pos, col_offset + 1, item_max)

            # После загрузки данных экспортируем в JSON
            self.export_ranges_to_json()
            # Генерируем математические взаимодействия линий
            self.generate_lines_math_interactions_json()

            # ПРОВЕРЯЕМ СОГЛАСОВАННОСТЬ МЕЖДУ ТАБЛИЦАМИ
            if not self.validate_cross_table_consistency():
                QMessageBox.warning(self, "Внимание",
                    "Обнаружены несоответствия между таблицами SET02, SET03 и SET07. "
                    "Рекомендуется выполнить полную синхронизацию.")

        except Exception as e:
            error_msg = f"Ошибка при загрузке спектральных диапазонов: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def save_data(self):
        """Сохраняет изменения в БД для всех приборов"""
        try:
            updated_count_total = 0
            ac_count = int(get_config("AC_COUNT", 1))

            # Валидация Min/Max
            validation_errors = []
            for row in range(self.table.rowCount()):
                item_sq_nmb = self.table.item(row, 0)
                if not item_sq_nmb:
                    continue

                sq_nmb = int(item_sq_nmb.text())

                # Проверяем Min/Max для каждого прибора
                for i, ac_nmb in enumerate(range(1, ac_count + 1)):
                    col_offset = 2 + i * 2

                    item_min = self.table.item(row, col_offset)
                    item_max = self.table.item(row, col_offset + 1)

                    if item_min and item_max:
                        min_val_str = item_min.text().strip()
                        max_val_str = item_max.text().strip()

                        # Если оба поля заполнены, проверяем что Max >= Min
                        if min_val_str and max_val_str:
                            try:
                                min_val = float(min_val_str)
                                max_val = float(max_val_str)
                                if max_val < min_val:
                                    # Находим имя линии для сообщения об ошибке
                                    line_name = "Неизвестная линия"
                                    if sq_nmb == 0:
                                        line_name = "None"
                                    else:
                                        combo_name = self.table.cellWidget(row, 1)
                                        if combo_name:
                                            line_name = combo_name.currentText()

                                    validation_errors.append(
                                        f"Прибор {ac_nmb}, линия '{line_name}': "
                                        f"Max ({max_val}) не может быть меньше Min ({min_val})"
                                    )
                            except ValueError:
                                # Если не числа, пропускаем проверку
                                pass

            if validation_errors:
                QMessageBox.warning(self, "Ошибка валидации", "\n".join(validation_errors))
                return

            # Обновляем названия линий для ВСЕХ приборов
            for row in range(self.table.rowCount()):
                item_sq_nmb = self.table.item(row, 0)
                if not item_sq_nmb:
                    continue

                sq_nmb = int(item_sq_nmb.text())
                if sq_nmb == 0:  # Пропускаем "None"
                    continue

                combo_name = self.table.cellWidget(row, 1)
                if not combo_name:
                    continue

                new_display_name = combo_name.currentText()

                # Находим новый ln_nmb
                new_ln_nmb = None
                for nmb, name in self.lines_names.items():
                    if name == new_display_name:
                        new_ln_nmb = nmb
                        break

                if new_ln_nmb is None:
                    continue

                # Находим старый ln_nmb (из первого прибора)
                old_ln_nmb = None
                for data in self.device_data[1].values():
                    if data["sq_nmb"] == sq_nmb:
                        old_ln_nmb = data["ln_nmb"]
                        break

                if old_ln_nmb is None or new_ln_nmb == old_ln_nmb:
                    continue

                # СИНХРОНИЗИРУЕМ ОБЕ ТАБЛИЦЫ!
                try:
                    updated_count = self.synchronize_line_changes(old_ln_nmb, new_ln_nmb, sq_nmb)
                    updated_count_total += updated_count

                    # Обновляем кэш для всех приборов
                    for ac_nmb in range(1, ac_count + 1):
                        for data in self.device_data[ac_nmb].values():
                            if data["sq_nmb"] == sq_nmb and data["ln_nmb"] == old_ln_nmb:
                                data["ln_nmb"] = new_ln_nmb

                except Exception as e:
                    print(f"Ошибка синхронизации для sq_nmb={sq_nmb}: {e}")

            # Обновляем Min/Max значений для каждого прибора
            for row in range(self.table.rowCount()):
                item_sq_nmb = self.table.item(row, 0)
                if not item_sq_nmb:
                    continue

                sq_nmb = int(item_sq_nmb.text())

                for i, ac_nmb in enumerate(range(1, ac_count + 1)):
                    # Находим ID строки в этом приборе
                    target_id = None
                    for row_id, data in self.device_data[ac_nmb].items():
                        if data["sq_nmb"] == sq_nmb:
                            target_id = row_id
                            break

                    if not target_id:
                        continue

                    col_offset = 2 + i * 2

                    # Min
                    item_min = self.table.item(row, col_offset)
                    if item_min:
                        new_min = item_min.text().strip()
                        old_min = self.device_data[ac_nmb][target_id]["ln_ch_min"]
                        if new_min != old_min:
                            try:
                                query = f"""
                                UPDATE SET02
                                SET ln_ch_min = ?
                                WHERE id = ? AND ac_nmb = ?
                                """
                                if new_min == "":
                                    self.db.execute(query, [None, target_id, ac_nmb])
                                else:
                                    self.db.execute(query, [float(new_min), target_id, ac_nmb])
                                self.device_data[ac_nmb][target_id]["ln_ch_min"] = new_min
                                updated_count_total += 1
                            except Exception as e:
                                print(f"Ошибка при обновлении ln_ch_min для ID={target_id}, ac_nmb={ac_nmb}: {e}")

                    # Max
                    item_max = self.table.item(row, col_offset + 1)
                    if item_max:
                        new_max = item_max.text().strip()
                        old_max = self.device_data[ac_nmb][target_id]["ln_ch_max"]
                        if new_max != old_max:
                            try:
                                query = f"""
                                UPDATE SET02
                                SET ln_ch_max = ?
                                WHERE id = ? AND ac_nmb = ?
                                """
                                if new_max == "":
                                    self.db.execute(query, [None, target_id, ac_nmb])
                                else:
                                    self.db.execute(query, [float(new_max), target_id, ac_nmb])
                                self.device_data[ac_nmb][target_id]["ln_ch_max"] = new_max
                                updated_count_total += 1
                            except Exception as e:
                                print(f"Ошибка при обновлении ln_ch_max для ID={target_id}, ac_nmb={ac_nmb}: {e}")

            if updated_count_total > 0:
                QMessageBox.information(self, "Успех", f"Сохранено {updated_count_total} изменений")
                self.load_data()  # Полная перезагрузка
                # После перезагрузки генерируем математические взаимодействия линий
                self.generate_lines_math_interactions_json()
            else:
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")

    def export_ranges_to_json(self):
        """Экспортирует имена линий (из комбобоксов строк sq_nmb 1-20) в config/range.json в формате [{"number": 1, "name": "..."}, ...]"""
        try:
            range_data = []
            # Проходим по строкам таблицы, соответствующим sq_nmb 1-20
            # Предполагаем, что строки упорядочены по sq_nmb
            for row in range(self.table.rowCount()):
                item_sq_nmb = self.table.item(row, 0)
                if not item_sq_nmb:
                    continue

                try:
                    sq_nmb = int(item_sq_nmb.text())
                    # Обрабатываем только строки с sq_nmb от 1 до 20
                    if 1 <= sq_nmb <= 20:
                        combo_name = self.table.cellWidget(row, 1)
                        if combo_name:
                            # Получаем выбранное имя из комбобокса
                            selected_name = combo_name.currentText()
                            range_data.append({
                                "number": sq_nmb,
                                "name": selected_name
                            })
                        else:
                            # Если комбобокса нет (например, для sq_nmb=0, хотя мы его не обрабатываем)
                            # Все равно добавляем, но с дефолтным именем
                            item_name = self.table.item(row, 1)
                            name = item_name.text() if item_name else f"Линия {sq_nmb}"
                            range_data.append({
                                "number": sq_nmb,
                                "name": name
                            })
                except ValueError:
                    # Пропускаем строки с некорректным sq_nmb
                    continue

            # Сортируем по номеру на случай, если порядок строк в таблице нарушен
            range_data.sort(key=lambda x: x["number"])

            # Определяем путь к JSON файлу
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(base_dir, "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True) # Создаем папку, если её нет
            json_path = os.path.join(config_dir, "range.json")

            # Записываем в файл
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(range_data, f, ensure_ascii=False, indent=4)

            print(f"JSON файл диапазонов успешно сохранён: {json_path}")

        except Exception as e:
            error_msg = f"Ошибка при экспорте диапазонов в JSON: {e}"
            print(error_msg)
            # Не показываем QMessageBox здесь, чтобы не перегружать UI, просто логируем

    def synchronize_line_changes(self, old_ln_nmb, new_ln_nmb, sq_nmb):
        """Синхронизирует изменения линий между SET02, SET03 и SET07 для всех записей с данным sq_nmb"""
        with self.db.connect() as conn:
            cursor = conn.cursor()
            updated_count = 0

            try:
                # Подготавливаем запрос и параметры один раз (или для каждого — неважно, логика в _prepare)
                # Обновляем SET02
                query_set02 = "UPDATE SET02 SET ln_nmb = ? WHERE sq_nmb = ? AND ln_nmb = ?"
                prepared_query, prepared_params = self.db._prepare_query_and_params(
                    query_set02, (new_ln_nmb, sq_nmb, old_ln_nmb)
                )
                cursor.execute(prepared_query, prepared_params or ())
                updated_count += cursor.rowcount

                # Обновляем SET03
                query_set03 = "UPDATE SET03 SET ln_nmb = ? WHERE sq_nmb = ? AND ln_nmb = ?"
                prepared_query, prepared_params = self.db._prepare_query_and_params(
                    query_set03, (new_ln_nmb, sq_nmb, old_ln_nmb)
                )
                cursor.execute(prepared_query, prepared_params or ())
                updated_count += cursor.rowcount

                # Обновляем SET07
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
        """Проверяет согласованность ln_nmb для каждого sq_nmb между SET02, SET03 и SET07"""
        try:
            inconsistencies = []

            # Получаем уникальные sq_nmb из SET02 (основная таблица)
            query_sq_nmb = f"""
            SELECT DISTINCT sq_nmb
            FROM SET02
            WHERE sq_nmb != 0
            ORDER BY sq_nmb
            """
            sq_nmb_list = [row["sq_nmb"] for row in self.db.fetch_all(query_sq_nmb)]

            for sq_nmb in sq_nmb_list:
                # Получаем эталонное значение ln_nmb из SET02
                query_set02 = f"""
                SELECT DISTINCT ln_nmb
                FROM SET02
                WHERE sq_nmb = ?
                """
                set02_data = self.db.fetch_all(query_set02, [sq_nmb])

                if len(set02_data) != 1:
                    inconsistencies.append(f"sq_nmb={sq_nmb}: в SET02 найдено {len(set02_data)} различных ln_nmb")
                    continue

                expected_ln_nmb = set02_data[0]["ln_nmb"]

                # Проверяем SET03
                query_set03 = f"""
                SELECT DISTINCT ln_nmb
                FROM SET03
                WHERE sq_nmb = ?
                """
                set03_data = self.db.fetch_all(query_set03, [sq_nmb])

                if len(set03_data) == 0:
                    inconsistencies.append(f"sq_nmb={sq_nmb}: отсутствует в SET03")
                elif len(set03_data) > 1:
                    inconsistencies.append(f"sq_nmb={sq_nmb}: в SET03 найдено {len(set03_data)} различных ln_nmb")
                elif set03_data[0]["ln_nmb"] != expected_ln_nmb:
                    inconsistencies.append(f"sq_nmb={sq_nmb}: SET02={expected_ln_nmb} vs SET03={set03_data[0]['ln_nmb']}")

                # Проверяем SET07
                query_set07 = f"""
                SELECT DISTINCT ln_nmb
                FROM SET07
                WHERE sq_nmb = ?
                """
                set07_data = self.db.fetch_all(query_set07, [sq_nmb])

                if len(set07_data) == 0:
                    inconsistencies.append(f"sq_nmb={sq_nmb}: отсутствует в SET07")
                elif len(set07_data) > 1:
                    inconsistencies.append(f"sq_nmb={sq_nmb}: в SET07 найдено {len(set07_data)} различных ln_nmb")
                elif set07_data[0]["ln_nmb"] != expected_ln_nmb:
                    inconsistencies.append(f"sq_nmb={sq_nmb}: SET02={expected_ln_nmb} vs SET07={set07_data[0]['ln_nmb']}")

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
        """Генерирует JSON-файл с математическими взаимодействиями линий"""
        try:
            # Загружаем данные из range.json
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(base_dir, "..", "..", "config")
            range_json_path = os.path.join(config_dir, "range.json")

            if not os.path.exists(range_json_path):
                print(f"Файл {range_json_path} не найден")
                return

            with open(range_json_path, "r", encoding="utf-8") as f:
                range_data = json.load(f)

            # Фильтруем активные линии (исключая "-")
            active_lines = []
            for line in range_data:
                if line["name"] != "-":
                    # Нумерация начинается с 0
                    adjusted_number = line["number"] - 1
                    active_lines.append({
                        "original_number": line["number"],
                        "adjusted_number": adjusted_number,
                        "name": line["name"]
                    })

            # Создаем структуру данных для математических взаимодействий
            interactions = []

            # Операции: 0=пустая строка, 1=линия, 2=умножение, 3=деление, 4=возведение в квадрат,
            # 5=обратное значение, 6=деление на квадрат, 7=обратное значение квадрата
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

            # 0. Пустая строка (первая всегда)
            interactions.append({
                "description": "",
                "x1": 0,
                "x2": 0,
                "op": 0
            })

            # 1. Линии
            for line in active_lines:
                interactions.append({
                    "description": line["name"],
                    "x1": line["adjusted_number"],
                    "x2": 0,
                    "op": 1
                })

            # 2. Умножение линий
            for i, line1 in enumerate(active_lines):
                for j, line2 in enumerate(active_lines):
                    if i < j:  # Исключаем дубликаты и умножение на себя
                        interactions.append({
                            "description": f"{line1['name']} * {line2['name']}",
                            "x1": line1["adjusted_number"],
                            "x2": line2["adjusted_number"],
                            "op": 2
                        })

            # 3. Деление линий
            for line1 in active_lines:
                for line2 in active_lines:
                    if line1["adjusted_number"] != line2["adjusted_number"]:
                        interactions.append({
                            "description": f"{line1['name']} / {line2['name']}",
                            "x1": line1["adjusted_number"],
                            "x2": line2["adjusted_number"],
                            "op": 3
                        })

            # 4. Квадраты линий
            for line in active_lines:
                interactions.append({
                    "description": f"{line['name']} ^ 2",
                    "x1": line["adjusted_number"],
                    "x2": 0,
                    "op": 4
                })

            # 5. Обратные значения линий
            for line in active_lines:
                interactions.append({
                    "description": f"1 / {line['name']}",
                    "x1": line["adjusted_number"],
                    "x2": 0,
                    "op": 5
                })

            # 6. Деление на квадраты линий
            for line1 in active_lines:
                for line2 in active_lines:
                    if line1["adjusted_number"] != line2["adjusted_number"]:
                        interactions.append({
                            "description": f"{line1['name']} / {line2['name']} ^ 2",
                            "x1": line1["adjusted_number"],
                            "x2": line2["adjusted_number"],
                            "op": 6
                        })

            # 7. Обратные значения квадратов линий
            for line in active_lines:
                interactions.append({
                    "description": f"1 / {line['name']} ^ 2",
                    "x1": line["adjusted_number"],
                    "x2": 0,
                    "op": 7
                })

            # Сохраняем в файл
            output_json_path = os.path.join(config_dir, "lines_math_interactions.json")

            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "operations": operations,
                    "lines": active_lines,
                    "interactions": interactions
                }, f, ensure_ascii=False, indent=4)

            print(f"JSON математических взаимодействий линий сохранён: {output_json_path}")
            print(f"Создано {len(interactions)} взаимодействий")

        except Exception as e:
            error_msg = f"Ошибка при генерации JSON математических взаимодействий линий: {e}"
            print(error_msg)

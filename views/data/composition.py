# views/data/composition.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QPushButton, QLabel, QHBoxLayout, QCheckBox, QComboBox, QDateTimeEdit,
    QTimeEdit, QMessageBox, QHeaderView, QScrollArea, QTableWidgetItem, QProgressDialog, QFileDialog)
from PySide6.QtCore import Qt, QDateTime, QTime
from PySide6.QtGui import QFontMetrics
from database.db import Database
import math
import json
import csv
from pathlib import Path
from utils.path_manager import get_config_path


class TimeEdit15Min(QTimeEdit):
    """Кастомный QTimeEdit с шагом 15 минут"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("HH:mm")
        self.setTime(QTime(0, 0))

    def stepBy(self, steps):
        current_time = self.time()
        minutes = current_time.minute()
        hours = current_time.hour()
        new_minutes = minutes + (steps * 15)
        if new_minutes >= 60:
            hours += 1
            new_minutes -= 60
        elif new_minutes < 0:
            hours -= 1
            new_minutes += 60

        if hours >= 24:
            hours = 0
        elif hours < 0:
            hours = 23

        self.setTime(QTime(hours, new_minutes))


class CompositionPage(QWidget):
    """Виджет для работы с химическим составом"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}
        self.intensity_columns = []
        self.init_ui()

    def _load_config_file(self, filename: str) -> list:
        config_path = get_config_path() / filename
        if not config_path.exists():
            print(f"Файл конфигурации не найден: {config_path}")
            return []
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, list):
                print(f"Ошибка: {filename} должен содержать список")
                return []
            return data
        except Exception as e:
            print(f"Ошибка загрузки файла {filename}: {str(e)}")
            return []

    def get_configured_elements(self) -> list:
        try:
            data = self._load_config_file("elements.json")
            if not data: return []
            elements = []
            for item in data:
                if not isinstance(item, dict): continue
                element_name = item.get('name', '').strip()
                if element_name and element_name not in ('-', 'None', ''):
                    elements.append(element_name)
            if all('number' in item for item in data):
                elements = sorted(elements,
                                  key=lambda x: next(item['number'] for item in data if item.get('name') == x))
            return elements
        except Exception as e:
            print(f"Ошибка в get_configured_elements: {str(e)}")
            return []

    def round_to_15_min(self, time: QTime) -> QTime:
        minute = time.minute()
        rounded_minute = (minute // 15) * 15
        return QTime(time.hour(), rounded_minute)

    def validate_dates(self) -> bool:
        dt_from = QDateTime(self.date_from.date(), self.time_from.time())
        dt_to = QDateTime(self.date_to.date(), self.time_to.time())
        if dt_to < dt_from:
            self.date_to.setStyleSheet("background-color: #ffdddd;")
            return False
        self.date_to.setStyleSheet("")
        return True

    def init_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setEditTriggers(QTableWidget.AllEditTriggers)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.verticalHeader().setVisible(False)
        return table

    def configure_table_normal(self):
        elements = self.get_configured_elements()
        column_count = 5 + len(elements) * 3
        self.table.clear()
        self.table.setColumnCount(column_count)
        headers = ["ID", "Модель", "Время (ts)", "Название пробы", "Калибр."]
        for element in elements:
            headers.extend([f"С расч ({element})", f"С кор ({element})", f"С хим ({element})"])
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 70)
        element_width = 90
        for i in range(5, column_count):
            self.table.setColumnWidth(i, element_width)

    def configure_table_intensity(self):
        column_count = 5 + len(self.intensity_columns)
        self.table.clear()
        self.table.setColumnCount(column_count)
        headers = ["ID", "Модель", "Время (ts)", "Название пробы", "Калибр."] + self.intensity_columns
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 70)
        self.table.setColumnWidth(2, 140)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 70)
        for i in range(5, column_count):
            self.table.setColumnWidth(i, 90)

    def toggle_intensity_mode(self):
        try:
            self.table.setRowCount(0)
            if self.check_inten.isChecked():
                if not self.load_intensity_columns():
                    self.check_inten.setChecked(False)
                    return
                self.configure_table_intensity()
                self.load_intensity_data()
            else:
                self.configure_table_normal()
                self.load_normal_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось переключить режим: {str(e)}")
            self.check_inten.setChecked(False)

    def load_intensity_columns(self) -> bool:
        try:
            data = self._load_config_file("range.json")
            if not data: return False
            self.intensity_columns = []
            for item in data:
                if not isinstance(item, dict): continue
                name = item.get('name', '').strip()
                if name and name != '-':
                    self.intensity_columns.append(name)
            if not self.intensity_columns: return False
            return True
        except Exception as e:
            print(f"Ошибка загрузки столбцов интенсивностей: {str(e)}")
            self.intensity_columns = []
            return False

    def load_intensity_data(self):
        try:
            self.table.setRowCount(0)
            self.original_data = {}
            pr_nmb = self.product_combo.currentData()
            if not pr_nmb or pr_nmb <= 0: return

            dt_from = QDateTime(self.date_from.date(), self.time_from.time()).toString("yyyyMMdd HH:mm:ss")
            dt_to = QDateTime(self.date_to.date(), self.time_to.time()).toString("yyyyMMdd HH:mm:ss")

            num_columns = len(self.intensity_columns)
            intensity_columns = [f"i_00_{i:02d}" for i in range(num_columns)]
            select_columns = ", ".join(intensity_columns)

            query = f"""
                SELECT id, mdl_nmb, timestamp, pr_nmb, sample_name, calibrate_sample, {select_columns}
                FROM pr_meas
                WHERE timestamp BETWEEN ? AND ?
                AND pr_nmb = ? AND active_model = 1
            """
            params = [dt_from, dt_to, pr_nmb]
            conditions = []
            if self.check_man.isChecked():
                conditions.append("meas_type = 0")
            else:
                conditions.append("meas_type = 1")
            if self.check_calib.isChecked(): conditions.append("calibrate_sample = 1")
            if conditions: query += " AND " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC"
            if self.db.db_type == 'postgres': query += " LIMIT 1000"

            rows = self.db.fetch_all(query, params)
            if not rows:
                QMessageBox.information(self, "Информация", "Данные интенсивностей не найдены.")
                return

            for row in rows:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)

                id_item = QTableWidgetItem(str(row.get('id', '')))
                id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)

                # Сохраняем id, pr_nmb и timestamp для UPDATE
                id_item.setData(Qt.UserRole, {
                    'id': row.get('id'),
                    'pr_nmb': row.get('pr_nmb'),
                    'timestamp': row.get('timestamp')
                })
                self.table.setItem(row_pos, 0, id_item)

                model_item = QTableWidgetItem(str(row.get('mdl_nmb', '')))
                model_item.setFlags(model_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_pos, 1, model_item)

                ts = row.get('timestamp')
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, 'strftime') else str(ts or "")
                time_item = QTableWidgetItem(ts_str)
                time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_pos, 2, time_item)

                sample_name = row.get('sample_name', '') or ''
                name_item = QTableWidgetItem(sample_name)
                self.table.setItem(row_pos, 3, name_item)
                self.original_data[(row_pos, 3)] = sample_name

                calib_val = row.get('calibrate_sample', 0)
                calib_item = QTableWidgetItem()
                calib_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                calib_item.setCheckState(Qt.Checked if calib_val else Qt.Unchecked)
                self.table.setItem(row_pos, 4, calib_item)
                self.original_data[(row_pos, 4)] = 1 if calib_val else 0

                for i in range(num_columns):
                    col_name = f"i_00_{i:02d}"
                    val = row.get(col_name)
                    item_text = f"{float(val):.4f}" if val is not None else ""
                    int_item = QTableWidgetItem(item_text)
                    int_item.setFlags(int_item.flags() & ~Qt.ItemIsEditable)
                    self.table.setItem(row_pos, 5 + i, int_item)

            self.table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки интенсивностей: {str(e)}")

    def load_normal_data(self):
        try:
            self.table.setRowCount(0)
            self.original_data = {}
            pr_nmb = self.product_combo.currentData()
            if not pr_nmb or pr_nmb <= 0: return

            dt_from = QDateTime(self.date_from.date(), self.time_from.time()).toString("yyyyMMdd HH:mm:ss")
            dt_to = QDateTime(self.date_to.date(), self.time_to.time()).toString("yyyyMMdd HH:mm:ss")

            query = """
            SELECT 
                id, mdl_nmb, timestamp, cuv_nmb, meas_type, pr_nmb, sample_name, calibrate_sample,
                c_01,c_02,c_03,c_04,c_05,c_06,c_07,c_08,
                c_cor_01,c_cor_02,c_cor_03,c_cor_04,c_cor_05,c_cor_06,c_cor_07,c_cor_08,
                c_chem_01,c_chem_02,c_chem_03,c_chem_04,c_chem_05,c_chem_06,c_chem_07,c_chem_08
            FROM pr_meas
            WHERE timestamp BETWEEN ? AND ?
            AND pr_nmb = ? AND active_model = 1
            """
            params = [dt_from, dt_to, pr_nmb]
            conditions = []
            if self.check_man.isChecked():
                conditions.append("meas_type = 0")
            else:
                conditions.append("meas_type = 1")
            if self.check_chem.isChecked():
                chem_conditions = [f"c_chem_{i:02d} <> 0" for i in range(1, 9)]
                conditions.append(f"({' OR '.join(chem_conditions)})")
            if self.check_calib.isChecked(): conditions.append("calibrate_sample = 1")
            if conditions: query += " AND " + " AND ".join(conditions)

            query += " ORDER BY timestamp DESC"
            if self.db.db_type == 'postgres': query += " LIMIT 1000"

            rows = self.db.fetch_all(query, params)
            if not rows:
                QMessageBox.information(self, "Информация", "Данные не найдены.")
                return

            elements = self.get_configured_elements()
            for row in rows:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)

                id_item = QTableWidgetItem(str(row.get('id', '')))
                id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)

                # Сохраняем id, pr_nmb и timestamp для UPDATE
                id_item.setData(Qt.UserRole, {
                    'id': row.get('id'),
                    'pr_nmb': row.get('pr_nmb'),
                    'timestamp': row.get('timestamp')
                })
                self.table.setItem(row_pos, 0, id_item)

                model_item = QTableWidgetItem(str(row.get('mdl_nmb', '')))
                model_item.setFlags(model_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_pos, 1, model_item)

                ts = row.get('timestamp')
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, 'strftime') else str(ts or "")
                time_item = QTableWidgetItem(ts_str)
                time_item.setFlags(time_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_pos, 2, time_item)

                sample_name = row.get('sample_name', '') or ''
                name_item = QTableWidgetItem(sample_name)
                self.table.setItem(row_pos, 3, name_item)
                self.original_data[(row_pos, 3)] = sample_name

                calib_val = row.get('calibrate_sample', 0)
                calib_item = QTableWidgetItem()
                calib_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsUserCheckable)
                calib_item.setCheckState(Qt.Checked if calib_val else Qt.Unchecked)
                self.table.setItem(row_pos, 4, calib_item)
                self.original_data[(row_pos, 4)] = 1 if calib_val else 0

                for i, element in enumerate(elements, 1):
                    if i > 8: break
                    col_base = 5 + (i - 1) * 3
                    for prefix in ['c_', 'c_cor_', 'c_chem_']:
                        val = row.get(f"{prefix}{i:02d}")
                        item_text = f"{float(val):.4f}" if val is not None else ""
                        item = QTableWidgetItem(item_text)
                        if prefix == 'c_chem_':
                            item.setFlags(item.flags() | Qt.ItemIsEditable)
                            try:
                                self.original_data[(row_pos, col_base)] = float(item_text)
                            except:
                                self.original_data[(row_pos, col_base)] = 0.0
                        else:
                            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        self.table.setItem(row_pos, col_base, item)
                        col_base += 1

            self.table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {str(e)}")
            self.table.setRowCount(0)
            self.original_data = {}

    def save_data(self):
        """Сохраняет измененную химию, имя пробы и галочку во ВСЕ модели текущего измерения"""
        from datetime import datetime, timedelta

        try:
            updates = []

            for row in range(self.table.rowCount()):
                id_item = self.table.item(row, 0)
                if not id_item: continue
                meta = id_item.data(Qt.UserRole)
                if not meta: continue

                row_changes = {}

                # 1. Проверка Названия пробы (столбец 3)
                item_sn = self.table.item(row, 3)
                new_sn = item_sn.text().strip() if item_sn else ""
                old_sn = self.original_data.get((row, 3), "")
                if new_sn != old_sn:
                    row_changes['sample_name'] = new_sn

                # 2. Проверка Калибровки (столбец 4)
                item_cal = self.table.item(row, 4)
                if item_cal:
                    new_cal = 1 if item_cal.checkState() == Qt.Checked else 0
                    old_cal = self.original_data.get((row, 4), 0)
                    if new_cal != old_cal:
                        # calibrate_sample в Postgres — BOOLEAN
                        row_changes['calibrate_sample'] = bool(new_cal)

                # 3. Проверка Химии (только если не режим Интенсивностей)
                if not self.check_inten.isChecked():
                    for col in range(5, self.table.columnCount()):
                        header = self.table.horizontalHeaderItem(col)
                        if header and "С хим" in header.text():
                            item_chem = self.table.item(row, col)
                            if item_chem:
                                try:
                                    new_chem = float(item_chem.text().replace(',', '.'))
                                except ValueError:
                                    new_chem = 0.0
                                old_chem = self.original_data.get((row, col), 0.0)
                                if not math.isclose(new_chem, old_chem, rel_tol=1e-5, abs_tol=1e-8):
                                    element_name = header.text().split("(")[1].split(")")[0]
                                    element_idx = self.get_configured_elements().index(element_name) + 1
                                    row_changes[f'c_chem_{element_idx:02d}'] = new_chem

                if row_changes:
                    updates.append((meta, row_changes))

            if not updates:
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения")
                return

            progress = QProgressDialog("Сохранение изменений...", "Отмена", 0, len(updates), self)
            progress.setWindowModality(Qt.WindowModal)
            success_count = 0

            for i, (meta, fields) in enumerate(updates):
                if progress.wasCanceled(): break

                pr_nmb = meta['pr_nmb']
                ts = meta['timestamp']

                # Приводим к объекту datetime, если пришло строкой
                if isinstance(ts, str):
                    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
                        try:
                            ts = datetime.strptime(ts, fmt)
                            break
                        except ValueError:
                            pass

                set_clauses = [f"{k} = ?" for k in fields.keys()]
                params = list(fields.values())

                if isinstance(ts, datetime):
                    # Создаем окно ±3 секунды в безопасном формате YYYYMMDD HH:mm:ss
                    ts_min = (ts - timedelta(seconds=3)).strftime("%Y%m%d %H:%M:%S")
                    ts_max = (ts + timedelta(seconds=3)).strftime("%Y%m%d %H:%M:%S")

                    query = f"UPDATE pr_meas SET {', '.join(set_clauses)} WHERE pr_nmb = ? AND timestamp BETWEEN ? AND ?"
                    params.extend([pr_nmb, ts_min, ts_max])
                else:
                    # Резервный вариант на случай непредвиденного формата даты (обновит хотя бы текущую строку)
                    query = f"UPDATE pr_meas SET {', '.join(set_clauses)} WHERE id = ?"
                    params.append(meta['id'])

                try:
                    self.db.execute(query, params)
                    success_count += 1
                except Exception as e:
                    print(f"Ошибка сохранения: {e}")

                progress.setValue(i + 1)

            QMessageBox.information(
                self,
                "Результат",
                f"Успешно сохранено проб: {success_count} из {len(updates)}\n(Изменения применены ко всем моделям измерения)."
            )

            self.load_data()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")

    def export_to_csv(self):
        """Экспорт таблицы в CSV файл"""
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт в CSV", "", "CSV Files (*.csv)")
        if not path: return
        try:
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')
                headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
                writer.writerow(headers)
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if col == 4:  # Столбец калибровки
                            row_data.append("1" if item and item.checkState() == Qt.Checked else "0")
                        else:
                            row_data.append(item.text() if item else "")
                    writer.writerow(row_data)
            QMessageBox.information(self, "Успех", "Данные успешно выгружены в CSV.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{e}")

    def force_reload_data(self):
        try:
            if not self.check_inten.isChecked(): self.configure_table_normal()
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении данных: {str(e)}")

    def load_data(self):
        """Единая точка входа для загрузки данных (вызывается при смене фильтров)"""
        if hasattr(self, 'check_inten') and self.check_inten.isChecked():
            self.load_intensity_data()
        else:
            self.load_normal_data()

    def load_products_list(self):
        try:
            products = self.db.fetch_all("SELECT pr_nmb, pr_name FROM cfg02 WHERE pr_nmb > 0 ORDER BY pr_nmb")
            self.product_combo.blockSignals(True)
            self.product_combo.clear()
            for p in products: self.product_combo.addItem(f"№{p['pr_nmb']}: {p['pr_name']}", p['pr_nmb'])
            self.product_combo.blockSignals(False)
        except Exception as e:
            print(f"Ошибка загрузки списка: {e}")

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setMinimumWidth(800)

        title = QLabel("Ввод химических содержаний и управление пробами")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        container = QHBoxLayout()
        container.setAlignment(Qt.AlignLeft)
        container.setSpacing(10)

        checkboxes = QVBoxLayout()
        checkboxes.setSpacing(10)
        self.check_man = QCheckBox("Ручное измерение")
        self.check_man.stateChanged.connect(self.load_data)
        self.check_chem = QCheckBox("Наличие химии")
        self.check_chem.stateChanged.connect(self.load_data)
        self.check_calib = QCheckBox("Калибровочные пробы")
        self.check_calib.stateChanged.connect(self.load_data)
        self.check_inten = QCheckBox("Интенсивности")
        self.check_inten.setChecked(False)
        self.check_inten.stateChanged.connect(self.toggle_intensity_mode)

        checkboxes.addWidget(self.check_man)
        checkboxes.addWidget(self.check_chem)
        checkboxes.addWidget(self.check_calib)
        checkboxes.addWidget(self.check_inten)
        container.addLayout(checkboxes)

        dates_layout = QVBoxLayout()
        dates_layout.setSpacing(10)

        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("От:"))
        self.date_from = QDateTimeEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDateTime(QDateTime.currentDateTime())
        self.date_from.setFixedWidth(100)
        from_layout.addWidget(self.date_from)

        self.time_from = TimeEdit15Min()
        self.time_from.setTime(self.round_to_15_min(QTime.currentTime()))
        from_layout.addWidget(self.time_from)
        dates_layout.addLayout(from_layout)

        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("До:"))
        self.date_to = QDateTimeEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.date_to.setFixedWidth(100)
        to_layout.addWidget(self.date_to)

        self.time_to = TimeEdit15Min()
        self.time_to.setTime(self.round_to_15_min(QTime.currentTime()))
        to_layout.addWidget(self.time_to)
        dates_layout.addLayout(to_layout)
        container.addLayout(dates_layout)
        main_layout.addLayout(container)

        product_layout = QHBoxLayout()
        product_layout.addWidget(QLabel("Выберите продукт:"))
        self.product_combo = QComboBox()
        self.product_combo.setFixedWidth(200)
        self.load_products_list()
        self.product_combo.currentIndexChanged.connect(self.force_reload_data)
        product_layout.addWidget(self.product_combo)
        product_layout.addStretch()
        main_layout.addLayout(product_layout)

        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignLeft)
        btn_layout.setSpacing(10)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.force_reload_data)

        self.save_btn = QPushButton("💾 Сохранить изменения")
        self.save_btn.setStyleSheet("background-color: #dcfce7; font-weight: bold; border: 1px solid #22c55e;")
        self.save_btn.clicked.connect(self.save_data)

        self.export_btn = QPushButton("📊 Экспорт в CSV")
        self.export_btn.clicked.connect(self.export_to_csv)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.export_btn)
        main_layout.addLayout(btn_layout)

        self.table = self.init_table()
        self.configure_table_normal()

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_layout.addWidget(scroll_area)

        self.date_from.dateTimeChanged.connect(self.validate_dates)
        self.time_from.timeChanged.connect(self.validate_dates)
        self.date_to.dateTimeChanged.connect(self.validate_dates)
        self.time_to.timeChanged.connect(self.validate_dates)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_products_list()
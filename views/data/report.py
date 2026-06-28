# views/data/report.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QPushButton, QLabel,
    QHBoxLayout, QComboBox, QDateTimeEdit, QMessageBox,
    QHeaderView, QTableWidgetItem, QTimeEdit, QFileDialog
)
from PySide6.QtCore import Qt, QDateTime, QTime
from PySide6.QtGui import QFontMetrics, QColor, QFont
from database.db import Database
import json
from pathlib import Path
import statistics
from utils.path_manager import get_config_path


# === КЛАСС ДЛЯ УМНОЙ ЧИСЛОВОЙ СОРТИРОВКИ ===
class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        def to_float(text):
            if not text: return None
            t = text.strip().replace(',', '.').replace('%', '')
            if t in ("-", "--", "---"): return None
            try:
                return float(t)
            except ValueError:
                return None

        v1 = to_float(self.text())
        v2 = to_float(other.text())

        if v1 is not None and v2 is not None: return v1 < v2
        if v1 is None and v2 is not None: return True
        if v1 is not None and v2 is None: return False
        return super().__lt__(other)


class TimeEdit15Min(QTimeEdit):
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


class ReportPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self._config_dir = get_config_path()
        self.init_ui()
        self.setup_connections()

    # ================== ЗАГРУЗКА КОНФИГУРАЦИИ ==================
    def _load_config_file(self, filename: str) -> list:
        config_path = get_config_path() / filename
        if not config_path.exists(): return []
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def get_configured_elements(self) -> list:
        data = self._load_config_file("elements.json")
        if not data: return []
        elements = []
        for item in data:
            try:
                if isinstance(item, dict):
                    name = item.get('name', '').strip()
                    if name and name not in ('-', 'None', ''):
                        elements.append(name)
            except:
                continue
        if all('number' in item for item in data):
            elements = sorted(elements, key=lambda x: next(item['number'] for item in data if item.get('name') == x))
        return elements

    def get_normatives_from_db(self, pr_nmb: int):
        try:
            query = "SELECT el_nmb, delta_c_01, delta_c_02 FROM set08 WHERE pr_nmb = ? ORDER BY el_nmb"
            normatives = self.db.fetch_all(query, [pr_nmb])
            return {n['el_nmb']: (self.safe_float(n['delta_c_01']), self.safe_float(n['delta_c_02'])) for n in
                    normatives}
        except:
            return {}

    def get_active_model_coefficients(self, pr_nmb: int):
        try:
            res = self.db.fetch_one("SELECT mdl_nmb FROM mdl_set WHERE pr_nmb = ? AND active_model = 1", [pr_nmb])
            if not res: return None, None
            mdl_nmb = res['mdl_nmb']
            coeffs = self.db.fetch_all("SELECT * FROM el_set WHERE pr_nmb = ? AND mdl_nmb = ? ORDER BY el_nmb",
                                       [pr_nmb, mdl_nmb])
            return mdl_nmb, coeffs
        except:
            return None, None

    # ================== ИНТЕРФЕЙС И ТАБЛИЦЫ ==================
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(700)

        title = QLabel("Отчет по химическим содержаниям")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # --- НАСТРОЙКИ ---
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(15)

        product_layout = QHBoxLayout()
        product_layout.addWidget(QLabel("Продукт:"))
        self.product_combo = QComboBox()
        self.load_products_list()
        self.product_combo.setFixedWidth(250)
        product_layout.addWidget(self.product_combo)
        product_layout.addStretch()
        settings_layout.addLayout(product_layout)

        dates_layout = QVBoxLayout()
        dates_layout.setSpacing(8)

        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("От:"))
        self.date_from = QDateTimeEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self.date_from.setFixedWidth(90)
        self.time_from = TimeEdit15Min()
        self.time_from.setTime(self.round_to_15_min(QTime(0, 0)))
        self.time_from.setFixedWidth(60)
        from_layout.addWidget(self.date_from)
        from_layout.addWidget(self.time_from)
        from_layout.addStretch()
        dates_layout.addLayout(from_layout)

        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("До:"))
        self.date_to = QDateTimeEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDateTime(QDateTime.currentDateTime())
        self.date_to.setFixedWidth(90)
        self.time_to = TimeEdit15Min()
        self.time_to.setTime(self.round_to_15_min(QTime.currentTime()))
        self.time_to.setFixedWidth(60)
        to_layout.addWidget(self.date_to)
        to_layout.addWidget(self.time_to)
        to_layout.addStretch()
        dates_layout.addLayout(to_layout)

        settings_layout.addLayout(dates_layout)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)
        self.load_btn = QPushButton("Выгрузка из БД")
        self.load_btn.setFixedSize(150, 30)
        buttons_layout.addWidget(self.load_btn)

        self.export_btn = QPushButton("Выгрузка в файл")
        self.export_btn.setFixedSize(150, 30)
        buttons_layout.addWidget(self.export_btn)
        buttons_layout.addStretch()
        settings_layout.addLayout(buttons_layout)

        main_layout.addLayout(settings_layout)

        # --- ТАБЛИЦА СТАТИСТИКИ (Верхняя) ---
        self.stats_table = QTableWidget()
        self.stats_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stats_table.setSelectionMode(QTableWidget.NoSelection)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.horizontalHeader().setVisible(True)
        self.stats_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.stats_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_layout.addWidget(self.stats_table)

        main_layout.addSpacing(30)

        # --- ТАБЛИЦА ДАННЫХ (Нижняя) ---
        self.data_table = QTableWidget()
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.verticalHeader().setVisible(False)
        self.data_table.horizontalHeader().setVisible(True)
        self.data_table.setSortingEnabled(True)
        self.data_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.data_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        main_layout.addWidget(self.data_table)

        self.configure_tables()

    def load_products_list(self):
        """Загрузка списка продуктов из базы данных"""
        # ИСПРАВЛЕНИЕ: фильтр WHERE pr_nmb > 0 исключает продукт -1
        products = self.db.fetch_all("SELECT pr_nmb, pr_name FROM cfg02 WHERE pr_nmb > 0 ORDER BY pr_nmb")
        self.product_combo.clear()
        for p in products:
            self.product_combo.addItem(f"№{p['pr_nmb']}: {p['pr_name']}", p['pr_nmb'])

    def configure_tables(self):
        elements = self.get_configured_elements()
        col_count = 1 + len(elements) * 4

        headers_stats = ["Показатель"]
        headers_data = ["Время цикла"]
        for _ in elements:
            headers_stats.extend(["С расч", "С хим", "ΔC", "Отн. %"])
            headers_data.extend(["С расч", "С хим", "ΔC", "Отн. %"])

        # === 1. ТАБЛИЦА СТАТИСТИКИ ===
        self.stats_table.setColumnCount(col_count)
        self.stats_table.setHorizontalHeaderLabels(headers_stats)
        self.stats_table.setRowCount(5)

        self.stats_table.verticalHeader().setDefaultSectionSize(30)
        self.stats_table.setFixedHeight(30 + 5 * 30 + 2)

        item_corner = QTableWidgetItem("Элемент:")
        item_corner.setBackground(QColor("#d1d5db"))
        self.stats_table.setItem(0, 0, item_corner)

        for i, el in enumerate(elements):
            col_base = 1 + i * 4
            self.stats_table.setSpan(0, col_base, 1, 4)
            item_el = QTableWidgetItem(el)
            item_el.setTextAlignment(Qt.AlignCenter)
            font = item_el.font()
            font.setBold(True)
            item_el.setFont(font)
            item_el.setBackground(QColor("#d1d5db"))
            self.stats_table.setItem(0, col_base, item_el)

        bold_font = QFont()
        bold_font.setBold(True)
        for i, name in enumerate(["Среднее", "СКО", "Норматив", "Вывод"]):
            item = QTableWidgetItem(name)
            item.setFont(bold_font)
            item.setBackground(QColor("#f3f4f6"))
            self.stats_table.setItem(i + 1, 0, item)

        # === 2. ТАБЛИЦА ДАННЫХ ===
        self.data_table.setSortingEnabled(False)
        self.data_table.setColumnCount(col_count)
        self.data_table.setHorizontalHeaderLabels(headers_data)
        self.data_table.setSortingEnabled(True)

        time_width = 140
        element_width = 85

        for table in (self.stats_table, self.data_table):
            table.setColumnWidth(0, time_width)
            for i in range(1, col_count):
                table.setColumnWidth(i, element_width)

    def setup_connections(self):
        self.load_btn.clicked.connect(self.load_report_data)
        self.export_btn.clicked.connect(self.export_to_file)
        self.data_table.doubleClicked.connect(self.delete_selected_row)

        self.date_from.dateTimeChanged.connect(self.validate_dates)
        self.time_from.timeChanged.connect(self.validate_dates)
        self.date_to.dateTimeChanged.connect(self.validate_dates)
        self.time_to.timeChanged.connect(self.validate_dates)

        # Синхронизация скролла
        self.data_table.horizontalScrollBar().valueChanged.connect(
            lambda val: self.stats_table.horizontalScrollBar().setValue(val)
        )
        self.stats_table.horizontalScrollBar().valueChanged.connect(
            lambda val: self.data_table.horizontalScrollBar().setValue(val)
        )

    # ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
    def round_to_15_min(self, time: QTime) -> QTime:
        return QTime(time.hour(), (time.minute() // 15) * 15)

    def validate_dates(self) -> bool:
        dt_from = QDateTime(self.date_from.date(), self.time_from.time())
        dt_to = QDateTime(self.date_to.date(), self.time_to.time())
        if dt_to < dt_from:
            self.date_to.setStyleSheet("background-color: #ffdddd;")
            QMessageBox.warning(self, "Ошибка", "Дата 'До' не может быть раньше 'От'!")
            return False
        self.date_to.setStyleSheet("")
        return True

    def safe_float(self, value):
        if value is None: return 0.0
        try:
            return float(value)
        except:
            return 0.0

    def safe_int(self, value):
        if value is None: return 0
        try:
            return int(value)
        except:
            return 0

    def get_f_critical_value(self, n):
        f_table = {1: 161.4, 2: 18.51, 3: 10.13, 4: 7.71, 5: 6.61, 6: 5.99, 7: 5.59, 8: 5.32, 9: 5.12, 10: 4.96,
                   11: 4.84, 12: 4.75, 13: 4.67, 14: 4.60, 15: 4.54, 20: 4.35, 30: 4.17, 40: 4.08, 60: 4.00, 120: 3.92}
        df = max(n - 1, 1)
        if df in f_table:
            return f_table[df]
        elif df > 120:
            return 3.84
        keys = sorted(f_table.keys())
        for i in range(len(keys) - 1):
            if keys[i] <= df <= keys[i + 1]:
                return f_table[keys[i]] + (f_table[keys[i + 1]] - f_table[keys[i]]) * (df - keys[i]) / (
                        keys[i + 1] - keys[i])
        return 4.0

    # ================== ЛОГИКА РАСЧЕТОВ ==================
    def calculate_operation(self, op1, op2, oper, row_data, is_intensity=True):
        try:
            if is_intensity:
                v1, v2 = self.safe_float(row_data.get(f'i_00_{op1:02d}')), self.safe_float(
                    row_data.get(f'i_00_{op2:02d}'))
            else:
                v1, v2 = self.safe_float(row_data.get(f'c_{op1 + 1:02d}')), self.safe_float(
                    row_data.get(f'c_{op2 + 1:02d}'))

            if oper == 0: return 0
            if oper == 1: return v1
            if oper == 2: return v1 * v2
            if oper == 3: return v1 / v2 if v2 != 0 else 0
            if oper == 4: return v1 * v1
            if oper == 5: return 1 / v1 if v1 != 0 else 0
            if oper == 6: return v1 / (v2 * v2) if v2 != 0 else 0
            if oper == 7: return 1 / (v1 * v1) if v1 != 0 else 0
            return 0
        except:
            return 0

    def calculate_concentration(self, row_data, coeffs, el_num):
        try:
            is_int = (self.safe_int(coeffs.get('meas_type')) == 0)
            pref_k = "k_i_alin" if is_int else "k_c_alin"
            pref_kl = "k_i_klin" if is_int else "k_c_klin"
            pref_op1 = "operand_i_01_" if is_int else "operand_c_01_"
            pref_op2 = "operand_i_02_" if is_int else "operand_c_02_"
            pref_oper = "operator_i_" if is_int else "operator_c_"

            c = self.safe_float(coeffs.get(f'{pref_k}00'))
            for i in range(1, 6):
                op1 = self.safe_int(coeffs.get(f'{pref_op1}0{i}'))
                op2 = self.safe_int(coeffs.get(f'{pref_op2}0{i}'))
                oper = self.safe_int(coeffs.get(f'{pref_oper}0{i}'))
                res = self.calculate_operation(op1, op2, oper, row_data, is_int)
                c += self.safe_float(coeffs.get(f'{pref_k}0{i}')) * res

            return self.safe_float(coeffs.get(f'{pref_kl}00')) + self.safe_float(coeffs.get(f'{pref_kl}01', 1.0)) * c
        except:
            return 0

    # ================== ЗАГРУЗКА И ВЫВОД ДАННЫХ ==================
    def load_report_data(self):
        try:
            if not self.validate_dates(): return

            dt_from = QDateTime(self.date_from.date(), self.time_from.time()).toString("yyyy-MM-dd HH:mm:ss")
            dt_to = QDateTime(self.date_to.date(), self.time_to.time()).toString("yyyy-MM-dd HH:mm:ss")
            pr_nmb = self.product_combo.currentData()

            # ИСПРАВЛЕНИЕ: Защита, если продукт не выбран или это заглушка (<=0)
            if not pr_nmb or pr_nmb <= 0:
                self.data_table.setRowCount(0)
                QMessageBox.warning(self, "Ошибка", "Выберите корректный продукт для отчета.")
                return

            active_model, coefficients = self.get_active_model_coefficients(pr_nmb)
            if not coefficients:
                QMessageBox.warning(self, "Ошибка", "Не найдены коэффициенты активной модели для продукта.")
                return

            query = """
            SELECT id, mdl_nmb, meas_dt,
                c_01, c_02, c_03, c_04, c_05, c_06, c_07, c_08,
                c_chem_01, c_chem_02, c_chem_03, c_chem_04, c_chem_05, c_chem_06, c_chem_07, c_chem_08,
                i_00_00, i_00_01, i_00_02, i_00_03, i_00_04, i_00_05, i_00_06, i_00_07, i_00_08, i_00_09,
                i_00_10, i_00_11, i_00_12, i_00_13, i_00_14, i_00_15, i_00_16, i_00_17, i_00_18, i_00_19
            FROM pr_meas
            WHERE meas_dt BETWEEN ? AND ? AND pr_nmb = ? AND mdl_nmb = ?
            AND (c_chem_01<>0 OR c_chem_02<>0 OR c_chem_03<>0 OR c_chem_04<>0 OR c_chem_05<>0 OR c_chem_06<>0)
            ORDER BY meas_dt
            """
            rows = self.db.fetch_all(query, [dt_from, dt_to, pr_nmb, active_model])

            if not rows:
                QMessageBox.information(self, "Информация", "Данные не найдены.")
                self.data_table.setRowCount(0)
                return

            elements = self.get_configured_elements()
            self.configure_tables()

            self.data_table.setSortingEnabled(False)
            self.data_table.setRowCount(len(rows))

            for row_idx, row in enumerate(rows):
                dt_str = row.get('meas_dt')
                dt_str = dt_str.strftime("%Y-%m-%d %H:%M:%S") if hasattr(dt_str, 'strftime') else str(dt_str)
                self.data_table.setItem(row_idx, 0, QTableWidgetItem(dt_str))

                for i, _ in enumerate(elements, 1):
                    if i > 8: break
                    col_base = 1 + (i - 1) * 4

                    el_coeffs = next((c for c in coefficients if c['el_nmb'] == i), None)
                    c_calc = self.calculate_concentration(row, el_coeffs, i) if el_coeffs else 0
                    c_chem = float(row.get(f'c_chem_{i:02d}', 0) or 0)

                    calc_item = NumericItem(f"{c_calc:.4f}")
                    calc_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.data_table.setItem(row_idx, col_base, calc_item)

                    if c_chem == 0:
                        chem_item, d_item, p_item = NumericItem("-"), NumericItem("-"), NumericItem("-")
                    else:
                        chem_item = NumericItem(f"{c_chem:.4f}")
                        delta_c = c_calc - c_chem
                        d_item = NumericItem(f"{delta_c:.4f}")
                        percent = round((delta_c / c_chem) * 100)
                        p_item = NumericItem(f"{percent:.0f}%")

                        if abs(delta_c) > 0.1: d_item.setBackground(QColor(255, 255, 200))
                        if abs(percent) > 10: p_item.setBackground(QColor(255, 255, 200))

                    for it, offset in zip([chem_item, d_item, p_item], [1, 2, 3]):
                        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        self.data_table.setItem(row_idx, col_base + offset, it)

            self.data_table.setSortingEnabled(True)
            self.update_statistics()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {e}")

    # ================== СТАТИСТИКА ==================
    def delete_selected_row(self, index):
        row = index.row()
        reply = QMessageBox.question(self, "Удаление", "Исключить эту строку из отчета и пересчитать статистику?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.data_table.removeRow(row)
            self.update_statistics()

    def update_statistics(self):
        pr_nmb = self.product_combo.currentData()
        # ИСПРАВЛЕНИЕ: Защита перед запросом нормативов
        if not pr_nmb or pr_nmb <= 0:
            return

        elements = self.get_configured_elements()
        normatives = self.get_normatives_from_db(pr_nmb) if pr_nmb else {}

        n_rows = self.data_table.rowCount()
        f_crit = self.get_f_critical_value(n_rows)

        light_green = QColor(200, 255, 200)
        light_red = QColor(255, 200, 200)
        default_bg = QColor(255, 255, 255)

        for col_idx, element in enumerate(elements):
            col_base = 1 + col_idx * 4
            el_num = col_idx + 1

            calcs, chems, deltas, rels = [], [], [], []
            for r in range(n_rows):
                try:
                    c_it = self.data_table.item(r, col_base)
                    ch_it = self.data_table.item(r, col_base + 1)
                    d_it = self.data_table.item(r, col_base + 2)
                    r_it = self.data_table.item(r, col_base + 3)

                    if ch_it and ch_it.text() != "-":
                        calcs.append(float(c_it.text().replace(',', '.')))
                        chems.append(float(ch_it.text().replace(',', '.')))
                        deltas.append(float(d_it.text().replace(',', '.')))
                        rels.append(float(r_it.text().replace('%', '').replace(',', '.')))
                except:
                    continue

            norm_d1, norm_d2 = normatives.get(el_num, (0.0, 0.0))

            if len(calcs) < 5:
                for r in (1, 2, 4):
                    for c in range(col_base, col_base + 4):
                        it = QTableWidgetItem("-")
                        it.setBackground(default_bg)
                        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        self.stats_table.setItem(r, c, it)

                self.stats_table.setItem(3, col_base, QTableWidgetItem("-"))
                self.stats_table.setItem(3, col_base + 1, QTableWidgetItem("-"))
                self._set_stat_item(3, col_base + 2, f"{norm_d1:.4f}" if norm_d1 > 0 else "-")
                self._set_stat_item(3, col_base + 3, f"{norm_d2:.0f}%" if norm_d2 > 0 else "-")
                continue

            avg_calc = statistics.mean(calcs)
            avg_chem = statistics.mean(chems)
            avg_d = statistics.mean(deltas)
            avg_r = statistics.mean(rels)

            std_d = statistics.stdev(deltas) if len(deltas) > 1 else 0
            std_r = statistics.stdev(rels) if len(rels) > 1 else 0

            # 1: Среднее
            self._set_stat_item(1, col_base, f"{avg_calc:.6f}")
            self._set_stat_item(1, col_base + 1, f"{avg_chem:.6f}")
            self._set_stat_item(1, col_base + 2, f"{avg_d:.6f}")
            self._set_stat_item(1, col_base + 3, f"{avg_r:.1f}%")

            # 2: СКО
            self.stats_table.setItem(2, col_base, QTableWidgetItem("-"))
            self.stats_table.setItem(2, col_base + 1, QTableWidgetItem("-"))
            self._set_stat_item(2, col_base + 2, f"{std_d:.6f}")
            self._set_stat_item(2, col_base + 3, f"{std_r:.1f}%")

            # 3: Норматив
            self.stats_table.setItem(3, col_base, QTableWidgetItem("-"))
            self.stats_table.setItem(3, col_base + 1, QTableWidgetItem("-"))
            self._set_stat_item(3, col_base + 2, f"{norm_d1:.4f}" if norm_d1 > 0 else "-")
            self._set_stat_item(3, col_base + 3, f"{norm_d2:.0f}%" if norm_d2 > 0 else "-")

            # 4: Вывод
            if norm_d1 == 0 or len(deltas) < 2:
                stat_d, color_d = "-", default_bg
            else:
                ok_d = (std_d / norm_d1) < f_crit
                stat_d, color_d = ("Норма", light_green) if ok_d else ("Не норма", light_red)

            if norm_d2 == 0 or len(rels) < 2:
                stat_r, color_r = "-", default_bg
            else:
                ok_r = std_r <= norm_d2
                stat_r, color_r = ("Норма", light_green) if ok_r else ("Не норма", light_red)

            self.stats_table.setItem(4, col_base, QTableWidgetItem("-"))
            self.stats_table.setItem(4, col_base + 1, QTableWidgetItem("-"))

            it_d = QTableWidgetItem(stat_d);
            it_d.setBackground(color_d)
            it_d.setTextAlignment(Qt.AlignCenter)
            self.stats_table.setItem(4, col_base + 2, it_d)

            it_r = QTableWidgetItem(stat_r);
            it_r.setBackground(color_r)
            it_r.setTextAlignment(Qt.AlignCenter)
            self.stats_table.setItem(4, col_base + 3, it_r)

    def _set_stat_item(self, r, c, text):
        it = QTableWidgetItem(text)
        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.stats_table.setItem(r, c, it)

    # ================== ЭКСПОРТ ==================
    def export_to_file(self):
        if self.data_table.rowCount() == 0:
            QMessageBox.warning(self, "Пусто", "Нет данных для экспорта")
            return

        pr_name = self.product_combo.currentText().replace(':', '_').replace(' ', '_')
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить CSV", f"отчет_{pr_name}.csv", "CSV (*.csv)")
        if not path: return

        try:
            import csv
            with open(path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f, delimiter=';')

                dt_f = self.date_from.dateTime().toString("dd.MM.yyyy HH:mm")
                dt_t = self.date_to.dateTime().toString("dd.MM.yyyy HH:mm")
                writer.writerows([
                    ["Отчет по химическим содержаниям"],
                    [f"Продукт: {self.product_combo.currentText()}"],
                    [f"Период: с {dt_f} по {dt_t}"],
                    []
                ])

                # Заголовки: ряд с объединенными элементами и ряд с названиями столбцов
                row0 = [self.stats_table.item(0, c).text() if self.stats_table.item(0, c) else "" for c in
                        range(self.stats_table.columnCount())]
                headers = [self.stats_table.horizontalHeaderItem(c).text() for c in
                           range(self.stats_table.columnCount())]
                writer.writerow(row0)
                writer.writerow(headers)

                # Статистика
                for r in range(1, self.stats_table.rowCount()):
                    writer.writerow([self.stats_table.item(r, c).text() if self.stats_table.item(r, c) else "" for c in
                                     range(self.stats_table.columnCount())])

                writer.writerow([])

                # Данные
                writer.writerow(headers)
                for r in range(self.data_table.rowCount()):
                    writer.writerow([self.data_table.item(r, c).text() if self.data_table.item(r, c) else "" for c in
                                     range(self.data_table.columnCount())])

            QMessageBox.information(self, "Успех", "Отчет выгружен!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def showEvent(self, event):
        super().showEvent(event)
        self.configure_tables()
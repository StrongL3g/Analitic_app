# views/data/recalc.py
import json
import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QSplitter, QMessageBox, QHeaderView,
    QLineEdit, QFormLayout, QTabWidget
)
from PySide6.QtGui import QColor, QCursor
from PySide6.QtCore import Qt, QTimer
from database.db import Database
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from views.data.sample_dialog import SampleDialog
from utils.path_manager import get_config_path


def fmt_num(val):
    if val is None or val == "": return ""
    try:
        v = float(val)
        if v == 0.0: return "0.000"
        abs_v = abs(v)
        if abs_v < 0.001 or abs_v >= 100000:
            return f"{v:.3e}"
        else:
            return f"{v:.4f}"
    except (ValueError, TypeError):
        return str(val)


class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        def to_float(text):
            if not text: return None
            t = text.strip().replace(',', '.')
            if not t or t == "-": return None
            if t.endswith('%'): t = t[:-1]
            try:
                return float(t)
            except ValueError:
                return None

        v1, v2 = to_float(self.text()), to_float(other.text())
        if v1 is not None and v2 is not None: return v1 < v2
        if v1 is None and v2 is not None: return True
        if v1 is not None and v2 is None: return False
        return super().__lt__(other)


class RecalcPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.raw_buffer = []
        self.current_meas_type = 0
        self.y_vector_raw = np.array([])
        self._is_updating_ui = False

        self.init_ui()

        self.combo_element.currentIndexChanged.connect(self.load_data)
        self.combo_meas_type.currentIndexChanged.connect(self.load_data)
        self.combo_model.currentIndexChanged.connect(self.load_data)
        for combo in self.combo_equation_terms:
            combo.currentIndexChanged.connect(self.perform_recalc)

        self.norm_stdev_edit.textChanged.connect(self.perform_recalc)
        self.coeff_table.itemChanged.connect(self.on_coeff_changed)

        if self.combo_element.count() > 0:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Свободный пересчет (Имитация и анализ)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        main_splitter = QSplitter(Qt.Vertical)

        # === ВЕРХНЯЯ ЧАСТЬ ===
        top_widget = QWidget()
        top_layout = QHBoxLayout()

        # --- Левая верхняя ---
        left_top_group = QGroupBox("Параметры уравнения (Можно редактировать)")
        left_top_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        self.btn_change_selection = QPushButton("Изменить выборку")
        self.btn_load_db = QPushButton("Сбросить к данным из БД")
        self.btn_change_selection.clicked.connect(self.open_sample_dialog)
        self.btn_load_db.clicked.connect(self.load_data)
        btn_layout.addWidget(self.btn_change_selection)
        btn_layout.addWidget(self.btn_load_db)
        btn_layout.addStretch()
        left_top_layout.addLayout(btn_layout)

        self.coeff_table = QTableWidget(13, 3)
        self.coeff_table.setHorizontalHeaderLabels(["Параметр", "Множитель", "Значение"])
        self.coeff_table.verticalHeader().setVisible(False)
        self.coeff_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        labels = [f"A{i}" for i in range(11)] + ["K0 (Сдвиг)", "K1 (Масштаб)"]
        for row, name in enumerate(labels):
            item_name = QTableWidgetItem(name)
            item_name.setBackground(Qt.GlobalColor.lightGray)
            item_name.setFlags(item_name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.coeff_table.setItem(row, 0, item_name)

            item_term = QTableWidgetItem("-")
            item_term.setBackground(Qt.GlobalColor.lightGray)
            item_term.setFlags(item_term.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.coeff_table.setItem(row, 1, item_term)

            item_val = QTableWidgetItem("0.0")
            item_val.setBackground(QColor("#f0fdf4"))
            self.coeff_table.setItem(row, 2, item_val)
        left_top_layout.addWidget(self.coeff_table)

        norm_layout = QFormLayout()
        self.norm_stdev_edit = QLineEdit("0.1")
        self.norm_stdev_edit.setPlaceholderText("Введите норматив СКО...")
        norm_layout.addRow("Норматив СКО (для крит. Фишера):", self.norm_stdev_edit)
        left_top_layout.addLayout(norm_layout)
        left_top_group.setLayout(left_top_layout)

        # --- Центральная ---
        mid_top_group = QGroupBox("Статистика и Критерии")
        mid_top_layout = QVBoxLayout()
        self.stats_table = QTableWidget(11, 2)
        self.stats_table.setHorizontalHeaderLabels(["Показатель", "Значение / Статус"])
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        stat_labels = ["Среднее ΔC", "Отн. ΔC (%)", "СКО ΔC", "Отн. СКО ΔC (%)", "Смин", "Смакс", "Ссред",
                       "t-расч (Стьюдент)", "t-табл (Стьюдент)", "F-расч (Фишер)", "F-табл (Фишер)"]
        for row, label in enumerate(stat_labels):
            item = QTableWidgetItem(label)
            item.setBackground(Qt.GlobalColor.lightGray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.stats_table.setItem(row, 0, item)
            self.stats_table.setItem(row, 1, QTableWidgetItem("-"))
        mid_top_layout.addWidget(self.stats_table)
        mid_top_group.setLayout(mid_top_layout)

        # --- Правая ---
        right_top_group = QGroupBox("График (C_хим от C_расч)")
        right_top_layout = QVBoxLayout()
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect('button_press_event', self.on_plot_double_click)
        right_top_layout.addWidget(self.canvas)
        right_top_group.setLayout(right_top_layout)

        top_layout.addWidget(left_top_group, 30)
        top_layout.addWidget(mid_top_group, 30)
        top_layout.addWidget(right_top_group, 40)
        top_widget.setLayout(top_layout)

        # === НИЖНЯЯ ЧАСТЬ ===
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()

        combo_layout = QHBoxLayout()
        self.combo_element = QComboBox()
        self.combo_meas_type = QComboBox()
        self.combo_meas_type.addItems(["Все пробы", "Ручные", "Цикл"])
        self.combo_model = QComboBox()
        self.combo_model.addItems(["Модель 1", "Модель 2", "Модель 3"])

        combo_layout.addWidget(QLabel("Элемент:"))
        combo_layout.addWidget(self.combo_element)
        combo_layout.addWidget(QLabel("Пробы:"))
        combo_layout.addWidget(self.combo_meas_type)
        combo_layout.addWidget(QLabel("Модель:"))
        combo_layout.addWidget(self.combo_model)
        combo_layout.addStretch()
        bottom_layout.addLayout(combo_layout)

        terms_group = QGroupBox("Члены уравнения (A1 - A10)")
        terms_layout = QGridLayout()
        self.combo_equation_terms = []
        for i in range(10):
            combo = QComboBox()
            combo.setMinimumWidth(120)
            self.combo_equation_terms.append(combo)
            terms_layout.addWidget(QLabel(f"A{i + 1}:"), i // 5, (i % 5) * 2)
            terms_layout.addWidget(combo, i // 5, (i % 5) * 2 + 1)
        terms_group.setLayout(terms_layout)
        bottom_layout.addWidget(terms_group)

        # Вкладки таблиц
        bottom_layout.addWidget(QLabel("Таблицы выборки (Двойной клик на строку - исключить/вернуть):"))
        self.tabs = QTabWidget()
        self.table_active = self.create_data_table()
        self.table_excluded = self.create_data_table()
        self.tabs.addTab(self.table_active, "Рабочая выборка")
        self.tabs.addTab(self.table_excluded, "Исключенные строки")

        self.table_active.cellDoubleClicked.connect(lambda r, c: self.on_table_double_click(r, self.table_active))
        self.table_excluded.cellDoubleClicked.connect(lambda r, c: self.on_table_double_click(r, self.table_excluded))

        bottom_layout.addWidget(self.tabs)
        bottom_widget.setLayout(bottom_layout)
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([450, 350])
        layout.addWidget(main_splitter)
        self.setLayout(layout)

        self.ini_load_elements()

    def create_data_table(self):
        table = QTableWidget()
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        return table

    def on_coeff_changed(self, item):
        if not self._is_updating_ui and item.column() == 2:
            self.perform_recalc()

    def _create_readonly_item(self, text, is_numeric=False):
        item = NumericItem(text) if is_numeric else QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        return item

    def on_table_double_click(self, row, table_widget):
        pr_item = table_widget.item(row, 0)
        if not pr_item: return
        buffer_idx = pr_item.data(Qt.UserRole)
        if buffer_idx is not None and 0 <= buffer_idx < len(self.raw_buffer):
            self.raw_buffer[buffer_idx]['is_active'] = not self.raw_buffer[buffer_idx]['is_active']
            QTimer.singleShot(0, self.perform_recalc)

    def on_plot_double_click(self, event):
        if not event.dblclick or event.inaxes != self.ax: return
        x, y = event.xdata, event.ydata
        if x is None or y is None: return

        min_dist = float('inf')
        closest_idx = -1
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
        x_range, y_range = xlim[1] - xlim[0], ylim[1] - ylim[0]
        if x_range == 0 or y_range == 0: return

        el_nmb = self.combo_element.currentData()
        chem_col = f"c_chem_{el_nmb:02d}"

        for i, rec in enumerate(self.raw_buffer):
            cx = rec.get('c_calc', None)
            cy = rec.get(chem_col, None)
            if cx is not None and cy is not None:
                dist = ((cx - x) / x_range) ** 2 + ((cy - y) / y_range) ** 2
                if dist < min_dist:
                    min_dist, closest_idx = dist, i

        if closest_idx != -1 and min_dist < 0.002:
            self.raw_buffer[closest_idx]['is_active'] = not self.raw_buffer[closest_idx]['is_active']
            QTimer.singleShot(0, self.perform_recalc)

    def ini_load_elements(self):
        try:
            elements_path = get_config_path() / "elements.json"
            if os.path.exists(elements_path):
                with open(elements_path, "r", encoding="utf-8") as f:
                    elements_data = json.load(f)
                valid_elements = [elem for elem in elements_data if elem.get("name") != "-"]
                self.combo_element.clear()
                for elem in valid_elements:
                    self.combo_element.addItem(elem["name"], elem["number"])
        except Exception as e:
            print(f"Ошибка загрузки элементов: {e}")

    def open_sample_dialog(self):
        dialog = SampleDialog(self.db, self)
        if dialog.exec(): self.load_data()

    def load_data(self):
        try:
            el_nmb = self.combo_element.currentData()
            if el_nmb is None: return

            sample_path = get_config_path() / "sample" / "s_regress.json"
            if not os.path.exists(sample_path): return
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_config = json.load(f)
            if not sample_config: return

            pr_nmb = sample_config[0].get("product_id")
            if not pr_nmb or pr_nmb <= 0:
                for t in [self.table_active, self.table_excluded]: t.setRowCount(0)
                return

            mdl_nmb = self.combo_model.currentIndex() + 1
            el_set_row = self.db.fetch_one("SELECT * FROM el_set WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?",
                                           [pr_nmb, el_nmb, mdl_nmb])
            if not el_set_row: return

            self.current_meas_type = el_set_row["meas_type"]
            self._load_equation_terms(self.current_meas_type, el_nmb)
            self._load_coeffs_to_table(el_set_row, self.current_meas_type)

            self.raw_buffer = self._fetch_meas_data(sample_config, el_nmb, mdl_nmb, self.current_meas_type)
            self.perform_recalc()

        except Exception as e:
            print(f"Ошибка загрузки: {e}")

    def _load_equation_terms(self, meas_type, el_nmb):
        try:
            json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
            json_path = get_config_path() / json_file
            terms_list = []
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if meas_type == 0:
                    terms_list = [t["description"] for t in data.get("interactions", []) if t.get("description")]
                else:
                    for group in data.get("interactions", []):
                        if group.get("element_original_number") == el_nmb:
                            terms_list = [t["description"] for t in group.get("interactions", []) if
                                          t.get("description")]
                            break

            for combo in self.combo_equation_terms:
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("")
                combo.addItems(terms_list)
                combo.blockSignals(False)
        except Exception as e:
            print(f"Ошибка _load_equation_terms: {e}")

    def _load_coeffs_to_table(self, el_set_row, meas_type):
        self._is_updating_ui = True
        prefix_k = "k_i_alin" if meas_type == 0 else "k_c_alin"
        prefix_klin = "k_i_klin" if meas_type == 0 else "k_c_klin"
        op_prefix = "operand_i_" if meas_type == 0 else "operand_c_"
        op_type = "operator_i_" if meas_type == 0 else "operator_c_"

        json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
        term_lookup = {}
        json_path = get_config_path() / json_file
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            if meas_type == 0:
                for term in json_data.get("interactions", []):
                    if term.get("description", "").strip(): term_lookup[(term["x1"], term["x2"], term["op"])] = term[
                        "description"].strip()
            else:
                el_nmb = self.combo_element.currentData()
                for group in json_data.get("interactions", []):
                    if group.get("element_original_number") == el_nmb:
                        for term in group.get("interactions", []):
                            if term.get("description", "").strip(): term_lookup[(term["x1"], term["x2"], term["op"])] = \
                            term["description"].strip()
                        break

        a0 = el_set_row.get(f"{prefix_k}00", 0.0)
        self.coeff_table.item(0, 2).setText(f"{a0:.6g}")
        self.coeff_table.item(0, 1).setText("-")

        for i in range(1, 6):
            coeff = el_set_row.get(f"{prefix_k}0{i}", 0.0)
            x1 = el_set_row.get(f"{op_prefix}01_0{i}", 0)
            x2 = el_set_row.get(f"{op_prefix}02_0{i}", 0)
            op = el_set_row.get(f"{op_type}0{i}", 0)
            term_desc = term_lookup.get((x1, x2, op), "-")

            self.coeff_table.item(i, 2).setText(f"{coeff:.6g}")
            self.coeff_table.item(i, 1).setText(term_desc)
            combo = self.combo_equation_terms[i - 1]
            combo.blockSignals(True)
            idx = combo.findText(term_desc) if term_desc != "-" else 0
            combo.setCurrentIndex(idx if idx >= 0 else 0)
            combo.blockSignals(False)

        for i in range(6, 11):
            self.coeff_table.item(i, 2).setText("0.0")
            self.coeff_table.item(i, 1).setText("-")
            combo = self.combo_equation_terms[i - 1]
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

        k0 = el_set_row.get(f"{prefix_klin}00", 0.0)
        k1 = el_set_row.get(f"{prefix_klin}01", 1.0)
        self.coeff_table.item(11, 2).setText(f"{k0:.6g}")
        self.coeff_table.item(12, 2).setText(f"{k1:.6g}")
        self._is_updating_ui = False

    def _fetch_meas_data(self, sample_config, el_nmb, mdl_nmb, meas_type):
        all_rows = []
        for cond in sample_config:
            pr_nmb = cond["product_id"]
            if pr_nmb <= 0: continue

            d_from = cond['date_from'].replace('-', '')
            d_to = cond['date_to'].replace('-', '')
            start_dt = f"{d_from} {cond['time_from']}"
            end_dt = f"{d_to} {cond['time_to']}"

            cols = ["pr_nmb", "timestamp"]
            if meas_type == 0:
                cols.extend([f"i_00_{i:02d}" for i in range(20)])
            else:
                cols.extend([f"c_cor_{i:02d}" for i in range(1, 9)])
            chem_col = f"c_chem_{el_nmb:02d}"
            cols.append(chem_col)

            # Изменили mdl_nmb = ? на active_model = 1 для соответствия структуре PR_MEAS
            query = f"""
                SELECT {', '.join(cols)}
                FROM PR_MEAS
                WHERE timestamp BETWEEN ? AND ?
                AND pr_nmb = ? AND {chem_col} <> 0 AND active_model = 1
            """
            meas_index = self.combo_meas_type.currentIndex()
            if meas_index == 1:
                query += " AND meas_type = 0"
            elif meas_index == 2:
                query += " AND meas_type = 1"
            query += " ORDER BY timestamp DESC"

            try:
                rows = self.db.fetch_all(query, [start_dt, end_dt, pr_nmb])
                for r in rows:
                    r['is_active'] = True
                    ts = r.get("timestamp")
                    r['timestamp_str'] = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, 'strftime') else str(ts or "")
                    r['raw_db_row'] = r
                all_rows.extend(rows)
            except Exception as e:
                print(f"Ошибка запроса выборки в свободном пересчете: {e}")
        return all_rows

    def perform_recalc(self, *args):  # <--- Добавили *args, чтобы принимать любые сигналы от Qt
        if not hasattr(self, 'raw_buffer') or not self.raw_buffer:
            return
        try:
            coeffs = []
            for i in range(11):
                try:
                    coeffs.append(float(self.coeff_table.item(i, 2).text().replace(',', '.')))
                except ValueError:
                    coeffs.append(0.0)
            try:
                k0 = float(self.coeff_table.item(11, 2).text().replace(',', '.'))
            except ValueError:
                k0 = 0.0
            try:
                k1 = float(self.coeff_table.item(12, 2).text().replace(',', '.'))
            except ValueError:
                k1 = 1.0

            self._is_updating_ui = True
            el_nmb = self.combo_element.currentData()
            features = []
            for i, combo in enumerate(self.combo_equation_terms):
                desc = combo.currentText().strip()
                self.coeff_table.item(i + 1, 1).setText(desc if desc else "-")
                feat_vals = self._compute_feature(desc, self.current_meas_type, el_nmb)
                features.append(feat_vals)
            self._is_updating_ui = False

            c_chem_active, c_calc_active, dc_active = [], [], []

            for row_idx, rec in enumerate(self.raw_buffer):
                c_chem = rec.get(f"c_chem_{el_nmb:02d}", 0.0)
                c_raw = coeffs[0] + sum(coeffs[i + 1] * features[i][row_idx] for i in range(10))
                c_calc = k0 + k1 * c_raw
                rec['c_calc'] = c_calc
                rec['dc'] = c_calc - c_chem
                rec['ddc'] = abs(rec['dc']) / c_chem if c_chem != 0 else 0.0

                if rec.get('is_active', True):
                    c_chem_active.append(c_chem)
                    c_calc_active.append(c_calc)
                    dc_active.append(rec['dc'])

            self._update_statistics(c_chem_active, c_calc_active, dc_active)
            self._rebuild_tables_ui()
            self._update_plot()
        except Exception as e:
            print(f"Ошибка в perform_recalc(): {e}")

    def _rebuild_tables_ui(self):
        for t in [self.table_active, self.table_excluded]:
            t.blockSignals(True)
            t.setUpdatesEnabled(False)
            t.setSortingEnabled(False)
            t.clear()

        headers = ["Продукт", "Время (ts)", "C_хим", "C_расч", "ΔC", "δC=|ΔC/C_хим|"]
        if self.current_meas_type == 0:
            headers.extend([f"I_{i:02d}" for i in range(20)])
        else:
            headers.extend([f"C_{i:02d}" for i in range(1, 9)])

        for t in [self.table_active, self.table_excluded]:
            t.setColumnCount(len(headers))
            t.setHorizontalHeaderLabels(headers)

        active_count = sum(1 for r in self.raw_buffer if r['is_active'])
        excl_count = len(self.raw_buffer) - active_count

        self.table_active.setRowCount(active_count)
        self.table_excluded.setRowCount(excl_count)

        self.tabs.setTabText(0, f"Рабочая выборка ({active_count})")
        self.tabs.setTabText(1, f"Исключенные строки ({excl_count})")

        act_idx, exc_idx = 0, 0
        el_nmb = self.combo_element.currentData()
        chem_col = f"c_chem_{el_nmb:02d}"

        for buf_idx, rec in enumerate(self.raw_buffer):
            is_act = rec['is_active']
            t_widget = self.table_active if is_act else self.table_excluded
            row_idx = act_idx if is_act else exc_idx

            item_pr = QTableWidgetItem(str(rec.get("pr_nmb", "")))
            item_pr.setData(Qt.UserRole, buf_idx)
            item_pr.setFlags(item_pr.flags() & ~Qt.ItemFlag.ItemIsEditable)
            t_widget.setItem(row_idx, 0, item_pr)

            t_widget.setItem(row_idx, 1, self._create_readonly_item(rec.get("timestamp_str", "")))

            c_chem = rec.get(chem_col, 0.0)
            c_calc = rec.get("c_calc", 0.0)
            dc = rec.get("dc", 0.0)
            ddc = rec.get("ddc", 0.0)

            t_widget.setItem(row_idx, 2, self._create_readonly_item(fmt_num(c_chem), True))
            t_widget.setItem(row_idx, 3, self._create_readonly_item(fmt_num(c_calc), True))
            t_widget.setItem(row_idx, 4, self._create_readonly_item(fmt_num(dc), True))
            t_widget.setItem(row_idx, 5, self._create_readonly_item(f"{ddc * 100:.2f}%", True))

            col_offset = 6
            if self.current_meas_type == 0:
                for i in range(20):
                    val = rec.get(f"i_00_{i:02d}", 0.0)
                    t_widget.setItem(row_idx, col_offset + i, self._create_readonly_item(fmt_num(val), True))
            else:
                for i in range(1, 9):
                    val = rec.get(f"c_cor_{i:02d}", 0.0)
                    t_widget.setItem(row_idx, col_offset + i - 1, self._create_readonly_item(fmt_num(val), True))

            if is_act:
                act_idx += 1
            else:
                exc_idx += 1

        for t in [self.table_active, self.table_excluded]:
            t.setSortingEnabled(True)
            t.setUpdatesEnabled(True)
            t.blockSignals(False)

    def _update_statistics(self, c_chem, c_calc, dc):
        m = len(dc)
        if m < 2:
            for row in range(11): self.stats_table.item(row, 1).setText("-")
            for row in range(7, 11): self.stats_table.item(row, 1).setBackground(Qt.GlobalColor.white)
            return

        max_val, min_val = np.max(c_chem), np.min(c_chem)
        mean_dc, stdev_dc = np.mean(dc), np.std(dc, ddof=1)
        rel_mean = (mean_dc * 2) / (max_val + min_val) if (max_val + min_val) != 0 else 0
        rel_stdev = (stdev_dc * 2) / (max_val + min_val) if (max_val + min_val) != 0 else 0

        x, y = np.array(c_chem), np.array(c_calc)
        sum_xy = np.sum((x - np.mean(x)) * (y - np.mean(y)))
        sum_x2 = np.sum((x - np.mean(x)) ** 2)
        sum_y2 = np.sum((y - np.mean(y)) ** 2)

        # Точная формула R² без потери точностей
        r2 = (sum_xy ** 2) / (sum_x2 * sum_y2) if (sum_x2 != 0 and sum_y2 != 0) else 0.0

        t_calc = (abs(mean_dc) * np.sqrt(m)) / stdev_dc if stdev_dc != 0 else 0
        try:
            import scipy.stats as stats
            t_table = stats.t.ppf(0.975, m - 1)
            has_scipy = True
        except ImportError:
            t_table, has_scipy = 0.0, False

        try:
            norm_stdev = float(self.norm_stdev_edit.text().replace(',', '.'))
        except ValueError:
            norm_stdev = 0.0

        if norm_stdev > 0:
            f_calc = (stdev_dc ** 2) / (norm_stdev ** 2)
            if has_scipy:
                try:
                    f_table = stats.f.ppf(0.95, m, m)
                except Exception as e:
                    print(f"Ошибка расчета критерия Фишера: {e}")
                    f_table = 0.0
            else:
                f_table = 0.0
        else:
            f_calc, f_table = 0.0, 0.0

        self.stats_table.item(0, 1).setText(f"{mean_dc:.4f}")
        self.stats_table.item(1, 1).setText(f"{rel_mean * 100:.2f}")
        self.stats_table.item(2, 1).setText(f"{stdev_dc:.4f}")
        self.stats_table.item(3, 1).setText(f"{rel_stdev * 100:.2f}")
        self.stats_table.item(4, 1).setText(f"{min_val:.2f}")
        self.stats_table.item(5, 1).setText(f"{max_val:.2f}")
        self.stats_table.item(6, 1).setText(f"{(max_val + min_val) / 2:.2f}")

        self.stats_table.item(7, 1).setText(f"{t_calc:.4f}")
        self.stats_table.item(8, 1).setText(f"{t_table:.4f} (" + ("Норма" if t_calc < t_table else "Сдвиг!") + ")")
        color_t = QColor("#dcfce7") if t_calc < t_table else QColor("#fee2e2")
        self.stats_table.item(7, 1).setBackground(color_t)
        self.stats_table.item(8, 1).setBackground(color_t)

        if norm_stdev > 0:
            self.stats_table.item(9, 1).setText(f"{f_calc:.4f}")
            self.stats_table.item(10, 1).setText(
                f"{f_table:.4f} (" + ("Норма" if f_calc < f_table else "Превышение!") + ")")
            color_f = QColor("#dcfce7") if f_calc < f_table else QColor("#fee2e2")
            self.stats_table.item(9, 1).setBackground(color_f)
            self.stats_table.item(10, 1).setBackground(color_f)
        else:
            self.stats_table.item(9, 1).setText("- (Укажите норматив)")
            self.stats_table.item(10, 1).setText("-")
            self.stats_table.item(9, 1).setBackground(Qt.GlobalColor.white)
            self.stats_table.item(10, 1).setBackground(Qt.GlobalColor.white)

    def _update_plot(self):
        try:
            self.ax.clear()
            cx_act, cy_act, cx_exc, cy_exc = [], [], [], []
            el_nmb = self.combo_element.currentData()
            chem_col = f"c_chem_{el_nmb:02d}"

            for rec in self.raw_buffer:
                c_calc = rec.get("c_calc")
                c_chem = rec.get(chem_col)
                if c_calc is not None and c_chem is not None and c_chem != 0:
                    if rec.get('is_active', True):
                        cx_act.append(c_calc)
                        cy_act.append(c_chem)
                    else:
                        cx_exc.append(c_calc)
                        cy_exc.append(c_chem)

            if cx_act and cy_act:
                self.ax.scatter(cx_act, cy_act, alpha=0.6, color='tab:blue', label='Участвуют')
                min_v, max_v = min(min(cx_act), min(cy_act)), max(max(cx_act), max(cy_act))
                self.ax.plot([min_v, max_v], [min_v, max_v], 'r--', label='Идеал', alpha=0.7)

            if cx_exc and cy_exc:
                self.ax.scatter(cx_exc, cy_exc, alpha=0.8, color='tab:red', marker='x', label='Исключены')

            if cx_act or cx_exc:
                self.ax.set_xlabel("C_расч")
                self.ax.set_ylabel("C_хим")
                self.ax.set_title("График зависимости C_хим от C_расч")
                self.ax.legend()
                self.ax.grid(True, alpha=0.3)
            self.canvas.draw()
        except Exception as e:
            print(f"Ошибка в _update_plot: {e}")

    def _compute_feature(self, feature_desc: str, meas_type: int, el_nmb: int) -> list:
        if not feature_desc or feature_desc == "-": return [0.0] * len(self.raw_buffer)
        json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
        json_path = get_config_path() / json_file
        if not os.path.exists(json_path): return [0.0] * len(self.raw_buffer)

        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)
        x1, x2, op, found = 0, 0, 0, False
        target_desc = feature_desc.strip()

        if meas_type == 0:
            for term in json_data.get("interactions", []):
                if term.get("description", "").strip() == target_desc:
                    x1, x2, op = term["x1"], term["x2"], term["op"]
                    found = True;
                    break
        else:
            for group in json_data.get("interactions", []):
                if group.get("element_original_number") == el_nmb:
                    for term in group.get("interactions", []):
                        if term.get("description", "").strip() == target_desc:
                            x1, x2, op = term["x1"], term["x2"], term["op"]
                            found = True;
                            break
                    if found: break

        if not found: return [0.0] * len(self.raw_buffer)

        result = []
        for rec in self.raw_buffer:
            try:
                db_row = rec["raw_db_row"]
                if meas_type == 0:
                    val1 = float(db_row.get(f"i_00_{x1:02d}") or 0.0)
                    val2 = float(db_row.get(f"i_00_{x2:02d}") or 0.0) if x2 != 0 else 1.0
                else:
                    val1 = float(db_row.get(f"c_cor_{x1:02d}") or 0.0) if x1 != 0 else 1.0
                    val2 = float(db_row.get(f"c_cor_{x2:02d}") or 0.0) if x2 != 0 else 1.0

                if op == 0:
                    res = 0.0
                elif op == 1:
                    res = val1
                elif op == 2:
                    res = val1 * val2
                elif op == 3:
                    res = val1 / val2 if val2 != 0 else 0.0
                elif op == 4:
                    res = val1 * val1
                elif op == 5:
                    res = 1.0 / val1 if val1 != 0 else 0.0
                elif op == 6:
                    res = val1 / (val2 * val2) if val2 != 0 else 0.0
                elif op == 7:
                    res = 1.0 / (val1 * val1) if val1 != 0 else 0.0
                else:
                    res = 0.0
                result.append(res)
            except:
                result.append(0.0)
        return result
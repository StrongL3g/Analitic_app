# views/data/regression.py
import json
import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QSplitter, QMessageBox,
    QDialog, QDialogButtonBox, QLineEdit, QFormLayout
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from database.db import Database
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from views.data.sample_dialog import SampleDialog
from utils.path_manager import get_config_path


# === НАДЕЖНЫЙ КЛАСС ДЛЯ ЧИСЛОВОЙ СОРТИРОВКИ ===
class NumericItem(QTableWidgetItem):
    def __lt__(self, other):
        def to_float(text):
            if not text:
                return None
            t = text.strip().replace(',', '.')
            if not t or t == "-":
                return None
            if t.endswith('%'):
                t = t[:-1]
            try:
                return float(t)
            except ValueError:
                return None

        v1 = to_float(self.text())
        v2 = to_float(other.text())

        if v1 is not None and v2 is not None:
            return v1 < v2
        if v1 is None and v2 is not None:
            return True
        if v1 is not None and v2 is None:
            return False
        return super().__lt__(other)


class RegressionPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_sample = []
        self.current_element = None
        self.current_meas_type = 0
        self.raw_buffer = []
        self.y_vector_raw = np.array([])

        self.init_ui()

        # Подключаем обработчики
        self.combo_element.currentIndexChanged.connect(self.load_data)
        self.combo_meas_type.currentIndexChanged.connect(self.load_data)
        for combo in self.combo_equation_terms:
            combo.currentIndexChanged.connect(self.perform_regression)

        # Загружаем данные при открытии страницы
        if self.combo_element.count() > 0:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Регрессионный анализ")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        main_splitter = QSplitter(Qt.Vertical)

        # === Верхняя часть ===
        top_widget = QWidget()
        top_layout = QHBoxLayout()

        # --- Левая верхняя (Таблицы) ---
        left_top_group = QGroupBox("Результаты и управление")
        left_top_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        self.btn_change_selection = QPushButton("Изменить выборку")
        self.btn_save_equation = QPushButton("Сохранить уравнение")
        self.btn_load_data = QPushButton("Выгрузка данных")

        self.btn_change_selection.clicked.connect(self.open_sample_dialog)
        self.btn_save_equation.clicked.connect(self.save_equation)
        self.btn_load_data.clicked.connect(self.load_data)

        btn_layout.addWidget(self.btn_change_selection)
        btn_layout.addWidget(self.btn_save_equation)
        btn_layout.addWidget(self.btn_load_data)
        btn_layout.addStretch()
        left_top_layout.addLayout(btn_layout)

        left_top_layout.addWidget(QLabel("Сводная таблица коэффициентов:"))
        self.coeff_table = QTableWidget(11, 4)
        self.coeff_table.setHorizontalHeaderLabels(["Коэффициент", "Множитель", "Значение", "Значимость"])
        self.coeff_table.verticalHeader().setVisible(False)
        for row in range(11):
            for col, default_val in enumerate([f"A{row}", "-", "0.0", "0.0"]):
                item = QTableWidgetItem(default_val)
                if col in (0, 1):
                    item.setBackground(Qt.GlobalColor.lightGray)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.coeff_table.setItem(row, col, item)
        left_top_layout.addWidget(self.coeff_table)

        left_top_layout.addWidget(QLabel("Характеристики уравнения:"))
        self.stats_table = QTableWidget(6, 2)
        self.stats_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        self.stats_table.verticalHeader().setVisible(False)
        for row, label in enumerate(["СКО σ", "Отн. СКО", "Смин", "Смакс", "Ссред", "Корреляция R²"]):
            item = QTableWidgetItem(label)
            item.setBackground(Qt.GlobalColor.lightGray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.stats_table.setItem(row, 0, item)
            self.stats_table.setItem(row, 1, QTableWidgetItem("0.0"))
        left_top_layout.addWidget(self.stats_table)
        left_top_group.setLayout(left_top_layout)

        # --- Верхняя правая (График) ---
        right_top_group = QGroupBox("График зависимости C_хим от C_расч")
        right_top_layout = QVBoxLayout()
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.canvas = FigureCanvas(self.fig)

        self.canvas.mpl_connect('button_press_event', self.on_plot_double_click)

        right_top_layout.addWidget(self.canvas)
        right_top_group.setLayout(right_top_layout)

        top_layout.addWidget(left_top_group, 40)
        top_layout.addWidget(right_top_group, 60)
        top_widget.setLayout(top_layout)

        # === Нижняя часть ===
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()

        combo_layout = QHBoxLayout()
        self.combo_element = QComboBox()
        self.combo_meas_type = QComboBox()
        self.combo_meas_type.addItems(["Все пробы", "Ручные", "Цикл"])
        combo_layout.addWidget(QLabel("Элемент:"))
        combo_layout.addWidget(self.combo_element)
        combo_layout.addWidget(QLabel("Пробы:"))
        combo_layout.addWidget(self.combo_meas_type)
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

        bottom_layout.addWidget(QLabel("Таблица выборки (Двойной клик исключает/возвращает строку):"))
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(16)
        self.data_table.setHorizontalHeaderLabels([
            "Продукт", "Дата/Время",
            "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10",
            "C_хим", "C_расч", "ΔC", "δC=|ΔC/C_хим|"
        ])
        self.data_table.cellDoubleClicked.connect(self.on_table_double_click)
        self.data_table.setSortingEnabled(True)
        bottom_layout.addWidget(self.data_table)

        bottom_widget.setLayout(bottom_layout)
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([400, 300])
        layout.addWidget(main_splitter)
        self.setLayout(layout)

        self.ini_load_elements()

    def on_table_double_click(self, row, col):
        pr_item = self.data_table.item(row, 0)
        dt_item = self.data_table.item(row, 1)
        if not pr_item or not dt_item: return

        for i, rec in enumerate(self.raw_buffer):
            if str(rec.get("pr_nmb", "")) == pr_item.text() and rec.get("meas_dt", "") == dt_item.text():
                self.toggle_row_state(i)
                break

    def on_plot_double_click(self, event):
        if not event.dblclick or event.inaxes != self.ax:
            return

        x, y = event.xdata, event.ydata
        if x is None or y is None: return

        min_dist = float('inf')
        closest_idx = -1

        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        if x_range == 0 or y_range == 0: return

        el_nmb = self.combo_element.currentData()
        chem_col = f"c_chem_{el_nmb:02d}"

        for i, rec in enumerate(self.raw_buffer):
            cx = rec.get(chem_col, 0)
            cy = rec.get('c_calc', None)
            if cx and cy is not None:
                dist = ((cx - x) / x_range) ** 2 + ((cy - y) / y_range) ** 2
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i

        if closest_idx != -1 and min_dist < 0.002:
            self.toggle_row_state(closest_idx)

    def toggle_row_state(self, idx):
        if idx < 0 or idx >= len(self.raw_buffer): return

        current_state = self.raw_buffer[idx].get('is_active', True)
        self.raw_buffer[idx]['is_active'] = not current_state
        self.raw_buffer.sort(key=lambda item: (not item.get('is_active', True), item.get('meas_dt', '')))

        el_nmb = self.combo_element.currentData()
        chem_col = f"c_chem_{el_nmb:02d}"
        self.y_vector_raw = np.array([rec.get(chem_col, 0.0) for rec in self.raw_buffer])

        self._update_data_table_from_buffer()
        self.perform_regression()

    def sort_data_table(self, logical_index):
        self.data_table.sortItems(logical_index, Qt.DescendingOrder)

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
        if dialog.exec():
            self.load_data()

    def load_data(self):
        try:
            sample_path = get_config_path() / "sample" / "s_regress.json"
            if not os.path.exists(sample_path):
                return

            with open(sample_path, "r", encoding="utf-8") as f:
                sample_config = json.load(f)

            if not sample_config:
                return

            pr_nmb = sample_config[0].get("product_id")
            el_nmb = self.combo_element.currentData()

            el_set_row = self.db.fetch_one("SELECT * FROM el_set WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = 1",
                                           [pr_nmb, el_nmb])
            if not el_set_row: return

            self.current_meas_type = el_set_row["meas_type"]
            self._load_equation_terms(self.current_meas_type, el_nmb)

            self.raw_buffer = self._fetch_pr_meas_data(sample_config, el_nmb, self.current_meas_type)

            if not self.raw_buffer:
                self.data_table.setRowCount(0)
                return

            chem_col = f"c_chem_{el_nmb:02d}"
            self.y_vector_raw = np.array([rec.get(chem_col, 0.0) for rec in self.raw_buffer])

            self._apply_initial_equation(el_set_row, self.current_meas_type)
            self._update_data_table_from_buffer()
            self.perform_regression()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки: {str(e)}")

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
            print(f"Ошибка в _load_equation_terms: {e}")

    def _fetch_pr_meas_data(self, sample_config, el_nmb, meas_type):
        all_rows = []
        for cond in sample_config:
            pr_nmb = cond["product_id"]
            start_dt = f"{cond['date_from']} {cond['time_from']}"
            end_dt = f"{cond['date_to']} {cond['time_to']}"

            cols = ["pr_nmb", "meas_dt"]
            if meas_type == 0:
                cols.extend([f"i_00_{i:02d}" for i in range(20)])
            else:
                cols.extend([f"c_cor_{i:02d}" for i in range(1, 9)])

            chem_col = f"c_chem_{el_nmb:02d}"
            cor_col = f"c_cor_{el_nmb:02d}"
            cols.extend([chem_col, cor_col])

            query = f"""
                SELECT {', '.join(cols)},
                    {cor_col} - {chem_col} AS dc,
                    CASE
                        WHEN {chem_col} <> 0 AND {chem_col} IS NOT NULL
                        THEN ABS({cor_col} - {chem_col}) / {chem_col}
                        ELSE 0
                    END AS ddc
                FROM PR_MEAS
                WHERE timestamp BETWEEN ? AND ?
                AND pr_nmb = ? AND {chem_col} <> 0 AND active_model = 1
            """

            meas_index = self.combo_meas_type.currentIndex()
            if meas_index == 1:
                query += " AND meas_type = 0"
            elif meas_index == 2:
                query += " AND meas_type = 1"
            query += " ORDER BY meas_dt, timestamp"

            try:
                rows = self.db.fetch_all(query, [start_dt, end_dt, pr_nmb])
                for r in rows: r['is_active'] = True
                all_rows.extend(rows)
            except Exception as e:
                print(f"Ошибка запроса: {e}")
        return all_rows

    def _apply_initial_equation(self, el_set_row, meas_type):
        try:
            k_prefix = "k_i_" if meas_type == 0 else "k_c_"
            op_prefix = "operand_i_" if meas_type == 0 else "operand_c_"
            op_type = "operator_i_" if meas_type == 0 else "operator_c_"

            json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
            json_path = get_config_path() / json_file
            if not os.path.exists(json_path): return

            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            term_lookup = {}
            if meas_type == 0:
                for term in json_data.get("interactions", []):
                    if term.get("description", "").strip():
                        term_lookup[(term["x1"], term["x2"], term["op"])] = term["description"].strip()
            else:
                el_nmb = self.combo_element.currentData()
                for group in json_data.get("interactions", []):
                    if group.get("element_original_number") == el_nmb:
                        for term in group.get("interactions", []):
                            if term.get("description", "").strip():
                                term_lookup[(term["x1"], term["x2"], term["op"])] = term["description"].strip()
                        break

            term_specs = [
                (f"{op_prefix}01_01", f"{op_prefix}02_01", f"{op_type}01"),
                (f"{op_prefix}01_02", f"{op_prefix}02_02", f"{op_type}02"),
                (f"{op_prefix}01_03", f"{op_prefix}02_03", f"{op_type}03"),
                (f"{op_prefix}01_04", f"{op_prefix}02_04", f"{op_type}04"),
                (f"{op_prefix}01_05", f"{op_prefix}02_05", f"{op_type}05"),
            ]

            found_terms = []
            for x1_key, x2_key, op_key in term_specs:
                x1 = el_set_row.get(x1_key, 0)
                x2 = el_set_row.get(x2_key, 0)
                op = el_set_row.get(op_key, 0)
                found_terms.append(term_lookup.get((x1, x2, op), "-"))

            for i, combo in enumerate(self.combo_equation_terms):
                combo.blockSignals(True)
                if i < len(found_terms) and found_terms[i] != "-":
                    idx = combo.findText(found_terms[i])
                    combo.setCurrentIndex(idx if idx >= 0 else 0)
                else:
                    combo.setCurrentIndex(0)
                combo.blockSignals(False)
        except Exception as e:
            print(f"Ошибка _apply_initial_equation: {e}")

    def _update_data_table_from_buffer(self):
        self.data_table.blockSignals(True)
        self.data_table.setSortingEnabled(False)
        self.data_table.setRowCount(0)

        if not self.raw_buffer:
            self.data_table.blockSignals(False)
            self.data_table.setSortingEnabled(True)
            return

        self.data_table.setRowCount(len(self.raw_buffer))
        el_nmb = self.combo_element.currentData()
        chem_col = f"c_chem_{el_nmb:02d}"

        for row_idx, rec in enumerate(self.raw_buffer):
            is_active = rec.get('is_active', True)
            bg_color = QColor("#ffffff") if is_active else QColor("#ffcccc")

            def set_text_item(col, val):
                item = QTableWidgetItem(str(val))
                item.setBackground(bg_color)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.data_table.setItem(row_idx, col, item)

            def set_num_item(col, val_str):
                item = NumericItem(val_str)
                item.setBackground(bg_color)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.data_table.setItem(row_idx, col, item)

            set_text_item(0, rec.get("pr_nmb", ""))
            set_text_item(1, rec.get("meas_dt", ""))

            c_chem_raw = rec.get(chem_col, "")
            try:
                c_chem_str = f"{float(c_chem_raw):.3f}" if c_chem_raw != "" else ""
            except ValueError:
                c_chem_str = str(c_chem_raw)

            set_num_item(12, c_chem_str)
            for col in (13, 14, 15): set_num_item(col, "")

        self.data_table.blockSignals(False)
        self.data_table.setSortingEnabled(True)

    def perform_regression(self):
        if not hasattr(self, 'raw_buffer') or not self.raw_buffer: return

        try:
            X_active, y_vector, active_indices = self._build_regression_data()
            if X_active is None or X_active.shape[0] < X_active.shape[1]:
                self.apply_current_equation(fallback_zeros=True)
                self._update_plot(self.y_vector_raw)
                return

            coeffs_active, stats, std_errs, t_stats_active, p_vals_active = self._calculate_regression(X_active,
                                                                                                       y_vector)

            full_coeffs = np.zeros(11)
            full_t_stats = np.zeros(11)

            full_coeffs[0] = coeffs_active[0]
            full_t_stats[0] = np.abs(t_stats_active[0])

            for i, original_index in enumerate(active_indices):
                full_coeffs[original_index] = coeffs_active[i + 1]
                full_t_stats[original_index] = np.abs(t_stats_active[i + 1])

            self._update_coefficients_table(full_coeffs, full_t_stats)
            self.apply_current_equation()
            self._update_statistics_table(stats, y_vector)
            self._update_plot(y_vector)

        except Exception as e:
            print(f"Ошибка в perform_regression: {e}")

    def _build_regression_data(self):
        try:
            active_mask = np.array([rec.get('is_active', True) for rec in self.raw_buffer])
            valid_mask = (self.y_vector_raw != 0) & active_mask
            y_vector = self.y_vector_raw[valid_mask]

            features = []
            active_indices = []

            for i, combo in enumerate(self.combo_equation_terms):
                term_desc = combo.currentText().strip()
                if term_desc and term_desc != "-":
                    feat_vals = self._compute_feature(term_desc, self.current_meas_type,
                                                      self.combo_element.currentData())
                    features.append(np.array(feat_vals)[valid_mask])
                    active_indices.append(i + 1)

            if len(y_vector) == 0: return None, None, None

            X_matrix = np.ones((len(y_vector), len(features) + 1))
            for col_idx, feat_vals in enumerate(features):
                X_matrix[:, col_idx + 1] = feat_vals

            return X_matrix, y_vector, active_indices
        except Exception as e:
            print(f"Ошибка построения матрицы: {e}")
            return None, None, None

    def _calculate_regression(self, X, y):
        try:
            n_samples, n_features = X.shape
            dof = max(n_samples - n_features, 1)

            XTX_pinv = np.linalg.pinv(X.T @ X)
            coeffs = XTX_pinv @ X.T @ y

            y_pred = X @ coeffs
            residuals = y - y_pred
            mse = np.sum(residuals ** 2) / dof
            std_errs = np.sqrt(np.abs(np.diag(XTX_pinv)) * mse)

            with np.errstate(divide='ignore', invalid='ignore'):
                t_stats = np.where(std_errs != 0, coeffs / std_errs, 0)

            try:
                from scipy import stats
                p_vals = 2 * (1 - stats.t.cdf(np.abs(t_stats), dof))
            except ImportError:
                p_vals = np.zeros(n_features)

            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_sq = 1 - (np.sum(residuals ** 2) / ss_tot) if ss_tot != 0 else 0

            stats_dict = {'r_squared': r_sq}
            return coeffs, stats_dict, std_errs, t_stats, p_vals
        except Exception as e:
            print(f"Ошибка в _calculate_regression: {e}")
            return np.zeros(X.shape[1]), {}, np.zeros(X.shape[1]), np.zeros(X.shape[1]), np.ones(X.shape[1])

    def _update_coefficients_table(self, coefficients, t_stats):
        a0_item = self.coeff_table.item(0, 1)
        if a0_item: a0_item.setText("-")

        for i in range(1, 11):
            combo = self.combo_equation_terms[i - 1]
            term_desc = combo.currentText().strip()
            multiplier_item = self.coeff_table.item(i, 1)
            if multiplier_item:
                multiplier_item.setText(term_desc if term_desc else "-")

            header_item = self.data_table.horizontalHeaderItem(1 + i)
            if header_item:
                header_item.setToolTip(term_desc if term_desc else f"A{i} (не выбран)")

        from PySide6.QtGui import QColor

        for i, (coeff, t_stat) in enumerate(zip(coefficients, t_stats)):
            value_item = self.coeff_table.item(i, 2)
            if value_item: value_item.setText(f"{coeff:.6g}")

            significance_item = self.coeff_table.item(i, 3)
            if significance_item:
                if coeff == 0.0 and i > 0 and self.combo_equation_terms[i - 1].currentText().strip() == "":
                    significance_item.setText("-")
                    significance_item.setBackground(Qt.GlobalColor.white)
                else:
                    significance_item.setText(f"{t_stat:.2f}")
                    if t_stat >= 3.0:
                        significance_item.setBackground(Qt.GlobalColor.white)
                    elif t_stat >= 1.0:
                        significance_item.setBackground(QColor("#FFE4B5"))
                    else:
                        significance_item.setBackground(QColor("#FFCCCC"))

    def _update_statistics_table(self, statistics=None, y_vector=None):
        if statistics is None: statistics = {}
        c_chem, c_calc, dc = [], [], []

        for row in range(self.data_table.rowCount()):
            # Проверяем UI строки, чтобы не брать красные
            chem_item = self.data_table.item(row, 12)
            if chem_item and chem_item.background().color().name() == "#ffcccc":
                continue

            try:
                chem_val = self.data_table.item(row, 12).text()
                calc_val = self.data_table.item(row, 13).text()
                if chem_val and calc_val:
                    c_val = float(chem_val)
                    calc = float(calc_val)
                    c_chem.append(c_val)
                    c_calc.append(calc)
                    dc.append(calc - c_val)
            except:
                continue

        if not c_chem:
            for r in range(6): self.stats_table.item(r, 1).setText("0.0")
            return

        max_val, min_val = np.max(c_chem), np.min(c_chem)
        stdev_dc = np.std(dc, ddof=1) if len(dc) > 1 else 0.0

        arrParam = [0.0] * 7
        arrParam[1] = stdev_dc
        arrParam[2] = (stdev_dc * 2) / (max_val + min_val) if (max_val + min_val) != 0 else 0
        arrParam[3] = min_val
        arrParam[4] = max_val
        arrParam[5] = (max_val + min_val) / 2

        x, y = np.array(c_chem), np.array(c_calc)
        sum_xy = np.sum((x - np.mean(x)) * (y - np.mean(y)))
        sum_x2 = np.sum((x - np.mean(x)) ** 2)
        sum_y2 = np.sum((y - np.mean(y)) ** 2)
        arrParam[6] = ((sum_xy ** 2) / sum_x2) / sum_y2 if (sum_x2 != 0 and sum_y2 != 0) else 0

        formats = [
            f"{arrParam[1]:.4f}",
            f"{arrParam[2] * 100:.2f}%",
            f"{arrParam[3]:.2f}",
            f"{arrParam[4]:.2f}",
            f"{arrParam[5]:.2f}",
            f"{arrParam[6]:.2f}"
        ]

        for row, formatted_val in enumerate(formats):
            item = self.stats_table.item(row, 1)
            if item: item.setText(formatted_val)

    def _update_plot(self, y_vector):
        try:
            self.ax.clear()
            c_chem_act, c_calc_act = [], []
            c_chem_exc, c_calc_exc = [], []

            for row in range(self.data_table.rowCount()):
                chem_item = self.data_table.item(row, 12)
                calc_item = self.data_table.item(row, 13)

                if chem_item and calc_item and chem_item.text() and calc_item.text():
                    try:
                        cv = float(chem_item.text())
                        ca = float(calc_item.text())
                        if chem_item.background().color().name() != "#ffcccc":
                            c_chem_act.append(cv)
                            c_calc_act.append(ca)
                        else:
                            c_chem_exc.append(cv)
                            c_calc_exc.append(ca)
                    except ValueError:
                        pass

            if c_chem_act and c_calc_act:
                self.ax.scatter(c_chem_act, c_calc_act, alpha=0.6, color='tab:blue', label='Участвуют')
                min_val = min(min(c_chem_act), min(c_calc_act))
                max_val = max(max(c_chem_act), max(c_calc_act))
                self.ax.plot([min_val, max_val], [min_val, max_val], 'r--', label='Идеал', alpha=0.7)

            if c_chem_exc and c_calc_exc:
                self.ax.scatter(c_chem_exc, c_calc_exc, alpha=0.8, color='tab:red', marker='x', label='Исключены')

            if c_chem_act or c_chem_exc:
                self.ax.set_xlabel("C_хим")
                self.ax.set_ylabel("C_расч")
                self.ax.set_title("График зависимости C_хим от C_расч")
                self.ax.legend()
                self.ax.grid(True, alpha=0.3)

            self.canvas.draw()
        except Exception as e:
            print(f"Ошибка в _update_plot: {e}")

    def apply_current_equation(self, fallback_zeros=False):
        try:
            if not hasattr(self, 'raw_buffer') or not self.raw_buffer: return

            coeffs = []
            if not fallback_zeros:
                for i in range(11):
                    item = self.coeff_table.item(i, 2)
                    try:
                        coeffs.append(float(item.text()) if item and item.text() else 0.0)
                    except:
                        coeffs.append(0.0)
            else:
                coeffs = [0.0] * 11

            el_nmb = self.combo_element.currentData()
            features = []

            self.data_table.setSortingEnabled(False)

            for i, combo in enumerate(self.combo_equation_terms):
                desc = combo.currentText().strip()
                feat_vals = self._compute_feature(desc, self.current_meas_type, el_nmb)
                features.append(feat_vals)
                self._fill_feature_column(i, feat_vals)

            for row_idx in range(len(self.raw_buffer)):
                c_chem = self.raw_buffer[row_idx].get(f"c_chem_{el_nmb:02d}", 0.0)
                X_row = [1.0] + [features[i][row_idx] for i in range(10)]

                c_calc = sum(coeffs[i] * X_row[i] for i in range(11))
                self.raw_buffer[row_idx]['c_calc'] = c_calc

                dC = c_calc - c_chem
                ddc = abs(dC) / c_chem if c_chem != 0 else 0.0

                is_active = self.raw_buffer[row_idx].get('is_active', True)
                bg_color = QColor("#ffffff") if is_active else QColor("#ffcccc")

                def set_calc_item(col, val_str):
                    item = NumericItem(val_str)
                    item.setBackground(bg_color)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    pr_val = str(self.raw_buffer[row_idx].get("pr_nmb", ""))
                    dt_val = self.raw_buffer[row_idx].get("meas_dt", "")

                    for ui_row in range(self.data_table.rowCount()):
                        if self.data_table.item(ui_row, 0).text() == pr_val and self.data_table.item(ui_row,
                                                                                                     1).text() == dt_val:
                            self.data_table.setItem(ui_row, col, item)
                            break

                set_calc_item(13, f"{c_calc:.3f}")
                set_calc_item(14, f"{dC:.3f}")
                set_calc_item(15, f"{ddc * 100:.2f}%")

            self.data_table.setSortingEnabled(True)

        except Exception as e:
            print(f"Ошибка в apply_current_equation(): {e}")

    def _compute_feature(self, feature_desc: str, meas_type: int, el_nmb: int) -> list:
        if not feature_desc or feature_desc == "-": return [0.0] * len(self.raw_buffer)
        json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
        json_path = get_config_path() / json_file
        if not os.path.exists(json_path): return [0.0] * len(self.raw_buffer)

        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        x1, x2, op = 0, 0, 0
        found = False
        if meas_type == 0:
            for term in json_data.get("interactions", []):
                if term.get("description") == feature_desc:
                    x1, x2, op = term["x1"], term["x2"], term["op"]
                    found = True;
                    break
        else:
            for group in json_data.get("interactions", []):
                if group.get("element_original_number") == el_nmb:
                    for term in group.get("interactions", []):
                        if term.get("description") == feature_desc:
                            x1, x2, op = term["x1"], term["x2"], term["op"]
                            found = True;
                            break
                    if found: break

        if not found: return [0.0] * len(self.raw_buffer)

        result = []
        for rec in self.raw_buffer:
            try:
                if meas_type == 0:
                    val1 = rec.get(f"i_00_{x1:02d}", 0.0)
                    val2 = rec.get(f"i_00_{x2:02d}", 0.0) if x2 != 0 else 1.0
                else:
                    val1 = rec.get(f"c_cor_{x1:02d}", 0.0) if x1 != 0 else 1.0
                    val2 = rec.get(f"c_cor_{x2:02d}", 0.0) if x2 != 0 else 1.0

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

    def _fill_feature_column(self, col_index: int, values: list):
        if 0 <= col_index <= 9:
            for row_idx, val in enumerate(values):
                is_active = self.raw_buffer[row_idx].get('is_active', True)
                item = NumericItem(f"{val:.3f}")
                item.setBackground(QColor("#ffffff") if is_active else QColor("#ffcccc"))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                pr_val = str(self.raw_buffer[row_idx].get("pr_nmb", ""))
                dt_val = self.raw_buffer[row_idx].get("meas_dt", "")

                for ui_row in range(self.data_table.rowCount()):
                    if self.data_table.item(ui_row, 0).text() == pr_val and self.data_table.item(ui_row,
                                                                                                 1).text() == dt_val:
                        self.data_table.setItem(ui_row, 2 + col_index, item)
                        break

    def save_equation(self):
        try:
            if not hasattr(self, 'raw_buffer') or not self.raw_buffer:
                QMessageBox.warning(self, "Внимание", "Нет данных для сохранения. Сначала загрузите выборку.")
                return

            sample_path = get_config_path() / "sample" / "s_regress.json"
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_config = json.load(f)

            default_pr_nmb = sample_config[0].get("product_id", 1)
            el_nmb = self.combo_element.currentData()
            meas_type = self.current_meas_type

            dialog = SaveEquationDialog(default_pr=default_pr_nmb, default_mdl="1", parent=self)
            if not dialog.exec():
                return

            try:
                target_products, target_models = dialog.get_data()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка ввода", str(e))
                return

            coeffs = []
            for i in range(11):
                item = self.coeff_table.item(i, 2)
                try:
                    coeffs.append(float(item.text().replace(',', '.')) if item and item.text() else 0.0)
                except:
                    coeffs.append(0.0)

            terms = []
            json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
            json_path = get_config_path() / json_file

            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            for combo in self.combo_equation_terms:
                desc = combo.currentText().strip()
                x1, x2, op = 0, 0, 0
                if desc and desc != "-":
                    if meas_type == 0:
                        for term in json_data.get("interactions", []):
                            if term.get("description") == desc:
                                x1, x2, op = term["x1"], term["x2"], term["op"]
                                break
                    else:
                        for group in json_data.get("interactions", []):
                            if group.get("element_original_number") == el_nmb:
                                for term in group.get("interactions", []):
                                    if term.get("description") == desc:
                                        x1, x2, op = term["x1"], term["x2"], term["op"]
                                        break
                                break
                terms.append((x1, x2, op))

            prefix_k = "k_i_alin" if meas_type == 0 else "k_c_alin"
            prefix_op = "i" if meas_type == 0 else "c"

            update_fields = [
                f"{prefix_k}00 = ?",
                f"{prefix_k}01 = ?", f"operand_{prefix_op}_01_01 = ?", f"operand_{prefix_op}_02_01 = ?",
                f"operator_{prefix_op}_01 = ?",
                f"{prefix_k}02 = ?", f"operand_{prefix_op}_01_02 = ?", f"operand_{prefix_op}_02_02 = ?",
                f"operator_{prefix_op}_02 = ?",
                f"{prefix_k}03 = ?", f"operand_{prefix_op}_01_03 = ?", f"operand_{prefix_op}_02_03 = ?",
                f"operator_{prefix_op}_03 = ?",
                f"{prefix_k}04 = ?", f"operand_{prefix_op}_01_04 = ?", f"operand_{prefix_op}_02_04 = ?",
                f"operator_{prefix_op}_04 = ?",
                f"{prefix_k}05 = ?", f"operand_{prefix_op}_01_05 = ?", f"operand_{prefix_op}_02_05 = ?",
                f"operator_{prefix_op}_05 = ?"
            ]

            for pr_nmb in target_products:
                for mdl_nmb in target_models:
                    params = [
                        coeffs[0],
                        coeffs[1], terms[0][0], terms[0][1], terms[0][2],
                        coeffs[2], terms[1][0], terms[1][1], terms[1][2],
                        coeffs[3], terms[2][0], terms[2][1], terms[2][2],
                        coeffs[4], terms[3][0], terms[3][1], terms[3][2],
                        coeffs[5], terms[4][0], terms[4][1], terms[4][2],
                        pr_nmb, el_nmb, mdl_nmb
                    ]
                    query = f"UPDATE el_set SET {', '.join(update_fields)} WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?"
                    self.db.execute(query, params)

            unsupported_used = any(coeffs[i] != 0.0 or terms[i - 1][2] != 0 for i in range(6, 11))
            if unsupported_used:
                QMessageBox.warning(self, "Внимание",
                                    f"Уравнение сохранено частично для {len(target_products)} продуктов и {len(target_models)} моделей.\n"
                                    "База данных успешно приняла члены A0 — A5.\n"
                                    "Для A6 — A10 необходимо доработать таблицу el_set.")
            else:
                QMessageBox.information(self, "Успех",
                                        f"Уравнение успешно сохранено!\n"
                                        f"Обновлено продуктов: {len(target_products)}\n"
                                        f"Обновлено моделей: {len(target_models)}")

        except Exception as e:
            print("Ошибка при сохранении уравнения:")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить уравнение:\n{e}")


class SaveEquationDialog(QDialog):
    def __init__(self, default_pr="1", default_mdl="1", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сохранение уравнения")
        self.setModal(True)
        self.resize(350, 150)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.products_edit = QLineEdit(str(default_pr))
        self.products_edit.setPlaceholderText("Например: 1, 2, 4-6")

        self.models_edit = QLineEdit(str(default_mdl))
        self.models_edit.setPlaceholderText("Например: 1, 2")

        form_layout.addRow("Продукты:", self.products_edit)
        form_layout.addRow("Модели:", self.models_edit)
        layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Ok).setText("Сохранить")
        self.button_box.button(QDialogButtonBox.Cancel).setText("Отмена")
        layout.addWidget(self.button_box)

    def get_data(self):
        try:
            def parse_numbers(text):
                numbers = set()
                parts = text.replace(' ', '').split(',')
                for part in parts:
                    if not part: continue
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        if start > end: start, end = end, start
                        numbers.update(range(start, end + 1))
                    else:
                        numbers.add(int(part))
                return sorted(list(numbers))

            pr_list = parse_numbers(self.products_edit.text())
            mdl_list = parse_numbers(self.models_edit.text())

            if not pr_list or not mdl_list:
                raise ValueError("Поля продуктов и моделей не могут быть пустыми.")

            return pr_list, mdl_list

        except Exception:
            raise ValueError(
                "Некорректный формат ввода.\nИспользуйте только числа, запятые и тире (например: 1, 3, 5-8).")
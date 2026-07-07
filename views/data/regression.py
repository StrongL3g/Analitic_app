# views/data/regression.py
import json
import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QSplitter, QMessageBox,
    QDialog, QDialogButtonBox, QLineEdit, QFormLayout, QTabWidget, QApplication
)
from PySide6.QtGui import QColor, QCursor
from PySide6.QtGui import QKeySequence, QShortcut
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


class RegressionPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_meas_type = 0
        self.raw_buffer = []
        self.init_ui()

        self.combo_element.currentIndexChanged.connect(self.load_data)
        self.combo_meas_type.currentIndexChanged.connect(self.load_data)
        for combo in self.combo_equation_terms:
            combo.currentIndexChanged.connect(self.recalculate_all)

        if self.combo_element.count() > 0:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Регрессионный анализ")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        main_splitter = QSplitter(Qt.Vertical)

        top_widget = QWidget()
        top_layout = QHBoxLayout()

        left_top_group = QGroupBox("Результаты и управление")
        left_top_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        self.btn_change_selection = QPushButton("Изменить выборку")
        self.btn_save_equation = QPushButton("Сохранить уравнение")
        self.btn_load_data = QPushButton("Выгрузка данных")
        self.btn_auto_select = QPushButton("✨ Автоподбор")
        self.btn_auto_select.setStyleSheet("background-color: #f0fdf4; font-weight: bold; border: 1px solid #22c55e;")

        # Добавляем горячую клавишу Ctrl+C для таблицы
        shortcut = QShortcut(QKeySequence("Ctrl+C"), self)
        shortcut.activated.connect(self.copy_to_excel)

        self.btn_change_selection.clicked.connect(self.open_sample_dialog)
        self.btn_save_equation.clicked.connect(self.save_equation)
        self.btn_load_data.clicked.connect(self.load_data)
        self.btn_auto_select.clicked.connect(self.auto_select_terms)

        btn_layout.addWidget(self.btn_change_selection)
        btn_layout.addWidget(self.btn_auto_select)
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

        right_top_group = QGroupBox("График зависимости C_хим от C_расч")
        right_top_layout = QVBoxLayout()
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect('button_press_event', self.on_plot_double_click)
        right_top_layout.addWidget(self.canvas)
        right_top_group.setLayout(right_top_layout)

        top_layout.addWidget(left_top_group, 45)
        top_layout.addWidget(right_top_group, 55)
        top_widget.setLayout(top_layout)

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

        bottom_layout.addWidget(QLabel("Таблицы выборки (Двойной клик исключает/возвращает строку):"))
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
        main_splitter.setSizes([400, 300])
        layout.addWidget(main_splitter)
        self.setLayout(layout)
        self.ini_load_elements()

    def copy_to_excel(self):
        # Определяем, какая вкладка открыта (Рабочая или Исключенные)
        current_table = self.tabs.currentWidget()

        # Получаем выделенные диапазоны
        selected_ranges = current_table.selectedRanges()
        if not selected_ranges:
            return

        text = ""
        # Проходим по строкам выделенного диапазона
        for r in range(selected_ranges[0].topRow(), selected_ranges[0].bottomRow() + 1):
            row_data = []
            # Проходим по столбцам
            for c in range(selected_ranges[0].leftColumn(), selected_ranges[0].rightColumn() + 1):
                item = current_table.item(r, c)
                row_data.append(item.text() if item else "")
            # Соединяем ячейки через знак табуляции (Excel это понимает как столбцы)
            text += "\t".join(row_data) + "\n"

        # Кладем в буфер обмена
        QApplication.clipboard().setText(text)
        self.statusBar().showMessage("Данные скопированы в буфер обмена", 2000) if hasattr(self, 'statusBar') else None

    def create_data_table(self):
        table = QTableWidget()
        table.setColumnCount(17)
        table.setHorizontalHeaderLabels([
            "Продукт", "Время (ts)", "Название пробы",
            "A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10",
            "C_хим", "C_расч", "ΔC", "δC=|ΔC/C_хим|"
        ])
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        return table

    def ini_load_elements(self):
        try:
            elements_path = get_config_path() / "elements.json"
            if os.path.exists(elements_path):
                with open(elements_path, "r", encoding="utf-8") as f:
                    elements_data = json.load(f)
                valid_elements = [elem for elem in elements_data if elem.get("name") != "-"]
                self.combo_element.clear()
                for elem in valid_elements: self.combo_element.addItem(elem["name"], elem["number"])
        except Exception as e:
            print(f"Ошибка загрузки элементов: {e}")

    def open_sample_dialog(self):
        dialog = SampleDialog(self.db, self)
        if dialog.exec(): self.load_data()

    def load_data(self):
        try:
            sample_path = get_config_path() / "sample" / "s_regress.json"
            if not os.path.exists(sample_path): return
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_config = json.load(f)
            if not sample_config: return

            pr_nmb = sample_config[0].get("product_id")
            if not pr_nmb or pr_nmb <= 0:
                for t in [self.table_active, self.table_excluded]: t.setRowCount(0)
                return

            el_nmb = self.combo_element.currentData()

            active_mdl = self.db.fetch_one("SELECT mdl_nmb FROM mdl_set WHERE pr_nmb = ? AND active_model = 1",
                                           [pr_nmb])
            if not active_mdl:
                active_mdl = self.db.fetch_one("SELECT TOP 1 mdl_nmb FROM mdl_set WHERE pr_nmb = ?", [pr_nmb])
                if not active_mdl: return

            active_mdl_nmb = active_mdl["mdl_nmb"]
            el_set_row = self.db.fetch_one("SELECT * FROM el_set WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?",
                                           [pr_nmb, el_nmb, active_mdl_nmb])
            if not el_set_row: return

            self.current_meas_type = el_set_row["meas_type"]
            self._load_equation_terms(self.current_meas_type, el_nmb)

            self._fetch_pr_meas_data(sample_config, el_nmb, self.current_meas_type)
            if not self.raw_buffer:
                self.table_active.setRowCount(0)
                self.table_excluded.setRowCount(0)
                return

            self._apply_initial_equation(el_set_row, self.current_meas_type)
            self.recalculate_all()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки: {str(e)}")

    def _fetch_pr_meas_data(self, sample_config, el_nmb, meas_type):
        self.raw_buffer.clear()
        for cond in sample_config:
            pr_nmb = cond["product_id"]
            if pr_nmb <= 0: continue

            d_from = cond['date_from'].replace('-', '')
            d_to = cond['date_to'].replace('-', '')
            start_dt = f"{d_from} {cond['time_from']}"
            end_dt = f"{d_to} {cond['time_to']}"

            cols = ["pr_nmb", "timestamp", "sample_name"]

            if meas_type == 0:
                cols.extend([f"i_00_{i:02d}" for i in range(20)])
            else:
                cols.extend([f"c_cor_{i:02d}" for i in range(1, 9)])
            chem_col = f"c_chem_{el_nmb:02d}"
            cols.append(chem_col)

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
                    dt = r.get("timestamp")
                    dt_str = dt.strftime("%Y-%m-%d %H:%M:%S") if hasattr(dt, 'strftime') else str(dt or "")

                    record = {
                        "pr_nmb": r.get("pr_nmb", ""),
                        "timestamp_str": dt_str,
                        "sample_name": r.get("sample_name", ""),
                        "c_chem": float(r.get(chem_col, 0.0)),
                        "is_active": True,
                        "raw_db_row": r,
                        "features": [0.0] * 10,
                        "c_calc": 0.0,
                        "dc": 0.0,
                        "ddc": 0.0
                    }
                    self.raw_buffer.append(record)
            except Exception as e:
                print(f"Ошибка запроса БД: {e}")

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

    def _apply_initial_equation(self, el_set_row, meas_type):
        try:
            op_prefix = "operand_i_" if meas_type == 0 else "operand_c_"
            op_type = "operator_i_" if meas_type == 0 else "operator_c_"

            json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
            json_path = get_config_path() / json_file
            if not os.path.exists(json_path): return

            term_lookup = {}
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

            term_specs = []
            for i in range(1, 11): term_specs.append(
                (f"{op_prefix}01_{i:02d}", f"{op_prefix}02_{i:02d}", f"{op_type}{i:02d}"))

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

    def recalculate_all(self):
        if not self.raw_buffer: return

        el_nmb = self.combo_element.currentData()
        for i, combo in enumerate(self.combo_equation_terms):
            desc = combo.currentText().strip()
            feature_array = self._compute_feature(desc, self.current_meas_type, el_nmb)
            for row_idx, rec in enumerate(self.raw_buffer): rec["features"][i] = feature_array[row_idx]

        active_X, active_y = [], []
        for rec in self.raw_buffer:
            if rec["is_active"] and rec["c_chem"] != 0:
                active_X.append([1.0] + rec["features"])
                active_y.append(rec["c_chem"])

        coeffs, t_stats = np.zeros(11), np.zeros(11)
        if len(active_y) > 0:
            X_mat, y_vec = np.array(active_X), np.array(active_y)
            active_cols = [0]
            for i in range(1, 11):
                if self.combo_equation_terms[i - 1].currentText().strip(): active_cols.append(i)

            if len(active_cols) > 0:
                X_reduced = X_mat[:, active_cols]
                try:
                    dof = len(y_vec) - X_reduced.shape[1]

                    # 1. Получаем псевдообратную матрицу напрямую для стабильности
                    pinv_X = np.linalg.pinv(X_reduced)

                    # 2. Считаем коэффициенты (это эквивалентно lstsq, но дает нам pinv_X для ошибок)
                    c_reduced = pinv_X @ y_vec

                    # 3. Считаем предсказания и среднеквадратичную ошибку (MSE)
                    y_pred = X_reduced @ c_reduced
                    mse = np.sum((y_vec - y_pred) ** 2) / max(dof, 1)

                    # 4. Считаем ковариационную матрицу стабильным способом: pinv(X) @ pinv(X).T
                    # Это полностью заменяет нестабильный pinv(X.T @ X)
                    cov_matrix = (pinv_X @ pinv_X.T) * mse
                    std_errs = np.sqrt(np.maximum(np.diag(cov_matrix), 0.0))

                    # 5. Вычисляем t-статистику (только если есть степени свободы и ошибка > 0)
                    with np.errstate(divide='ignore', invalid='ignore'):
                        t_reduced = np.where((std_errs > 0) & (dof > 0), c_reduced / std_errs, 0.0)

                    for idx_reduced, idx_full in enumerate(active_cols):
                        coeffs[idx_full] = c_reduced[idx_reduced]
                        t_stats[idx_full] = np.abs(t_reduced[idx_reduced])

                except Exception as e:
                    print(f"Ошибка матричного расчета регрессии/значимости: {e}")

        for rec in self.raw_buffer:
            c_calc = coeffs[0] + sum(coeffs[i + 1] * rec["features"][i] for i in range(10))
            rec["c_calc"] = c_calc
            rec["dc"] = c_calc - rec["c_chem"]
            rec["ddc"] = abs(rec["dc"]) / rec["c_chem"] if rec["c_chem"] != 0 else 0.0

        self._update_coefficients_table(coeffs, t_stats)
        self._update_statistics_table()
        self._rebuild_tables_ui()
        self._update_plot()

    def auto_select_terms(self):
        if not self.raw_buffer:
            QMessageBox.warning(self, "Внимание", "Нет данных для автоподбора.")
            return

        self.setCursor(Qt.WaitCursor)
        try:
            combo = self.combo_equation_terms[0]
            all_terms = [combo.itemText(i) for i in range(1, combo.count())]
            if not all_terms: return

            active_mask = np.array([rec['is_active'] for rec in self.raw_buffer])
            y_full = np.array([rec['c_chem'] for rec in self.raw_buffer])
            valid_mask = (y_full != 0) & active_mask
            y_vector = y_full[valid_mask]
            n_samples = len(y_vector)

            if n_samples < 5:
                QMessageBox.warning(self, "Внимание", "Слишком мало активных точек для качественного подбора.")
                return

            el_nmb, meas_type = self.combo_element.currentData(), self.current_meas_type
            feature_dict = {}
            for desc in all_terms:
                vals = self._compute_feature(desc, meas_type, el_nmb)
                feature_dict[desc] = np.array(vals)[valid_mask]

            selected_terms = []
            current_X = np.ones((n_samples, 1))

            def get_adj_r2_and_t(X, y):
                n, p = X.shape
                if n <= p: return -float('inf'), 0
                XTX_pinv = np.linalg.pinv(X.T @ X)
                coeffs = XTX_pinv @ X.T @ y
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                ss_res = np.sum((y - X @ coeffs) ** 2)
                r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
                adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p)
                mse = ss_res / (n - p)
                with np.errstate(divide='ignore', invalid='ignore'):
                    t_stats = np.where(np.sqrt(np.abs(np.diag(XTX_pinv)) * mse) != 0,
                                       coeffs / np.sqrt(np.abs(np.diag(XTX_pinv)) * mse), 0)
                return adj_r2, np.abs(t_stats[-1]) if len(t_stats) > 1 else 0

            current_adj_r2, _ = get_adj_r2_and_t(current_X, y_vector)

            for step in range(10):
                best_desc, best_adj_r2 = None, current_adj_r2
                for desc in all_terms:
                    if desc in selected_terms: continue
                    adj_r2, last_t = get_adj_r2_and_t(np.column_stack([current_X, feature_dict[desc]]), y_vector)
                    if adj_r2 > best_adj_r2 and last_t > 1.5:
                        best_adj_r2, best_desc = adj_r2, desc
                if best_desc and (best_adj_r2 - current_adj_r2 > 0.005):
                    selected_terms.append(best_desc)
                    current_X = np.column_stack([current_X, feature_dict[best_desc]])
                    current_adj_r2 = best_adj_r2
                else:
                    break

            if not selected_terms:
                QMessageBox.information(self, "Результат", "Не удалось подобрать значимые члены для этих данных.")
                return

            for i, combo in enumerate(self.combo_equation_terms):
                combo.blockSignals(True)
                if i < len(selected_terms):
                    idx = combo.findText(selected_terms[i])
                    combo.setCurrentIndex(idx if idx >= 0 else 0)
                else:
                    combo.setCurrentIndex(0)
                combo.blockSignals(False)

            self.recalculate_all()
            QMessageBox.information(self, "Успех",
                                    f"Автоподбор завершен!\nВыбрано членов: {len(selected_terms)}\nR²: {(current_adj_r2 if current_adj_r2 > 0 else 0):.4f}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка: {e}")
        finally:
            self.setCursor(Qt.ArrowCursor)

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
                    val1 = float(db_row.get(f"i_00_{x1:02d}", 0.0))
                    val2 = float(db_row.get(f"i_00_{x2:02d}", 0.0)) if x2 != 0 else 1.0
                else:
                    val1 = float(db_row.get(f"c_cor_{x1:02d}", 0.0)) if x1 != 0 else 1.0
                    val2 = float(db_row.get(f"c_cor_{x2:02d}", 0.0)) if x2 != 0 else 1.0

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
            except Exception as e:
                print(f"Ошибка в расчете: {e}")
                result.append(0.0)
        return result

    def _rebuild_tables_ui(self):
        for t in [self.table_active, self.table_excluded]:
            t.blockSignals(True)
            t.setUpdatesEnabled(False)
            t.setSortingEnabled(False)
            t.setRowCount(0)

        active_count = sum(1 for r in self.raw_buffer if r['is_active'])
        excl_count = len(self.raw_buffer) - active_count

        self.table_active.setRowCount(active_count)
        self.table_excluded.setRowCount(excl_count)
        self.tabs.setTabText(0, f"Рабочая выборка ({active_count})")
        self.tabs.setTabText(1, f"Исключенные строки ({excl_count})")

        act_idx, exc_idx = 0, 0
        for buf_idx, rec in enumerate(self.raw_buffer):
            is_act = rec['is_active']
            t_widget = self.table_active if is_act else self.table_excluded
            row_idx = act_idx if is_act else exc_idx

            item_pr = QTableWidgetItem(str(rec["pr_nmb"]))
            item_pr.setData(Qt.UserRole, buf_idx)
            item_pr.setFlags(item_pr.flags() & ~Qt.ItemFlag.ItemIsEditable)
            t_widget.setItem(row_idx, 0, item_pr)

            t_widget.setItem(row_idx, 1, self._create_readonly_item(rec["timestamp_str"]))
            sample_name = rec["sample_name"]
            t_widget.setItem(row_idx, 2, self._create_readonly_item(sample_name if sample_name else ""))

            for i in range(10): t_widget.setItem(row_idx, 3 + i,
                                                 self._create_readonly_item(fmt_num(rec["features"][i]), True))
            t_widget.setItem(row_idx, 13, self._create_readonly_item(fmt_num(rec["c_chem"]), True))
            t_widget.setItem(row_idx, 14, self._create_readonly_item(fmt_num(rec["c_calc"]), True))
            t_widget.setItem(row_idx, 15, self._create_readonly_item(fmt_num(rec["dc"]), True))
            t_widget.setItem(row_idx, 16, self._create_readonly_item(f"{rec['ddc'] * 100:.2f}%", True))

            if is_act:
                act_idx += 1
            else:
                exc_idx += 1

        for t in [self.table_active, self.table_excluded]:
            t.setSortingEnabled(True)
            t.setUpdatesEnabled(True)
            t.blockSignals(False)

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
            QTimer.singleShot(0, self.recalculate_all)

    def on_plot_double_click(self, event):
        if not event.dblclick or event.inaxes != self.ax: return
        x, y = event.xdata, event.ydata
        if x is None or y is None: return

        min_dist = float('inf')
        closest_idx = -1
        xlim, ylim = self.ax.get_xlim(), self.ax.get_ylim()
        x_range, y_range = xlim[1] - xlim[0], ylim[1] - ylim[0]
        if x_range == 0 or y_range == 0: return

        for i, rec in enumerate(self.raw_buffer):
            cx, cy = rec.get('c_chem'), rec.get('c_calc')
            if cx is not None and cy is not None:
                dist = ((cx - x) / x_range) ** 2 + ((cy - y) / y_range) ** 2
                if dist < min_dist: min_dist, closest_idx = dist, i

        if closest_idx != -1 and min_dist < 0.002:
            self.raw_buffer[closest_idx]['is_active'] = not self.raw_buffer[closest_idx]['is_active']
            QTimer.singleShot(0, self.recalculate_all)

    def _update_coefficients_table(self, coefficients, t_stats):
        a0_item = self.coeff_table.item(0, 1)
        if a0_item: a0_item.setText("-")

        for i in range(1, 11):
            combo = self.combo_equation_terms[i - 1]
            term_desc = combo.currentText().strip()
            multiplier_item = self.coeff_table.item(i, 1)
            if multiplier_item: multiplier_item.setText(term_desc if term_desc else "-")

        from PySide6.QtGui import QColor
        for i, (coeff, t_stat) in enumerate(zip(coefficients, t_stats)):
            value_item = self.coeff_table.item(i, 2)
            if value_item: value_item.setText(fmt_num(coeff))

            significance_item = self.coeff_table.item(i, 3)
            if significance_item:
                if coeff == 0.0 and i > 0 and self.combo_equation_terms[i - 1].currentText().strip() == "":
                    significance_item.setText("-")
                    significance_item.setBackground(Qt.GlobalColor.white)
                else:
                    significance_item.setText(f"{t_stat:.4f}")
                    if t_stat >= 3.0:
                        significance_item.setBackground(Qt.GlobalColor.white)
                    elif t_stat >= 1.0:
                        significance_item.setBackground(QColor("#FFE4B5"))
                    else:
                        significance_item.setBackground(QColor("#FFCCCC"))

    def _update_statistics_table(self):
        c_chem, c_calc, dc = [], [], []
        for rec in self.raw_buffer:
            if rec['is_active']:
                c_chem.append(rec['c_chem'])
                c_calc.append(rec['c_calc'])
                dc.append(rec['dc'])

        if not c_chem or len(c_chem) < 2:
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
        arrParam[6] = (sum_xy ** 2) / (sum_x2 * sum_y2) if (sum_x2 != 0 and sum_y2 != 0) else 0

        formats = [
            f"{arrParam[1]:.4f}", f"{arrParam[2] * 100:.2f}%", f"{arrParam[3]:.2f}",
            f"{arrParam[4]:.2f}", f"{arrParam[5]:.2f}", f"{arrParam[6]:.4f}"
        ]

        for row, formatted_val in enumerate(formats):
            item = self.stats_table.item(row, 1)
            if item: item.setText(formatted_val)

    def _update_plot(self):
        try:
            self.ax.clear()
            c_chem_act, c_calc_act, c_chem_exc, c_calc_exc = [], [], [], []
            for rec in self.raw_buffer:
                if rec['is_active']:
                    c_chem_act.append(rec['c_chem'])
                    c_calc_act.append(rec['c_calc'])
                else:
                    c_chem_exc.append(rec['c_chem'])
                    c_calc_exc.append(rec['c_calc'])

            if c_chem_act and c_calc_act:
                self.ax.scatter(c_chem_act, c_calc_act, alpha=0.6, color='tab:blue', label='Участвуют')
                min_val, max_val = min(min(c_chem_act), min(c_calc_act)), max(max(c_chem_act), max(c_calc_act))
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
                except Exception as e:
                    print(f"Ошибка парсинга коэффициента A{i}: {e}")
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
                            if term.get("description", "").strip() == desc:
                                x1, x2, op = term["x1"], term["x2"], term["op"]
                                break
                    else:
                        for group in json_data.get("interactions", []):
                            if group.get("element_original_number") == el_nmb:
                                for term in group.get("interactions", []):
                                    if term.get("description", "").strip() == desc:
                                        x1, x2, op = term["x1"], term["x2"], term["op"]
                                        break
                                break
                terms.append((x1, x2, op))

            prefix_k = "k_i_alin" if meas_type == 0 else "k_c_alin"
            prefix_op = "i" if meas_type == 0 else "c"

            update_fields = [f"{prefix_k}00 = ?"]
            for i in range(1, 11):
                update_fields.extend([
                    f"{prefix_k}{i:02d} = ?",
                    f"operand_{prefix_op}_01_{i:02d} = ?",
                    f"operand_{prefix_op}_02_{i:02d} = ?",
                    f"operator_{prefix_op}_{i:02d} = ?"
                ])

            # Формируем пакет параметров для executemany
            params_list = []
            for pr_nmb in target_products:
                for mdl_nmb in target_models:
                    params = [coeffs[0]]
                    for i in range(1, 11):
                        params.extend([coeffs[i], terms[i - 1][0], terms[i - 1][1], terms[i - 1][2]])
                    params.extend([pr_nmb, el_nmb, mdl_nmb])
                    params_list.append(params)

            # Выполняем один пакетный запрос вместо сотен мелких
            query = f"UPDATE el_set SET {', '.join(update_fields)} WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?"
            self.db.executemany(query, params_list)

            QMessageBox.information(
                self, "Успех",
                f"Уравнение успешно сохранено пакетом!\nОбновлено продуктов: {len(target_products)}\nОбновлено моделей: {len(target_models)}"
            )
        except Exception as e:
            print(f"Критическая ошибка в save_equation: {e}")
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
        self.models_edit = QLineEdit(str(default_mdl))
        form_layout.addRow("Продукты:", self.products_edit)
        form_layout.addRow("Модели:", self.models_edit)
        layout.addLayout(form_layout)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_data(self):
        try:
            def parse_numbers(text):
                numbers = set()
                for part in text.replace(' ', '').split(','):
                    if not part: continue
                    if '-' in part:
                        start, end = map(int, part.split('-'))
                        if start > end: start, end = end, start
                        numbers.update(range(start, end + 1))
                    else:
                        numbers.add(int(part))
                return sorted(list(numbers))

            pr_list, mdl_list = parse_numbers(self.products_edit.text()), parse_numbers(self.models_edit.text())
            if not pr_list or not mdl_list: raise ValueError("Поля продуктов и моделей не могут быть пустыми.")
            return pr_list, mdl_list
        except Exception:
            raise ValueError("Некорректный формат ввода.\nИспользуйте только числа, запятые и тире.")
# views/data/regression.py
import json
import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QSplitter, QMessageBox
)
from PySide6.QtCore import Qt
from database.db import Database
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from views.data.sample_dialog import SampleDialog
from utils.path_manager import get_config_path


class RegressionPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_sample = []
        self.current_element = None
        self.current_meas_type = 0  # 0 - по интенсивностям, 1 - по концентрациям
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

        # === Заголовок ===
        title = QLabel("Регрессионный анализ")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # === Основной сплиттер (вертикальный) ===
        main_splitter = QSplitter(Qt.Vertical)

        # === Верхняя часть ===
        top_widget = QWidget()
        top_layout = QHBoxLayout()

        # === Левая верхняя часть ===
        left_top_group = QGroupBox("Результаты и управление")
        left_top_layout = QVBoxLayout()

        # Кнопки
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

        # === Таблица коэффициентов (Расширена до 11) ===
        left_top_layout.addWidget(QLabel("Сводная таблица коэффициентов:"))
        self.coeff_table = QTableWidget()
        self.coeff_table.setRowCount(11)  # A0–A10
        self.coeff_table.setColumnCount(4)
        self.coeff_table.setHorizontalHeaderLabels(["Коэффициент", "Множитель", "Значение", "Значимость"])
        self.coeff_table.verticalHeader().setVisible(False)

        for row in range(11):
            name = f"A{row}"
            item = QTableWidgetItem(name)
            item.setBackground(Qt.GlobalColor.lightGray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.coeff_table.setItem(row, 0, item)

            multiplier_item = QTableWidgetItem("-")
            multiplier_item.setFlags(multiplier_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.coeff_table.setItem(row, 1, multiplier_item)

            value_item = QTableWidgetItem("0.0")
            self.coeff_table.setItem(row, 2, value_item)

            significance_item = QTableWidgetItem("0.0")
            self.coeff_table.setItem(row, 3, significance_item)

        left_top_layout.addWidget(self.coeff_table)

        # === Таблица характеристик уравнения ===
        left_top_layout.addWidget(QLabel("Характеристики уравнения:"))
        self.stats_table = QTableWidget()
        self.stats_table.setRowCount(6)
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        self.stats_table.verticalHeader().setVisible(False)

        stats_labels = [
            "СКО σ", "Отн. СКО", "Смин", "Смакс", "Ссред", "Корреляция R²"
        ]

        for row, label in enumerate(stats_labels):
            item = QTableWidgetItem(label)
            item.setBackground(Qt.GlobalColor.lightGray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.stats_table.setItem(row, 0, item)

            value_item = QTableWidgetItem("0.0")
            self.stats_table.setItem(row, 1, value_item)

        left_top_layout.addWidget(self.stats_table)
        left_top_group.setLayout(left_top_layout)

        # === Верхняя правая часть (график) ===
        right_top_group = QGroupBox("График зависимости C_хим от C_расч")
        right_top_layout = QVBoxLayout()
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.canvas = FigureCanvas(self.fig)
        right_top_layout.addWidget(self.canvas)
        right_top_group.setLayout(right_top_layout)

        top_layout.addWidget(left_top_group, 40)
        top_layout.addWidget(right_top_group, 60)
        top_widget.setLayout(top_layout)

        # === Нижняя часть ===
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()

        # Комбо-боксы выборки
        combo_layout = QHBoxLayout()
        self.combo_element = QComboBox()
        combo_layout.addWidget(QLabel("Элемент:"))
        combo_layout.addWidget(self.combo_element)

        self.combo_meas_type = QComboBox()
        self.combo_meas_type.addItems(["Все пробы", "Ручные", "Цикл"])
        combo_layout.addWidget(QLabel("Пробы:"))
        combo_layout.addWidget(self.combo_meas_type)
        combo_layout.addStretch()
        bottom_layout.addLayout(combo_layout)

        # 10 комбо-боксов для членов уравнения (Сетка)
        terms_group = QGroupBox("Члены уравнения (A1 - A10)")
        terms_layout = QGridLayout()
        self.combo_equation_terms = []
        for i in range(10):
            combo = QComboBox()
            combo.setMinimumWidth(120)
            self.combo_equation_terms.append(combo)
            row = i // 5
            col = i % 5
            terms_layout.addWidget(QLabel(f"A{i + 1}:"), row, col * 2)
            terms_layout.addWidget(combo, row, col * 2 + 1)
        terms_group.setLayout(terms_layout)
        bottom_layout.addWidget(terms_group)

        # Таблица выборки (Расширена до X10)
        bottom_layout.addWidget(QLabel("Таблица выборки:"))
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(16)
        self.data_table.setHorizontalHeaderLabels([
            "Продукт", "Дата/Время",
            "X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", "X9", "X10",
            "C_хим", "C_расч", "ΔC", "δC=|ΔC/C_хим|"
        ])
        bottom_layout.addWidget(self.data_table)

        bottom_widget.setLayout(bottom_layout)

        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([400, 300])

        layout.addWidget(main_splitter)
        self.setLayout(layout)

        self.ini_load_elements()

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
            else:
                self.combo_element.addItems(["Cu", "Ni", "Fe", "ТФ"])
        except Exception as e:
            print(f"Ошибка загрузки элементов: {e}")
            self.combo_element.addItems(["Cu", "Ni", "Fe", "ТФ"])

    def open_sample_dialog(self):
        dialog = SampleDialog(self.db, self)
        if dialog.exec():
            self.load_data()

    def load_data(self):
        try:
            sample_path = get_config_path() / "sample" / "s_regress.json"
            if not os.path.exists(sample_path):
                QMessageBox.warning(self, "Ошибка", "Файл выборки не найден: config/sample/s_regress.json")
                return

            with open(sample_path, "r", encoding="utf-8") as f:
                sample_config = json.load(f)

            if not sample_config:
                QMessageBox.warning(self, "Ошибка", "Выборка пуста. Откройте «Изменить выборку».")
                return

            pr_nmb = sample_config[0].get("product_id")
            if pr_nmb is None:
                return

            el_nmb = self.combo_element.currentData()
            if el_nmb is None: return

            query_el_set = """
                SELECT * FROM el_set
                WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = 1
            """
            el_set_row = self.db.fetch_one(query_el_set, [pr_nmb, el_nmb])
            if not el_set_row:
                QMessageBox.critical(self, "Ошибка", f"Не найдена модель 1 в el_set:\npr_nmb={pr_nmb}, el_nmb={el_nmb}")
                return

            meas_type = el_set_row["meas_type"]
            self.current_meas_type = meas_type

            self._load_equation_terms(meas_type, el_nmb)
            self.raw_buffer = self._fetch_pr_meas_data(sample_config, el_nmb, meas_type)

            if not self.raw_buffer:
                QMessageBox.warning(self, "Информация", "По условиям выборки данных не найдено.")
                self.data_table.setRowCount(0)
                return

            self._apply_initial_equation(el_set_row, meas_type)
            self._update_data_table_from_buffer()
            self.perform_regression()

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"load_data() провалился:\n{str(e)}")

    def _load_equation_terms(self, meas_type, el_nmb):
        try:
            json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
            json_path = get_config_path() / json_file

            terms_list = []
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if meas_type == 0:
                    interactions = data.get("interactions", [])
                    terms_list = [t["description"] for t in interactions if t.get("description")]
                else:
                    for group in data.get("interactions", []):
                        if group.get("element_original_number") == el_nmb:
                            interactions = group.get("interactions", [])
                            terms_list = [t["description"] for t in interactions if t.get("description")]
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

            select_list = ", ".join(f"{c}" for c in cols)
            query = f"""
                SELECT {select_list},
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
                all_rows.extend(self.db.fetch_all(query, [start_dt, end_dt, pr_nmb]))
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

            # Читаем 5 старых членов из базы
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
        self.data_table.setRowCount(0)
        if not self.raw_buffer: return

        self.data_table.setRowCount(len(self.raw_buffer))
        el_nmb = self.combo_element.currentData()

        for row_idx, rec in enumerate(self.raw_buffer):
            self.data_table.setItem(row_idx, 0, QTableWidgetItem(str(rec.get("pr_nmb", ""))))
            self.data_table.setItem(row_idx, 1, QTableWidgetItem(str(rec.get("meas_dt", ""))))
            c_chem = rec.get(f"c_chem_{el_nmb:02d}", "")
            self.data_table.setItem(row_idx, 12, QTableWidgetItem(str(c_chem)))

            # C_расч, ΔC, δC
            self.data_table.setItem(row_idx, 13, QTableWidgetItem(""))
            self.data_table.setItem(row_idx, 14, QTableWidgetItem(""))
            self.data_table.setItem(row_idx, 15, QTableWidgetItem(""))

    def perform_regression(self):
        if not hasattr(self, 'raw_buffer') or not self.raw_buffer:
            return

        try:
            # 1. Умная сборка: Исключаем пустые колонки
            X_active, y_vector, active_indices = self._build_regression_data()
            if X_active is None: return

            # 2. Выполняем регрессию только по активным столбцам
            coeffs_active, stats, std_errs, t_stats, p_vals_active = self._calculate_regression(X_active, y_vector)

            # 3. Разворачиваем коэффициенты обратно в массив из 11 элементов
            full_coeffs = np.zeros(11)
            full_p_vals = np.ones(11)

            full_coeffs[0] = coeffs_active[0]
            full_p_vals[0] = p_vals_active[0]

            for i, original_index in enumerate(active_indices):
                full_coeffs[original_index] = coeffs_active[i + 1]
                full_p_vals[original_index] = p_vals_active[i + 1]

            # 4. Обновляем UI
            self._update_coefficients_table(full_coeffs, full_p_vals)
            self._update_statistics_table(stats, y_vector)
            self.apply_current_equation()
            self._update_plot(y_vector)

        except Exception as e:
            print(f"Ошибка в perform_regression: {e}")

    def _build_regression_data(self):
        try:
            n_samples = len(self.raw_buffer)
            if n_samples == 0: return None, None, None

            el_nmb = self.combo_element.currentData()
            y_vector = np.array([rec.get(f"c_chem_{el_nmb:02d}", 0.0) for rec in self.raw_buffer])

            # Собираем только выбранные признаки
            features = []
            active_indices = []

            for i, combo in enumerate(self.combo_equation_terms):
                term_desc = combo.currentText().strip()
                if term_desc and term_desc != "-":
                    feat_vals = self._compute_feature(term_desc, self.current_meas_type, el_nmb)
                    features.append(feat_vals)
                    active_indices.append(i + 1)  # A1 это индекс 1

            n_features = len(features) + 1
            X_matrix = np.ones((n_samples, n_features))
            for col_idx, feat_vals in enumerate(features):
                X_matrix[:, col_idx + 1] = feat_vals

            return X_matrix, y_vector, active_indices

        except Exception as e:
            print(f"Ошибка в _build_regression_data: {e}")
            return None, None, None

    def _calculate_regression(self, X, y):
        try:
            n_samples, n_features = X.shape
            # Защита от деления на ноль, если признаков больше чем данных
            dof = n_samples - np.linalg.matrix_rank(X)
            if dof <= 0: dof = 1

            coefficients = np.linalg.lstsq(X, y, rcond=None)[0]
            y_pred = X @ coefficients
            residuals = y - y_pred

            mse = np.sum(residuals ** 2) / dof
            rmse = np.sqrt(mse)

            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r_squared = 1 - (np.sum(residuals ** 2) / ss_tot) if ss_tot != 0 else 0

            try:
                # Используем pinv для абсолютной защиты от сингулярных матриц
                XTX_pinv = np.linalg.pinv(X.T @ X)
                standard_errors = np.sqrt(np.abs(np.diag(XTX_pinv)) * mse)

                with np.errstate(divide='ignore', invalid='ignore'):
                    t_stats = np.where(standard_errors != 0, coefficients / standard_errors, 0)

                from scipy import stats
                p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), dof))
            except Exception:
                standard_errors = np.zeros(n_features)
                t_stats = np.zeros(n_features)
                p_values = np.ones(n_features)

            statistics = {
                'rmse': rmse,
                'r_squared': r_squared,
                'y_min': np.min(y),
                'y_max': np.max(y),
                'y_mean': np.mean(y),
                'relative_rmse': rmse / np.mean(y) if np.mean(y) != 0 else 0
            }

            return coefficients, statistics, standard_errors, t_stats, p_values

        except Exception as e:
            print(f"Ошибка в _calculate_regression: {e}")
            return np.zeros(X.shape[1]), {}, np.zeros(X.shape[1]), np.zeros(X.shape[1]), np.ones(X.shape[1])

    def _update_coefficients_table(self, coefficients, p_values):
        # A0
        a0_item = self.coeff_table.item(0, 1)
        if a0_item: a0_item.setText("-")

        # A1..A10
        for i in range(1, 11):
            combo = self.combo_equation_terms[i - 1]
            term_desc = combo.currentText().strip()
            multiplier_item = self.coeff_table.item(i, 1)
            if multiplier_item:
                multiplier_item.setText(term_desc if term_desc else "-")

        # Значения и значимость
        for i, (coeff, p_value) in enumerate(zip(coefficients, p_values)):
            value_item = self.coeff_table.item(i, 2)
            if value_item: value_item.setText(f"{coeff:.6g}")

            significance_item = self.coeff_table.item(i, 3)
            if significance_item:
                if coeff == 0.0 and i > 0 and self.combo_equation_terms[i - 1].currentText().strip() == "":
                    significance_item.setText("-")
                    significance_item.setBackground(Qt.GlobalColor.white)
                else:
                    significance_item.setText(f"{p_value:.4f}")
                    if p_value < 0.05:
                        significance_item.setBackground(Qt.GlobalColor.green)
                    elif p_value < 0.1:
                        significance_item.setBackground(Qt.GlobalColor.yellow)
                    else:
                        significance_item.setBackground(Qt.GlobalColor.white)

    def _update_statistics_table(self, statistics, y_vector=None):
        stats_mapping = [
            (0, statistics.get('rmse', 0)),
            (1, statistics.get('relative_rmse', 0)),
            (2, statistics.get('y_min', 0) if y_vector is None else np.min(y_vector)),
            (3, statistics.get('y_max', 0) if y_vector is None else np.max(y_vector)),
            (4, statistics.get('y_mean', 0) if y_vector is None else np.mean(y_vector)),
            (5, statistics.get('r_squared', 0))
        ]

        for row, value in stats_mapping:
            item = self.stats_table.item(row, 1)
            if item: item.setText(f"{value:.6g}")

    def _update_plot(self, y_vector):
        try:
            self.ax.clear()
            c_chem_values, c_calc_values = [], []

            for row in range(self.data_table.rowCount()):
                chem_item = self.data_table.item(row, 12)
                calc_item = self.data_table.item(row, 13)

                if chem_item and calc_item and chem_item.text() and calc_item.text():
                    try:
                        c_chem_values.append(float(chem_item.text()))
                        c_calc_values.append(float(calc_item.text()))
                    except ValueError:
                        pass

            if c_chem_values and c_calc_values:
                self.ax.scatter(c_chem_values, c_calc_values, alpha=0.6, label='Данные')
                min_val = min(min(c_chem_values), min(c_calc_values))
                max_val = max(max(c_chem_values), max(c_calc_values))
                self.ax.plot([min_val, max_val], [min_val, max_val], 'r--', label='Идеал')
                self.ax.set_xlabel("C_хим")
                self.ax.set_ylabel("C_расч")
                self.ax.set_title("График зависимости C_хим от C_расч")
                self.ax.legend()
                self.ax.grid(True, alpha=0.3)

            self.canvas.draw()
        except Exception as e:
            print(f"Ошибка в _update_plot: {e}")

    def apply_current_equation(self):
        try:
            if not hasattr(self, 'raw_buffer') or not self.raw_buffer: return

            coeffs = []
            for i in range(11):
                item = self.coeff_table.item(i, 2)
                try:
                    coeffs.append(float(item.text()) if item and item.text() else 0.0)
                except:
                    coeffs.append(0.0)

            el_nmb = self.combo_element.currentData()
            features = []
            for i, combo in enumerate(self.combo_equation_terms):
                desc = combo.currentText().strip()
                feat_vals = self._compute_feature(desc, self.current_meas_type, el_nmb)
                features.append(feat_vals)
                self._fill_feature_column(i, feat_vals)

            for row_idx in range(len(self.raw_buffer)):
                c_chem = self.raw_buffer[row_idx].get(f"c_chem_{el_nmb:02d}", 0.0)
                X_row = [1.0] + [features[i][row_idx] for i in range(10)]

                c_calc = sum(coeffs[i] * X_row[i] for i in range(11))
                dC = c_calc - c_chem
                ddc = abs(dC) / c_chem if c_chem != 0 else 0.0

                self.data_table.setItem(row_idx, 13, QTableWidgetItem(f"{c_calc:.6g}"))
                self.data_table.setItem(row_idx, 14, QTableWidgetItem(f"{dC:.6g}"))
                self.data_table.setItem(row_idx, 15, QTableWidgetItem(f"{ddc:.6g}"))

        except Exception as e:
            print(f"Ошибка в apply_current_equation(): {e}")

    def _compute_feature(self, feature_desc: str, meas_type: int, el_nmb: int) -> list:
        if not feature_desc or feature_desc == "-":
            return [0.0] * len(self.raw_buffer)

        json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
        json_path = get_config_path() / json_file

        if not os.path.exists(json_path):
            return [0.0] * len(self.raw_buffer)

        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        x1, x2, op = 0, 0, 0
        found = False

        if meas_type == 0:
            for term in json_data.get("interactions", []):
                if term.get("description") == feature_desc:
                    x1, x2, op = term["x1"], term["x2"], term["op"]
                    found = True
                    break
        else:
            for group in json_data.get("interactions", []):
                if group.get("element_original_number") == el_nmb:
                    for term in group.get("interactions", []):
                        if term.get("description") == feature_desc:
                            x1, x2, op = term["x1"], term["x2"], term["op"]
                            found = True
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
                    denom = val2 * val2
                    res = val1 / denom if denom != 0 else 0.0
                elif op == 7:
                    denom = val1 * val1
                    res = 1.0 / denom if denom != 0 else 0.0
                else:
                    res = 0.0

                result.append(res)
            except Exception:
                result.append(0.0)

        return result

    def _fill_feature_column(self, col_index: int, values: list):
        if 0 <= col_index <= 9:
            for row_idx, val in enumerate(values):
                self.data_table.setItem(row_idx, 2 + col_index, QTableWidgetItem(f"{val:.6g}"))

    def save_equation(self):
        try:
            if not hasattr(self, 'raw_buffer') or not self.raw_buffer:
                QMessageBox.warning(self, "Внимание", "Нет данных для сохранения. Сначала загрузите выборку.")
                return

            sample_path = get_config_path() / "sample" / "s_regress.json"
            with open(sample_path, "r", encoding="utf-8") as f:
                sample_config = json.load(f)

            pr_nmb = sample_config[0].get("product_id")
            el_nmb = self.combo_element.currentData()
            meas_type = self.current_meas_type

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

            params = [
                coeffs[0],
                coeffs[1], terms[0][0], terms[0][1], terms[0][2],
                coeffs[2], terms[1][0], terms[1][1], terms[1][2],
                coeffs[3], terms[2][0], terms[2][1], terms[2][2],
                coeffs[4], terms[3][0], terms[3][1], terms[3][2],
                coeffs[5], terms[4][0], terms[4][1], terms[4][2],
                pr_nmb, el_nmb
            ]

            query = f"""
                UPDATE el_set
                SET {', '.join(update_fields)}
                WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = 1
            """

            self.db.execute(query, params)

            # Проверяем, есть ли заполненные члены A6-A10
            unsupported_used = any(coeffs[i] != 0.0 or terms[i - 1][2] != 0 for i in range(6, 11))

            if unsupported_used:
                QMessageBox.warning(self, "Внимание",
                                    "Уравнение сохранено частично.\n\n"
                                    "База данных успешно приняла члены A0 — A5.\n"
                                    "Для сохранения A6 — A10 необходимо доработать столбцы в таблице el_set.")
            else:
                QMessageBox.information(self, "Успех", "Уравнение и коэффициенты успешно сохранены в базу данных!")

        except Exception as e:
            print("Ошибка при сохранении уравнения:")
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить уравнение:\n{e}")
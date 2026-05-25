# views/data/recalc.py
import json
import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QSplitter, QMessageBox, QHeaderView,
    QLineEdit, QFormLayout
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
            return True  # Пустые или некорректные ячейки будут сгруппированы в конце/начале
        if v1 is not None and v2 is None:
            return False
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

        # Подключаем обработчики
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

        stat_labels = [
            "Среднее ΔC", "Отн. ΔC (%)", "СКО ΔC", "Отн. СКО ΔC (%)",
            "Смин", "Смакс", "Ссред",
            "t-расч (Стьюдент)", "t-табл (Стьюдент)",
            "F-расч (Фишер)", "F-табл (Фишер)"
        ]

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

        # Таблица выборки
        bottom_layout.addWidget(
            QLabel("Таблица выборки (Клик на заголовок для сортировки, Двойной клик на строку - исключить):"))
        self.data_table = QTableWidget()
        self.data_table.setSortingEnabled(True)
        self.data_table.cellDoubleClicked.connect(self.on_table_double_click)

        bottom_layout.addWidget(self.data_table)

        bottom_widget.setLayout(bottom_layout)
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([450, 350])
        layout.addWidget(main_splitter)
        self.setLayout(layout)

        self.ini_load_elements()

    def on_coeff_changed(self, item):
        if not self._is_updating_ui and item.column() == 2:
            self.perform_recalc()

    def on_table_double_click(self, row, col):
        pr_item = self.data_table.item(row, 0)
        dt_item = self.data_table.item(row, 1)
        if not pr_item or not dt_item: return

        for i, rec in enumerate(self.raw_buffer):
            if str(rec.get("pr_nmb", "")) == pr_item.text() and rec.get("meas_dt", "") == dt_item.text():
                self.toggle_row_state(i)
                break

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
            cx = rec.get('c_chem', None)
            cy = rec.get('c_calc', None)
            if cx is not None and cy is not None:
                dist = ((cx - x) / x_range) ** 2 + ((cy - y) / y_range) ** 2
                if dist < min_dist:
                    min_dist, closest_idx = dist, i

        if closest_idx != -1 and min_dist < 0.002:
            self.toggle_row_state(closest_idx)

    def toggle_row_state(self, idx):
        if idx < 0 or idx >= len(self.raw_buffer): return
        self.raw_buffer[idx]['is_active'] = not self.raw_buffer[idx].get('is_active', True)

        self._update_data_table_from_buffer()
        self.perform_recalc()

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
            if not os.path.exists(sample_path): return

            with open(sample_path, "r", encoding="utf-8") as f:
                sample_config = json.load(f)

            if not sample_config: return

            pr_nmb = sample_config[0].get("product_id")
            el_nmb = self.combo_element.currentData()
            mdl_nmb = self.combo_model.currentIndex() + 1

            el_set_row = self.db.fetch_one("SELECT * FROM el_set WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?",
                                           [pr_nmb, el_nmb, mdl_nmb])
            if not el_set_row: return

            self.current_meas_type = el_set_row["meas_type"]
            self._load_equation_terms(self.current_meas_type, el_nmb)
            self._load_coeffs_to_table(el_set_row, self.current_meas_type)

            self.raw_buffer = self._fetch_meas_data(sample_config, el_nmb, mdl_nmb, self.current_meas_type)

            chem_col = f"c_chem_{el_nmb:02d}"
            self.y_vector_raw = np.array([rec.get(chem_col, 0.0) for rec in self.raw_buffer])

            self._update_data_table_from_buffer()
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
            print(f"Ошибка в _load_equation_terms: {e}")

    def _load_coeffs_to_table(self, el_set_row, meas_type):
        self._is_updating_ui = True

        prefix_k = "k_i_alin" if meas_type == 0 else "k_c_alin"
        prefix_klin = "k_i_klin" if meas_type == 0 else "k_c_klin"
        op_prefix = "operand_i_" if meas_type == 0 else "operand_c_"
        op_type = "operator_i_" if meas_type == 0 else "operator_c_"

        json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
        json_path = get_config_path() / json_file
        term_lookup = {}
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

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
            start_dt = f"{cond['date_from']} {cond['time_from']}"
            end_dt = f"{cond['date_to']} {cond['time_to']}"

            cols = ["pr_nmb", "meas_dt"]
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
                AND pr_nmb = ? AND {chem_col} <> 0 AND mdl_nmb = ?
            """
            meas_index = self.combo_meas_type.currentIndex()
            if meas_index == 1:
                query += " AND meas_type = 0"
            elif meas_index == 2:
                query += " AND meas_type = 1"
            query += " ORDER BY meas_dt, timestamp"

            try:
                rows = self.db.fetch_all(query, [start_dt, end_dt, pr_nmb, mdl_nmb])
                for r in rows: r['is_active'] = True
                all_rows.extend(rows)
            except Exception as e:
                print(f"Ошибка запроса: {e}")

        return all_rows

    def _update_data_table_from_buffer(self):
        self.data_table.blockSignals(True)
        self.data_table.setSortingEnabled(False)
        self.data_table.setRowCount(0)

        # === Измененный порядок заголовков ===
        headers = ["Продукт", "Дата/Время", "C_хим", "C_расч", "ΔC", "δC=|ΔC/C_хим|"]
        raw_cols = []
        if self.current_meas_type == 0:
            raw_cols = [f"I_{i:02d}" for i in range(20)]
        else:
            raw_cols = [f"C_{i:02d}" for i in range(1, 9)]

        headers.extend(raw_cols)

        self.data_table.setColumnCount(len(headers))
        self.data_table.setHorizontalHeaderLabels(headers)

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

            # Продукт и Дата
            set_text_item(0, rec.get("pr_nmb", ""))
            set_text_item(1, rec.get("meas_dt", ""))

            # C_хим (столбец 2)
            c_chem_raw = rec.get(chem_col, "")
            try:
                c_chem_str = f"{float(c_chem_raw):.3f}" if c_chem_raw != "" else ""
            except:
                c_chem_str = str(c_chem_raw)
            set_num_item(2, c_chem_str)

            # Оставляем расчетные пустыми (3, 4, 5)
            set_num_item(3, "")
            set_num_item(4, "")
            set_num_item(5, "")

            # Сырые линии сдвигаются на столбец 6
            col_offset = 6
            if self.current_meas_type == 0:
                for i in range(20):
                    val = rec.get(f"i_00_{i:02d}", 0.0)
                    set_num_item(col_offset + i, f"{val:.4f}")
            else:
                for i in range(1, 9):
                    val = rec.get(f"c_cor_{i:02d}", 0.0)
                    set_num_item(col_offset + i - 1, f"{val:.4f}")

        self.data_table.blockSignals(False)
        self.data_table.setSortingEnabled(True)

    def perform_recalc(self):
        if not hasattr(self, 'raw_buffer') or not self.raw_buffer: return

        try:
            coeffs = []
            for i in range(11):
                try:
                    coeffs.append(float(self.coeff_table.item(i, 2).text().replace(',', '.')))
                except:
                    coeffs.append(0.0)

            try:
                k0 = float(self.coeff_table.item(11, 2).text().replace(',', '.'))
            except:
                k0 = 0.0

            try:
                k1 = float(self.coeff_table.item(12, 2).text().replace(',', '.'))
            except:
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

            # Постоянные фиксированные индексы столбцов
            col_calc = 3
            col_dc = 4
            col_ddc = 5

            # ВАЖНО: Отключаем сортировку ОДИН РАЗ перед всем циклом
            self.data_table.setSortingEnabled(False)

            for row_idx, rec in enumerate(self.raw_buffer):
                c_chem = rec.get(f"c_chem_{el_nmb:02d}", 0.0)
                c_raw = coeffs[0] + sum(coeffs[i + 1] * features[i][row_idx] for i in range(10))

                c_calc = k0 + k1 * c_raw
                rec['c_calc'] = c_calc

                dC = c_calc - c_chem
                ddc = abs(dC) / c_chem if c_chem != 0 else 0.0

                is_active = rec.get('is_active', True)
                bg_color = QColor("#ffffff") if is_active else QColor("#ffcccc")

                def update_calc_item(col, val_str):
                    item = NumericItem(val_str)
                    item.setBackground(bg_color)
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                    pr_val = str(rec.get("pr_nmb", ""))
                    dt_val = rec.get("meas_dt", "")

                    # Ищем строку интерфейса, так как таблица может быть отсортирована пользователем
                    for ui_row in range(self.data_table.rowCount()):
                        if self.data_table.item(ui_row, 0).text() == pr_val and self.data_table.item(ui_row,
                                                                                                     1).text() == dt_val:
                            self.data_table.setItem(ui_row, col, item)
                            break

                update_calc_item(col_calc, f"{c_calc:.3f}")
                update_calc_item(col_dc, f"{dC:.3f}")
                update_calc_item(col_ddc, f"{ddc * 100:.2f}%")

                if is_active:
                    c_chem_active.append(c_chem)
                    c_calc_active.append(c_calc)
                    dc_active.append(dC)

            # Включаем сортировку ПОСЛЕ завершения всех обновлений ячеек
            self.data_table.setSortingEnabled(True)

            self._update_statistics(c_chem_active, c_calc_active, dc_active)
            self._update_plot()

        except Exception as e:
            print(f"Ошибка в perform_recalc(): {e}")

    def _update_statistics(self, c_chem, c_calc, dc):
        m = len(dc)

        if m < 2:
            for row in range(11): self.stats_table.item(row, 1).setText("-")
            for row in range(7, 11): self.stats_table.item(row, 1).setBackground(Qt.GlobalColor.white)
            return

        max_val, min_val = np.max(c_chem), np.min(c_chem)
        mean_dc = np.mean(dc)
        stdev_dc = np.std(dc, ddof=1)

        rel_mean = (mean_dc * 2) / (max_val + min_val) if (max_val + min_val) != 0 else 0
        rel_stdev = (stdev_dc * 2) / (max_val + min_val) if (max_val + min_val) != 0 else 0

        x, y = np.array(c_chem), np.array(c_calc)
        sum_xy = np.sum((x - np.mean(x)) * (y - np.mean(y)))
        sum_x2 = np.sum((x - np.mean(x)) ** 2)
        sum_y2 = np.sum((y - np.mean(y)) ** 2)
        r2 = ((sum_xy ** 2) / sum_x2) / sum_y2 if (sum_x2 != 0 and sum_y2 != 0) else 0

        t_calc = (abs(mean_dc) * np.sqrt(m)) / stdev_dc if stdev_dc != 0 else 0
        try:
            import scipy.stats as stats
            t_table = stats.t.ppf(0.975, m - 1)
            has_scipy = True
        except:
            t_table = 0.0
            has_scipy = False

        try:
            norm_stdev = float(self.norm_stdev_edit.text().replace(',', '.'))
        except:
            norm_stdev = 0.0

        if norm_stdev > 0:
            f_calc = (stdev_dc ** 2) / (norm_stdev ** 2)
            if has_scipy:
                try:
                    f_table = stats.f.ppf(0.95, m, m)
                except:
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
            c_chem_act, c_calc_act = [], []
            c_chem_exc, c_calc_exc = [], []

            col_chem = 2
            col_calc = 3

            for row in range(self.data_table.rowCount()):
                chem_item = self.data_table.item(row, col_chem)
                calc_item = self.data_table.item(row, col_calc)

                if chem_item and calc_item and chem_item.text() and calc_item.text():
                    try:
                        cv = float(chem_item.text())
                        ca = float(calc_item.text())
                        bg_color = chem_item.background().color()
                        if bg_color.name() != "#ffcccc":
                            c_chem_act.append(cv)
                            c_calc_act.append(ca)
                        else:
                            c_chem_exc.append(cv)
                            c_calc_exc.append(ca)
                    except ValueError:
                        pass

            if c_chem_act and c_calc_act:
                self.ax.scatter(c_chem_act, c_calc_act, alpha=0.6, color='tab:blue', label='Участвуют')
                min_v = min(min(c_chem_act), min(c_calc_act))
                max_v = max(max(c_chem_act), max(c_calc_act))
                self.ax.plot([min_v, max_v], [min_v, max_v], 'r--', label='Идеал', alpha=0.7)

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
# views/data/correction.py
import json
import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QSplitter, QMessageBox, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QTabWidget
)
from PySide6.QtGui import QColor
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


class CorrectionPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.raw_buffer = []
        self.current_meas_type = 0

        self.init_ui()

        self.combo_element.currentIndexChanged.connect(self.load_data)
        self.combo_meas_type.currentIndexChanged.connect(self.load_data)
        self.combo_model.currentIndexChanged.connect(self.load_data)

        if self.combo_element.count() > 0:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        title = QLabel("Корректировка (Калибровка, сдвиг, масштаб)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        main_splitter = QSplitter(Qt.Vertical)

        # === Верхняя часть ===
        top_widget = QWidget()
        top_layout = QHBoxLayout()

        left_top_group = QGroupBox("Результаты и управление")
        left_top_layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        self.btn_change_selection = QPushButton("Изменить выборку")
        self.btn_save_equation = QPushButton("Сохранить корректировку")
        self.btn_load_data = QPushButton("Выгрузка данных")

        self.btn_change_selection.clicked.connect(self.open_sample_dialog)
        self.btn_load_data.clicked.connect(self.load_data)
        self.btn_save_equation.clicked.connect(self.save_correction)

        btn_layout.addWidget(self.btn_change_selection)
        btn_layout.addWidget(self.btn_save_equation)
        btn_layout.addWidget(self.btn_load_data)
        btn_layout.addStretch()
        left_top_layout.addLayout(btn_layout)

        left_top_layout.addWidget(QLabel("Коэффициенты корректировки:"))
        self.coeff_table = QTableWidget(2, 3)
        self.coeff_table.setHorizontalHeaderLabels(["Коэффициент", "Значение", "Значимость"])
        self.coeff_table.verticalHeader().setVisible(False)
        self.coeff_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, name in enumerate(["K0 (Сдвиг)", "K1 (Масштаб)"]):
            item = QTableWidgetItem(name)
            item.setBackground(Qt.GlobalColor.lightGray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.coeff_table.setItem(row, 0, item)
            self.coeff_table.setItem(row, 1, QTableWidgetItem("0.0"))
            self.coeff_table.setItem(row, 2, QTableWidgetItem("0.0"))
        left_top_layout.addWidget(self.coeff_table)

        left_top_layout.addWidget(QLabel("Характеристики уравнения:"))
        self.stats_table = QTableWidget(3, 4)
        self.stats_table.setHorizontalHeaderLabels(["Параметр", "Без корр-ки", "После корр-ки", "Изменение"])
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        for row, label in enumerate(["СКО σ", "Отн. СКО", "Корреляция R²"]):
            item = QTableWidgetItem(label)
            item.setBackground(Qt.GlobalColor.lightGray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.stats_table.setItem(row, 0, item)
            for col in range(1, 4): self.stats_table.setItem(row, col, QTableWidgetItem("0.0"))
        left_top_layout.addWidget(self.stats_table)
        left_top_group.setLayout(left_top_layout)

        # --- Верхняя правая (График) ---
        right_top_group = QGroupBox("График зависимости C_хим от C_корр")
        right_top_layout = QVBoxLayout()
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.canvas = FigureCanvas(self.fig)
        self.canvas.mpl_connect('button_press_event', self.on_plot_double_click)
        right_top_layout.addWidget(self.canvas)
        right_top_group.setLayout(right_top_layout)

        top_layout.addWidget(left_top_group, 45)
        top_layout.addWidget(right_top_group, 55)
        top_widget.setLayout(top_layout)

        # === Нижняя часть ===
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
        main_splitter.setSizes([400, 300])
        layout.addWidget(main_splitter)
        self.setLayout(layout)

        self.ini_load_elements()

    def create_data_table(self):
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(["Продукт", "Время (ts)", "C_расч", "C_хим", "C_корр", "ΔC", "δC=|ΔC/C_хим|"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setSortingEnabled(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        return table

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
            QTimer.singleShot(0, self.perform_correction)

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
            cx, cy = rec.get('c_corr', None), rec.get('c_chem', None)
            if cx is not None and cy is not None:
                dist = ((cx - x) / x_range) ** 2 + ((cy - y) / y_range) ** 2
                if dist < min_dist: min_dist, closest_idx = dist, i

        if closest_idx != -1 and min_dist < 0.002:
            self.raw_buffer[closest_idx]['is_active'] = not self.raw_buffer[closest_idx]['is_active']
            QTimer.singleShot(0, self.perform_correction)

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
            mdl_nmb = self.combo_model.currentIndex() + 1
            el_set_row = self.db.fetch_one("SELECT * FROM el_set WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?",
                                           [pr_nmb, el_nmb, mdl_nmb])

            if el_set_row: self.current_meas_type = el_set_row["meas_type"]
            self.raw_buffer = self._fetch_c_data(sample_config, el_nmb, mdl_nmb)
            self.perform_correction()

        except Exception as e:
            print(f"Ошибка загрузки: {e}")

    def _fetch_c_data(self, sample_config, el_nmb, mdl_nmb):
        all_rows = []
        for cond in sample_config:
            pr_nmb = cond["product_id"]
            if pr_nmb <= 0: continue

            d_from = cond['date_from'].replace('-', '')
            d_to = cond['date_to'].replace('-', '')
            start_dt = f"{d_from} {cond['time_from']}"
            end_dt = f"{d_to} {cond['time_to']}"

            c_calc_col = f"c_{el_nmb:02d}"
            c_chem_col = f"c_chem_{el_nmb:02d}"

            query = f"""
                SELECT pr_nmb, timestamp, 
                       {c_calc_col} AS c_calc, 
                       {c_chem_col} AS c_chem
                FROM PR_MEAS
                WHERE timestamp BETWEEN ? AND ?
                AND pr_nmb = ? AND {c_chem_col} <> 0 AND mdl_nmb = ?
            """
            meas_index = self.combo_meas_type.currentIndex()
            if meas_index == 1:
                query += " AND meas_type = 0"
            elif meas_index == 2:
                query += " AND meas_type = 1"
            query += " ORDER BY timestamp DESC"

            try:
                rows = self.db.fetch_all(query, [start_dt, end_dt, pr_nmb, mdl_nmb])
                for r in rows:
                    r['is_active'] = True
                    ts = r.get("timestamp")
                    r['timestamp_str'] = ts.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts, 'strftime') else str(ts or "")
                all_rows.extend(rows)
            except Exception as e:
                print(f"Ошибка SQL: {e}")
        return all_rows

    def perform_correction(self):
        if not self.raw_buffer: return

        c_calc_active, c_chem_active = [], []
        for rec in self.raw_buffer:
            if rec.get('is_active', True):
                c_calc_active.append(rec.get("c_calc", 0))
                c_chem_active.append(rec.get("c_chem", 0))

        if len(c_calc_active) > 1:
            X = np.vstack([np.ones(len(c_calc_active)), c_calc_active]).T
            y = np.array(c_chem_active)
            XTX_pinv = np.linalg.pinv(X.T @ X)
            coeffs = XTX_pinv @ X.T @ y
            y_pred = X @ coeffs
            mse = np.sum((y - y_pred) ** 2) / max(len(y) - 2, 1)
            std_errs = np.sqrt(np.abs(np.diag(XTX_pinv)) * mse)
            with np.errstate(divide='ignore', invalid='ignore'):
                t_stats = np.where(std_errs != 0, np.abs(coeffs / std_errs), 0)
        else:
            coeffs, t_stats = [0.0, 1.0], [0.0, 0.0]

        for i in range(2):
            self.coeff_table.item(i, 1).setText(f"{coeffs[i]:.6g}")
            sig_item = self.coeff_table.item(i, 2)
            sig_item.setText(f"{t_stats[i]:.2f}")
            is_bad = (i == 0 and t_stats[i] < 0.000000001) or (i == 1 and t_stats[i] < 2.0)
            sig_item.setBackground(QColor("#FFCCCC") if is_bad else Qt.GlobalColor.white)

        k0, k1 = coeffs[0], coeffs[1]
        for rec in self.raw_buffer:
            c_chem = rec.get("c_chem", 0)
            c_calc = rec.get("c_calc", 0)
            c_corr = k0 + k1 * c_calc
            rec['c_corr'] = c_corr
            dc = c_corr - c_chem
            rec['dc'] = dc
            rec['ddc'] = abs(dc) / c_chem if c_chem != 0 else 0

        self._update_statistics()
        self._rebuild_tables_ui()
        self._update_plot()

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

            item_pr = QTableWidgetItem(str(rec.get("pr_nmb", "")))
            item_pr.setData(Qt.UserRole, buf_idx)
            item_pr.setFlags(item_pr.flags() & ~Qt.ItemFlag.ItemIsEditable)
            t_widget.setItem(row_idx, 0, item_pr)

            t_widget.setItem(row_idx, 1, self._create_readonly_item(rec.get("timestamp_str", "")))
            t_widget.setItem(row_idx, 2, self._create_readonly_item(fmt_num(rec.get("c_calc", 0)), True))
            t_widget.setItem(row_idx, 3, self._create_readonly_item(fmt_num(rec.get("c_chem", 0)), True))
            t_widget.setItem(row_idx, 4, self._create_readonly_item(fmt_num(rec.get("c_corr", 0)), True))
            t_widget.setItem(row_idx, 5, self._create_readonly_item(fmt_num(rec.get("dc", 0)), True))
            t_widget.setItem(row_idx, 6, self._create_readonly_item(f"{rec.get('ddc', 0) * 100:.2f}%", True))

            if is_act:
                act_idx += 1
            else:
                exc_idx += 1

        for t in [self.table_active, self.table_excluded]:
            t.setSortingEnabled(True)
            t.setUpdatesEnabled(True)
            t.blockSignals(False)

    def _update_statistics(self):
        c_chem_list, c_calc_list, c_corr_list = [], [], []
        for rec in self.raw_buffer:
            if rec.get('is_active', True):
                c_chem_list.append(rec.get("c_chem", 0))
                c_calc_list.append(rec.get("c_calc", 0))
                c_corr_list.append(rec.get("c_corr", 0))

        if not c_chem_list: return
        before_stats = self._calc_stats(c_chem_list, c_calc_list)
        after_stats = self._calc_stats(c_chem_list, c_corr_list)

        for row in range(3):
            val_before, val_after = before_stats[row], after_stats[row]
            val_delta = val_before - val_after
            if row == 1:
                self.stats_table.item(row, 1).setText(f"{val_before * 100:.2f}%")
                self.stats_table.item(row, 2).setText(f"{val_after * 100:.2f}%")
                self.stats_table.item(row, 3).setText(f"{val_delta * 100:.2f}%")
            elif row == 0:
                self.stats_table.item(row, 1).setText(f"{val_before:.4f}")
                self.stats_table.item(row, 2).setText(f"{val_after:.4f}")
                self.stats_table.item(row, 3).setText(f"{val_delta:.4f}")
            else:
                self.stats_table.item(row, 1).setText(f"{val_before:.2f}")
                self.stats_table.item(row, 2).setText(f"{val_after:.2f}")
                self.stats_table.item(row, 3).setText(f"{val_delta:.2f}")

    def _calc_stats(self, c_chem, c_pred):
        y_true, y_pred = np.array(c_chem), np.array(c_pred)
        dc = y_pred - y_true
        stdev_dc = np.std(dc, ddof=1) if len(dc) > 1 else 0.0
        max_val, min_val = np.max(y_true), np.min(y_true)
        rel_stdev = (stdev_dc * 2) / (max_val + min_val) if (max_val + min_val) != 0 else 0
        sum_xy = np.sum((y_true - np.mean(y_true)) * (y_pred - np.mean(y_pred)))
        sum_x2, sum_y2 = np.sum((y_true - np.mean(y_true)) ** 2), np.sum((y_pred - np.mean(y_pred)) ** 2)
        r2 = ((sum_xy ** 2) / sum_x2) / sum_y2 if (sum_x2 != 0 and sum_y2 != 0) else 0
        return [stdev_dc, rel_stdev, r2]

    def _update_plot(self):
        try:
            self.ax.clear()
            cx_act, cy_act, cx_exc, cy_exc = [], [], [], []
            for rec in self.raw_buffer:
                ca, cv = rec.get("c_chem"), rec.get("c_corr")
                if ca is not None and cv is not None:
                    if rec.get('is_active', True):
                        cx_act.append(cv); cy_act.append(ca)
                    else:
                        cx_exc.append(cv); cy_exc.append(ca)

            if cx_act and cy_act:
                self.ax.scatter(cx_act, cy_act, alpha=0.6, color='tab:blue', label='Участвуют')
                min_v, max_v = min(min(cx_act), min(cy_act)), max(max(cx_act), max(cy_act))
                self.ax.plot([min_v, max_v], [min_v, max_v], 'r--', label='Идеал', alpha=0.7)

            if cx_exc and cy_exc:
                self.ax.scatter(cx_exc, cy_exc, alpha=0.8, color='tab:red', marker='x', label='Исключены')

            if cx_act or cx_exc:
                self.ax.set_xlabel("C_корр")
                self.ax.set_ylabel("C_хим")
                self.ax.set_title("График зависимости C_хим от C_корр")
                self.ax.legend()
                self.ax.grid(True, alpha=0.3)
            self.canvas.draw()
        except Exception as e:
            print(f"Ошибка в _update_plot: {e}")

    def save_correction(self):
        try:
            if not self.raw_buffer:
                QMessageBox.warning(self, "Внимание", "Нет данных для сохранения. Сначала загрузите выборку.")
                return

            try:
                k0 = float(self.coeff_table.item(0, 1).text().replace(',', '.'))
                k1 = float(self.coeff_table.item(1, 1).text().replace(',', '.'))
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Некорректные значения коэффициентов K0 или K1.")
                return

            el_nmb = self.combo_element.currentData()
            mdl_nmb_current = self.combo_model.currentIndex() + 1
            default_pr_nmb = 1

            sample_path = get_config_path() / "sample" / "s_regress.json"
            if sample_path.exists():
                with open(sample_path, "r", encoding="utf-8") as f:
                    sample_config = json.load(f)
                    if sample_config: default_pr_nmb = sample_config[0].get("product_id", 1)

            if default_pr_nmb <= 0:
                QMessageBox.warning(self, "Ошибка", "Нельзя сохранить корректировку для 'Нет продукта'.")
                return

            dialog = SaveCorrectionDialog(default_pr=default_pr_nmb, default_mdl=mdl_nmb_current, parent=self)
            if not dialog.exec(): return

            try:
                target_products, target_models = dialog.get_data()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка ввода", str(e))
                return

            updated_count = 0
            for pr_nmb in target_products:
                for mdl_nmb in target_models:
                    row = self.db.fetch_one(
                        "SELECT meas_type FROM el_set WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?",
                        [pr_nmb, el_nmb, mdl_nmb])
                    if row:
                        prefix = "k_i_klin" if row["meas_type"] == 0 else "k_c_klin"
                        self.db.execute(
                            f"UPDATE el_set SET {prefix}00 = ?, {prefix}01 = ? WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?",
                            [k0, k1, pr_nmb, el_nmb, mdl_nmb])
                        updated_count += 1

            if updated_count > 0:
                QMessageBox.information(self, "Успех",
                                        f"Коэффициенты K0 и K1 успешно сохранены!\nОбновлено записей в базе: {updated_count}")
            else:
                QMessageBox.warning(self, "Внимание",
                                    "Не найдено записей в таблице el_set для выбранных продуктов и моделей.")

        except Exception as e:
            print("Ошибка при сохранении корректировки:", e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")


class SaveCorrectionDialog(QDialog):
    def __init__(self, default_pr="1", default_mdl="1", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сохранение коэффициентов K0, K1")
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
            if any(p <= 0 for p in pr_list): raise ValueError("Номера продуктов должны быть > 0.")
            if not pr_list or not mdl_list: raise ValueError("Поля продуктов и моделей не могут быть пустыми.")
            return pr_list, mdl_list
        except Exception:
            raise ValueError("Некорректный формат ввода.\nИспользуйте только числа, запятые и тире.")
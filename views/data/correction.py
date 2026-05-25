# views/data/correction.py
import json
import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QGroupBox, QSplitter, QMessageBox, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox  # <--- Добавили это
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from database.db import Database
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from views.data.sample_dialog import SampleDialog
from utils.path_manager import get_config_path


class CorrectionPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.raw_buffer = []
        self.current_meas_type = 0

        self.init_ui()

        # Подключаем обработчики изменения фильтров
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

        # --- Левая верхняя (Таблицы) ---
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

        # Таблица коэффициентов (K0, K1)
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

        # Таблица характеристик
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
            for col in range(1, 4):
                self.stats_table.setItem(row, col, QTableWidgetItem("0.0"))
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

        bottom_layout.addWidget(QLabel("Таблица выборки (Двойной клик исключает/возвращает строку):"))
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(7)
        self.data_table.setHorizontalHeaderLabels([
            "Продукт", "Дата/Время", "C_расч", "C_хим", "C_корр", "ΔC", "δC=|ΔC/C_хим|"
        ])
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.data_table.cellDoubleClicked.connect(self.on_table_double_click)
        self.data_table.horizontalHeader().sectionDoubleClicked.connect(self.sort_data_table)
        bottom_layout.addWidget(self.data_table)

        bottom_widget.setLayout(bottom_layout)
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([400, 300])
        layout.addWidget(main_splitter)
        self.setLayout(layout)

        self.ini_load_elements()

    # ================== ИСКЛЮЧЕНИЕ СТРОК (Как в регрессии) ==================
    def on_table_double_click(self, row, col):
        self.toggle_row_state(row)

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
            cx = rec.get('c_corr', None)  # По оси X у нас C_corr
            cy = rec.get('c_chem', None)  # По оси Y у нас C_chem
            if cx is not None and cy is not None:
                dist = ((cx - x) / x_range) ** 2 + ((cy - y) / y_range) ** 2
                if dist < min_dist:
                    min_dist, closest_idx = dist, i

        if closest_idx != -1 and min_dist < 0.002:
            self.toggle_row_state(closest_idx)

    def toggle_row_state(self, idx):
        if idx < 0 or idx >= len(self.raw_buffer): return
        self.raw_buffer[idx]['is_active'] = not self.raw_buffer[idx].get('is_active', True)
        self.raw_buffer.sort(key=lambda item: (not item.get('is_active', True), item.get('meas_dt', '')))

        self._update_data_table_from_buffer()
        self.perform_correction()

    def sort_data_table(self, logical_index):
        self.data_table.sortItems(logical_index, Qt.DescendingOrder)

    # ================== ЗАГРУЗКА ДАННЫХ ==================
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

            el_nmb = self.combo_element.currentData()
            mdl_nmb = self.combo_model.currentIndex() + 1  # 1, 2, 3

            # Получаем настройки элемента чтобы узнать meas_type (концентрации или интенсивности)
            pr_nmb = sample_config[0].get("product_id")
            el_set_row = self.db.fetch_one("SELECT * FROM el_set WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?",
                                           [pr_nmb, el_nmb, mdl_nmb])
            if el_set_row:
                self.current_meas_type = el_set_row["meas_type"]

            self.raw_buffer = self._fetch_c_data(sample_config, el_nmb, mdl_nmb)

            self._update_data_table_from_buffer()
            self.perform_correction()

        except Exception as e:
            print(f"Ошибка загрузки: {e}")

    def _fetch_c_data(self, sample_config, el_nmb, mdl_nmb):
        all_rows = []
        for cond in sample_config:
            pr_nmb = cond["product_id"]
            start_dt = f"{cond['date_from']} {cond['time_from']}"
            end_dt = f"{cond['date_to']} {cond['time_to']}"

            # В таблице PR_MEAS берем C_расч (c_0X) и C_хим (c_chem_0X)
            c_calc_col = f"c_{el_nmb:02d}"
            c_chem_col = f"c_chem_{el_nmb:02d}"

            query = f"""
                SELECT pr_nmb, meas_dt, timestamp, 
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
            query += " ORDER BY meas_dt, timestamp"

            try:
                rows = self.db.fetch_all(query, [start_dt, end_dt, pr_nmb, mdl_nmb])
                for r in rows:
                    r['is_active'] = True
                all_rows.extend(rows)
            except Exception as e:
                print(f"Ошибка SQL: {e}")

        return all_rows

    def _update_data_table_from_buffer(self):
        self.data_table.blockSignals(True)
        self.data_table.setRowCount(0)

        for row_idx, rec in enumerate(self.raw_buffer):
            self.data_table.insertRow(row_idx)
            is_active = rec.get('is_active', True)
            bg_color = QColor("#ffffff") if is_active else QColor("#ffcccc")

            def set_item(col, val):
                item = QTableWidgetItem(str(val))
                item.setBackground(bg_color)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.data_table.setItem(row_idx, col, item)

            set_item(0, rec.get("pr_nmb", ""))
            set_item(1, rec.get("meas_dt", ""))

            c_calc = rec.get("c_calc", 0)
            c_chem = rec.get("c_chem", 0)

            set_item(2, f"{c_calc:.3f}")
            set_item(3, f"{c_chem:.3f}")
            set_item(4, "")  # C_корр
            set_item(5, "")  # dC
            set_item(6, "")  # Отн погрешность

        self.data_table.blockSignals(False)

    # ================== РАСЧЕТ КОРРЕКТИРОВКИ ==================
    def perform_correction(self):
        if not self.raw_buffer: return

        # Собираем данные только для активных строк
        c_calc_active = []
        c_chem_active = []

        for rec in self.raw_buffer:
            if rec.get('is_active', True):
                c_calc_active.append(rec.get("c_calc", 0))
                c_chem_active.append(rec.get("c_chem", 0))

        if len(c_calc_active) > 1:
            X = np.vstack([np.ones(len(c_calc_active)), c_calc_active]).T
            y = np.array(c_chem_active)

            # Регрессия
            XTX_pinv = np.linalg.pinv(X.T @ X)
            coeffs = XTX_pinv @ X.T @ y  # [K0, K1]

            # Значимость
            y_pred = X @ coeffs
            mse = np.sum((y - y_pred) ** 2) / max(len(y) - 2, 1)
            std_errs = np.sqrt(np.abs(np.diag(XTX_pinv)) * mse)
            with np.errstate(divide='ignore', invalid='ignore'):
                t_stats = np.where(std_errs != 0, np.abs(coeffs / std_errs), 0)
        else:
            coeffs = [0.0, 1.0]  # Значения по умолчанию
            t_stats = [0.0, 0.0]

        # Заполняем таблицу коэффициентов
        for i in range(2):
            self.coeff_table.item(i, 1).setText(f"{coeffs[i]:.6g}")

            sig_item = self.coeff_table.item(i, 2)
            sig_item.setText(f"{t_stats[i]:.2f}")

            # Логика подсветки значимости из Excel: 
            # Для K0: < 0.000000001 (по сути 0) - красным
            # Для K1: < 2 - красным
            is_bad = False
            if i == 0 and t_stats[i] < 0.000000001: is_bad = True
            if i == 1 and t_stats[i] < 2.0: is_bad = True

            sig_item.setBackground(QColor("#FFCCCC") if is_bad else Qt.GlobalColor.white)

        # Применяем уравнение
        self.apply_correction(coeffs[0], coeffs[1])

        # Обновляем статистику и график
        self._update_statistics()
        self._update_plot()

    def apply_correction(self, k0, k1):
        for row_idx, rec in enumerate(self.raw_buffer):
            c_chem = rec.get("c_chem", 0)
            c_calc = rec.get("c_calc", 0)

            c_corr = k0 + k1 * c_calc
            rec['c_corr'] = c_corr  # Сохраняем для графика

            dc = c_corr - c_chem
            ddc = abs(dc) / c_chem if c_chem != 0 else 0

            is_active = rec.get('is_active', True)
            bg_color = QColor("#ffffff") if is_active else QColor("#ffcccc")

            def set_cell(col, text):
                item = QTableWidgetItem(text)
                item.setBackground(bg_color)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.data_table.setItem(row_idx, col, item)

            set_cell(4, f"{c_corr:.3f}")
            set_cell(5, f"{dc:.3f}")
            set_cell(6, f"{ddc * 100:.2f}%")

    def _update_statistics(self):
        c_chem_list = []
        c_calc_list = []
        c_corr_list = []

        for rec in self.raw_buffer:
            if rec.get('is_active', True):
                c_chem_list.append(rec.get("c_chem", 0))
                c_calc_list.append(rec.get("c_calc", 0))
                c_corr_list.append(rec.get("c_corr", 0))

        if not c_chem_list: return

        # Статистика "ДО" (используем c_calc)
        before_stats = self._calc_stats(c_chem_list, c_calc_list)
        # Статистика "ПОСЛЕ" (используем c_corr)
        after_stats = self._calc_stats(c_chem_list, c_corr_list)

        for row in range(3):
            val_before = before_stats[row]
            val_after = after_stats[row]
            val_delta = val_before - val_after

            if row == 1:  # Относительное СКО (%)
                self.stats_table.item(row, 1).setText(f"{val_before * 100:.2f}%")
                self.stats_table.item(row, 2).setText(f"{val_after * 100:.2f}%")
                self.stats_table.item(row, 3).setText(f"{val_delta * 100:.2f}%")
            elif row == 0:  # СКО (4 знака)
                self.stats_table.item(row, 1).setText(f"{val_before:.4f}")
                self.stats_table.item(row, 2).setText(f"{val_after:.4f}")
                self.stats_table.item(row, 3).setText(f"{val_delta:.4f}")
            else:  # R2 (2 знака)
                self.stats_table.item(row, 1).setText(f"{val_before:.2f}")
                self.stats_table.item(row, 2).setText(f"{val_after:.2f}")
                self.stats_table.item(row, 3).setText(f"{val_delta:.2f}")

    def _calc_stats(self, c_chem, c_pred):
        y_true = np.array(c_chem)
        y_pred = np.array(c_pred)

        dc = y_pred - y_true
        stdev_dc = np.std(dc, ddof=1) if len(dc) > 1 else 0.0

        max_val, min_val = np.max(y_true), np.min(y_true)
        rel_stdev = (stdev_dc * 2) / (max_val + min_val) if (max_val + min_val) != 0 else 0

        sum_xy = np.sum((y_true - np.mean(y_true)) * (y_pred - np.mean(y_pred)))
        sum_x2 = np.sum((y_true - np.mean(y_true)) ** 2)
        sum_y2 = np.sum((y_pred - np.mean(y_pred)) ** 2)
        r2 = ((sum_xy ** 2) / sum_x2) / sum_y2 if (sum_x2 != 0 and sum_y2 != 0) else 0

        return [stdev_dc, rel_stdev, r2]

    def _update_plot(self):
        try:
            self.ax.clear()
            cx_act, cy_act = [], []
            cx_exc, cy_exc = [], []

            for rec in self.raw_buffer:
                c_corr = rec.get("c_corr", 0)
                c_chem = rec.get("c_chem", 0)

                if rec.get('is_active', True):
                    cx_act.append(c_corr)
                    cy_act.append(c_chem)
                else:
                    cx_exc.append(c_corr)
                    cy_exc.append(c_chem)

            # Рисуем активные
            if cx_act and cy_act:
                self.ax.scatter(cx_act, cy_act, alpha=0.6, color='tab:blue', label='Участвуют')
                min_v = min(min(cx_act), min(cy_act))
                max_v = max(max(cx_act), max(cy_act))
                self.ax.plot([min_v, max_v], [min_v, max_v], 'r--', label='Идеал', alpha=0.7)

            # Рисуем исключенные
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
            if not hasattr(self, 'raw_buffer') or not self.raw_buffer:
                QMessageBox.warning(self, "Внимание", "Нет данных для сохранения. Сначала загрузите выборку.")
                return

            # Считываем коэффициенты K0 и K1 из таблицы
            try:
                k0 = float(self.coeff_table.item(0, 1).text().replace(',', '.'))
                k1 = float(self.coeff_table.item(1, 1).text().replace(',', '.'))
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Некорректные значения коэффициентов K0 или K1.")
                return

            # Вызываем диалог сохранения
            el_nmb = self.combo_element.currentData()
            mdl_nmb_current = self.combo_model.currentIndex() + 1

            # Пытаемся подтянуть продукт по умолчанию из файла выборки
            default_pr_nmb = 1
            sample_path = get_config_path() / "sample" / "s_regress.json"
            if sample_path.exists():
                try:
                    with open(sample_path, "r", encoding="utf-8") as f:
                        sample_config = json.load(f)
                        if sample_config:
                            default_pr_nmb = sample_config[0].get("product_id", 1)
                except Exception:
                    pass

            # Открываем окно для ввода продуктов и моделей
            dialog = SaveCorrectionDialog(default_pr=default_pr_nmb, default_mdl=mdl_nmb_current, parent=self)
            if not dialog.exec():
                return

            try:
                target_products, target_models = dialog.get_data()
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка ввода", str(e))
                return

            updated_count = 0

            # Цикл сохранения по базе данных с динамической проверкой meas_type
            for pr_nmb in target_products:
                for mdl_nmb in target_models:
                    # 1. Запрашиваем meas_type конкретно для этой пары Продукт/Модель из БД
                    row = self.db.fetch_one(
                        "SELECT meas_type FROM el_set WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?",
                        [pr_nmb, el_nmb, mdl_nmb]
                    )

                    if row:
                        local_meas_type = row["meas_type"]

                        # 2. Выбираем правильные столбцы
                        prefix = "k_i_klin" if local_meas_type == 0 else "k_c_klin"
                        col_k0 = f"{prefix}00"
                        col_k1 = f"{prefix}01"

                        # 3. Записываем коэффициенты в базу
                        query = f"UPDATE el_set SET {col_k0} = ?, {col_k1} = ? WHERE pr_nmb = ? AND el_nmb = ? AND mdl_nmb = ?"
                        self.db.execute(query, [k0, k1, pr_nmb, el_nmb, mdl_nmb])
                        updated_count += 1

            # Итоги операции
            if updated_count > 0:
                QMessageBox.information(self, "Успех",
                                        f"Коэффициенты K0 и K1 успешно сохранены!\n"
                                        f"Обновлено записей в базе: {updated_count}")
            else:
                QMessageBox.warning(self, "Внимание",
                                    "Не найдено записей в таблице el_set для выбранных продуктов и моделей.")

        except Exception as e:
            print("Ошибка при сохранении корректировки:", e)
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить:\n{e}")



class SaveCorrectionDialog(QDialog):
    """Диалоговое окно для выбора продуктов и моделей при сохранении коэффициентов"""

    def __init__(self, default_pr="1", default_mdl="1", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Сохранение коэффициентов K0, K1")
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
            raise ValueError("Некорректный формат ввода.\nИспользуйте только числа, запятые и тире.")
# views/data/compare_models.py
import json
import os
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QComboBox, QDateTimeEdit, QCheckBox, QMessageBox, QHeaderView,
    QSplitter, QGroupBox, QScrollArea
)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QColor, QFont
from database.db import Database
from utils.path_manager import get_config_path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


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

        v1 = to_float(self.text());
        v2 = to_float(other.text())
        if v1 is not None and v2 is not None: return v1 < v2
        if v1 is None and v2 is not None: return True
        if v1 is None and v2 is None: return False
        return super().__lt__(other)


class CompareModelsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.elements_config = []
        self.model_checkboxes = {}

        self.init_ui()
        self.load_elements_config()
        self.load_products()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        title = QLabel("Сравнение математических моделей")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Главный разделитель (Верх - Низ)
        main_splitter = QSplitter(Qt.Vertical)

        # --- ВЕРХНЯЯ ЧАСТЬ ---
        top_splitter = QSplitter(Qt.Horizontal)

        # 1. Зона управления (Слева)
        controls_group = QGroupBox("Управление и фильтры")
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(12)

        # Продукт и Элемент
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Продукт:"))
        self.combo_pr = QComboBox()
        row1.addWidget(self.combo_pr)
        row1.addWidget(QLabel("Элемент:"))
        self.combo_element = QComboBox()
        row1.addWidget(self.combo_element)
        controls_layout.addLayout(row1)

        # Даты
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("От:"))
        self.date_from = QDateTimeEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDateTime(QDateTime.currentDateTime().addDays(-1))
        row2.addWidget(self.date_from)

        row2.addWidget(QLabel("До:"))
        self.date_to = QDateTimeEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDateTime(QDateTime.currentDateTime().addDays(1))
        row2.addWidget(self.date_to)
        controls_layout.addLayout(row2)

        # Химия
        self.check_chem = QCheckBox("Только с наличием химии")
        self.check_chem.setChecked(False)  # По умолчанию снято
        controls_layout.addWidget(self.check_chem)

        # Галочки моделей (динамические)
        models_label = QLabel("Выберите модели для сравнения:")
        models_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        controls_layout.addWidget(models_label)

        self.models_layout = QVBoxLayout()

        # Оборачиваем галочки в ScrollArea на случай если моделей много
        scroll_models = QScrollArea()
        scroll_models.setWidgetResizable(True)
        scroll_models.setStyleSheet("QScrollArea { border: none; }")
        scroll_widget = QWidget()
        scroll_widget.setLayout(self.models_layout)
        scroll_models.setWidget(scroll_widget)

        controls_layout.addWidget(scroll_models)
        controls_group.setLayout(controls_layout)

        # 2. Зона графика (Справа)
        plot_group = QGroupBox("График концентраций")
        plot_layout = QVBoxLayout()
        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.canvas = FigureCanvas(self.fig)
        plot_layout.addWidget(self.canvas)
        plot_group.setLayout(plot_layout)

        top_splitter.addWidget(controls_group)
        top_splitter.addWidget(plot_group)
        top_splitter.setSizes([350, 650])  # Соотношение панелей

        # --- НИЖНЯЯ ЧАСТЬ ---
        table_group = QGroupBox("Сводная таблица (сгруппировано по времени)")
        table_layout = QVBoxLayout()
        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        table_layout.addWidget(self.table)
        table_group.setLayout(table_layout)

        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(table_group)
        main_splitter.setSizes([350, 400])

        main_layout.addWidget(main_splitter)

        # --- ПОДКЛЮЧЕНИЯ ---
        self.combo_pr.currentIndexChanged.connect(self.on_product_changed)
        self.combo_element.currentIndexChanged.connect(self.load_data)
        self.date_from.dateTimeChanged.connect(self.load_data)
        self.date_to.dateTimeChanged.connect(self.load_data)
        self.check_chem.stateChanged.connect(self.load_data)

    def load_elements_config(self):
        try:
            elements_path = get_config_path() / "elements.json"
            if os.path.exists(elements_path):
                with open(elements_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self.combo_element.blockSignals(True)
                self.combo_element.clear()

                valid_elements = [el for el in data if
                                  isinstance(el, dict) and el.get("name") and el.get("name") != "-"]
                valid_elements = sorted(valid_elements, key=lambda x: x.get('number', 0))

                for el in valid_elements:
                    self.combo_element.addItem(el["name"], el["number"])

                self.combo_element.blockSignals(False)
        except Exception as e:
            print(f"Ошибка загрузки элементов: {e}")

    def load_products(self):
        try:
            products = self.db.fetch_all("SELECT pr_nmb, pr_name FROM cfg02 WHERE pr_nmb > 0 ORDER BY pr_nmb")
            self.combo_pr.blockSignals(True)
            self.combo_pr.clear()
            for p in products:
                self.combo_pr.addItem(f"№{p['pr_nmb']}: {p['pr_name']}", p['pr_nmb'])
            self.combo_pr.blockSignals(False)

            # Вручную дергаем обновление моделей для первого продукта
            if products:
                self.on_product_changed()
        except Exception as e:
            print(f"Ошибка: {e}")

    def on_product_changed(self):
        pr_nmb = self.combo_pr.currentData()
        if not pr_nmb: return

        # ИСПРАВЛЕНИЕ 1: Полностью и правильно очищаем layout от старых виджетов и пружин
        while self.models_layout.count():
            item = self.models_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.model_checkboxes.clear()

        try:
            models = self.db.fetch_all("SELECT DISTINCT mdl_nmb FROM pr_meas WHERE pr_nmb = ? ORDER BY mdl_nmb",
                                       [pr_nmb])
            for m in models:
                mdl_idx = m['mdl_nmb']
                cb = QCheckBox(f"Модель {mdl_idx}")
                cb.setChecked(False)  # По умолчанию сняты
                cb.stateChanged.connect(self.load_data)

                self.models_layout.addWidget(cb)
                self.model_checkboxes[mdl_idx] = cb

            self.models_layout.addStretch()  # Добавляем пружину заново
        except Exception as e:
            print(f"Ошибка загрузки моделей: {e}")

        self.load_data()

    def load_data(self):
        """Главный метод получения и обработки данных"""
        pr_nmb = self.combo_pr.currentData()
        el_nmb = self.combo_element.currentData()
        selected_mdls = sorted([m for m, cb in self.model_checkboxes.items() if cb.isChecked()])

        if not pr_nmb or not el_nmb or not selected_mdls:
            self.table.setRowCount(0)
            self.ax.clear()
            self.canvas.draw()
            return

        dt_from = self.date_from.dateTime().toPython()
        dt_to = self.date_to.dateTime().toPython()

        chem_col = f"c_chem_{el_nmb:02d}"
        cor_col = f"c_cor_{el_nmb:02d}"

        placeholders = ','.join(['?'] * len(selected_mdls))

        # Берем ВСЕ данные без фильтра химии, чтобы база не "оторвала" модели друг от друга
        query = f"""
            SELECT pr_nmb, timestamp, sample_name, mdl_nmb, 
                   {cor_col} as corr, {chem_col} as chem 
            FROM pr_meas 
            WHERE pr_nmb = ? AND mdl_nmb IN ({placeholders}) 
            AND timestamp BETWEEN ? AND ? 
            ORDER BY timestamp DESC, mdl_nmb ASC
        """
        params = [pr_nmb] + selected_mdls + [dt_from, dt_to]

        try:
            rows = self.db.fetch_all(query, params)
            self._process_and_display(rows, selected_mdls)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", f"Сбой при загрузке данных: {e}")

    def _process_and_display(self, rows, selected_mdls):
        """Интеллектуально группирует данные и строит таблицу + график"""

        # 1. Умная группировка по timestamp (до 3 секунд разницы = одна проба)
        grouped_data = []
        current_group = None

        for r in rows:
            ts = r.get("timestamp")
            if not ts: continue

            chem_val = float(r.get('chem') or 0.0)
            cor_val = float(r.get('corr') or 0.0)
            mdl_nmb = r['mdl_nmb']

            if current_group is None:
                current_group = {
                    'base_ts': ts,
                    'display_time': ts.strftime("%Y-%m-%d %H:%M:%S"),
                    'pr_nmb': r.get('pr_nmb', ''),
                    'sample_name': r.get('sample_name', ''),
                    'c_chem': chem_val,
                    'models': {mdl_nmb: cor_val}
                }
                grouped_data.append(current_group)
            else:
                # Если разница во времени записи менее 3 секунд - это модели одного измерения
                delta = abs((current_group['base_ts'] - ts).total_seconds())
                if delta < 3.0:
                    # Сохраняем химию, если она есть хоть у одной модели в группе
                    if chem_val != 0.0:
                        current_group['c_chem'] = chem_val
                    current_group['models'][mdl_nmb] = cor_val
                else:
                    # Начинаем новую группу
                    current_group = {
                        'base_ts': ts,
                        'display_time': ts.strftime("%Y-%m-%d %H:%M:%S"),
                        'pr_nmb': r.get('pr_nmb', ''),
                        'sample_name': r.get('sample_name', ''),
                        'c_chem': chem_val,
                        'models': {mdl_nmb: cor_val}
                    }
                    grouped_data.append(current_group)

        # 2. Фильтрация на уровне Питона (после того, как мы склеили модели)
        if self.check_chem.isChecked():
            filtered_groups = [g for g in grouped_data if g['c_chem'] != 0.0]
        else:
            filtered_groups = grouped_data

        # 3. Отрисовка ТАБЛИЦЫ
        self.table.blockSignals(True)
        self.table.clear()

        headers = ["Продукт", "Время (ts)", "Название", "C_хим"]
        for m in selected_mdls:
            headers.extend([f"М{m} (расч)", f"М{m} (Δ)"])

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(filtered_groups))

        # filtered_groups уже отсортированы DESC, так как мы шли по SQL результату
        for row_idx, data in enumerate(filtered_groups):
            c_chem = data['c_chem']

            def add_cell(c, val, is_num=False, highlight=False):
                item = NumericItem(fmt_num(val)) if is_num else QTableWidgetItem(str(val))
                if is_num:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    item.setTextAlignment(Qt.AlignCenter)

                if highlight:
                    item.setBackground(QColor("#fef2f2"))
                else:
                    item.setBackground(QColor("#ffffff"))
                self.table.setItem(row_idx, c, item)

            add_cell(0, data['pr_nmb'])
            add_cell(1, data['display_time'])
            add_cell(2, data['sample_name'])

            if c_chem != 0.0:
                add_cell(3, c_chem, True, highlight=True)
            else:
                add_cell(3, "-")

            col = 4
            for m in selected_mdls:
                if m in data['models']:
                    c_cor = data['models'][m]
                    dc = c_cor - c_chem if c_chem != 0.0 else None

                    add_cell(col, c_cor, True)

                    if dc is not None:
                        add_cell(col + 1, dc, True)
                    else:
                        add_cell(col + 1, "-")
                else:
                    add_cell(col, "-")
                    add_cell(col + 1, "-")
                col += 2

        self.table.resizeColumnsToContents()
        self.table.blockSignals(False)

        # 4. Отрисовка ГРАФИКА
        self.ax.clear()

        # Для графика разворачиваем список, чтобы время шло слева направо (от старых к новым)
        plot_groups = list(reversed(filtered_groups))
        x_indices = range(len(plot_groups))

        y_chem = [g['c_chem'] if g['c_chem'] != 0.0 else np.nan for g in plot_groups]

        if not all(np.isnan(y_chem)):
            self.ax.plot(x_indices, y_chem, color='black', linestyle='--', marker='o', label='C_хим', linewidth=2)

        colors = ['tab:blue', 'tab:orange', 'tab:green', 'tab:red', 'tab:purple']

        for i, m in enumerate(selected_mdls):
            y_cor = [g['models'].get(m, np.nan) for g in plot_groups]
            color = colors[i % len(colors)]
            self.ax.plot(x_indices, y_cor, color=color, marker='s', label=f'Модель {m}')

        self.ax.set_title(f"Сравнение концентраций (Элемент: {self.combo_element.currentText()})")
        self.ax.set_xlabel("Измерения (хронологически)")
        self.ax.set_ylabel("Концентрация")

        if len(plot_groups) <= 20 and plot_groups:
            short_labels = [g['display_time'].split(' ')[1] for g in plot_groups]
            self.ax.set_xticks(x_indices)
            self.ax.set_xticklabels(short_labels, rotation=45, ha='right', fontsize=8)
        else:
            self.ax.set_xticks([])

        self.ax.grid(True, alpha=0.3)
        self.ax.legend()
        self.fig.tight_layout()
        self.canvas.draw()

    def refresh(self):
        # Вызывается при переходе на вкладку
        if self.combo_pr.count() == 0:
            self.load_products()
        else:
            self.load_data()
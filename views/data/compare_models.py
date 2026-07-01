# views/data/compare_models.py
import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QComboBox, QDateTimeEdit, QCheckBox, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QColor, QFont
from database.db import Database
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

        v1 = to_float(self.text());
        v2 = to_float(other.text())
        if v1 is not None and v2 is not None: return v1 < v2
        if v1 is None and v2 is not None: return True
        if v1 is not None and v2 is None: return False
        return super().__lt__(other)


class CompareModelsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.elements_config = []
        self.init_ui()
        self.setup_connections()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel("Сравнение математических моделей")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Продукт:"))
        self.combo_pr = QComboBox()
        self.combo_pr.setFixedWidth(200)
        filter_layout.addWidget(self.combo_pr)

        filter_layout.addWidget(QLabel("От:"))
        self.date_from = QDateTimeEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDateTime(QDateTime.currentDateTime().addDays(-1))
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("До:"))
        self.date_to = QDateTimeEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDateTime(QDateTime.currentDateTime().addDays(1))
        filter_layout.addWidget(self.date_to)

        self.check_chem = QCheckBox("Только с наличием химии")
        self.check_chem.setChecked(True)
        filter_layout.addWidget(self.check_chem)

        self.btn_load = QPushButton("Сравнить")
        self.btn_load.setStyleSheet("background-color: #e0f2fe; padding: 5px 15px;")
        filter_layout.addWidget(self.btn_load)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

    def setup_connections(self):
        self.btn_load.clicked.connect(self.load_data)

    def load_products(self):
        try:
            products = self.db.fetch_all("SELECT pr_nmb, pr_name FROM cfg02 WHERE pr_nmb > 0 ORDER BY pr_nmb")
            self.combo_pr.blockSignals(True)
            self.combo_pr.clear()
            for p in products: self.combo_pr.addItem(f"№{p['pr_nmb']}: {p['pr_name']}", p['pr_nmb'])
            self.combo_pr.blockSignals(False)
        except Exception as e:
            print(f"Ошибка: {e}")

    def load_elements_config(self):
        try:
            elements_path = get_config_path() / "elements.json"
            if os.path.exists(elements_path):
                with open(elements_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.elements_config = sorted(
                    [el for el in data if isinstance(el, dict) and el.get("name") and el.get("name") != "-"],
                    key=lambda x: x.get('number', 0))
        except Exception:
            self.elements_config = []

    def load_data(self):
        pr_nmb = self.combo_pr.currentData()
        if not pr_nmb: return
        self.load_elements_config()

        # Передаем QDateTime объекты напрямую
        dt_from = self.date_from.dateTime().toPython()
        dt_to = self.date_to.dateTime().toPython()

        db_cols = ["id", "timestamp", "sample_name", "mdl_nmb", "active_model"]
        for el in self.elements_config:
            db_cols.append(f"c_cor_{el['number']:02d}")
            db_cols.append(f"c_chem_{el['number']:02d}")

        query = f"SELECT {', '.join(db_cols)} FROM pr_meas WHERE pr_nmb = ? AND timestamp >= ? AND timestamp <= ?"
        params = [pr_nmb, dt_from, dt_to]

        if self.check_chem.isChecked():
            chem_conditions = [f"c_chem_{el['number']:02d} <> 0" for el in self.elements_config]
            if chem_conditions: query += f" AND ({' OR '.join(chem_conditions)})"

        query += " ORDER BY timestamp DESC, mdl_nmb ASC"

        try:
            rows = self.db.fetch_all(query, params)
            self._build_table(rows)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка БД", str(e))

    def _build_table(self, rows):
        self.table.blockSignals(True)
        self.table.clear()

        headers = ["Время (timestamp)", "Название", "Модель"]
        for el in self.elements_config: headers.extend(
            [f"{el['name']} (расч)", f"{el['name']} (хим)", f"{el['name']} (Δ)"])

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))

        color_active = QColor("#dcfce7")
        for row_idx, r in enumerate(rows):
            # Отображаем timestamp
            ts_val = r.get("timestamp")
            ts_str = ts_val.strftime("%Y-%m-%d %H:%M:%S") if hasattr(ts_val, 'strftime') else str(ts_val or "")

            row_color = color_active if r.get("active_model", 0) else QColor("#ffffff")

            def add_cell(c, val, is_num=False):
                item = NumericItem(fmt_num(val)) if is_num else QTableWidgetItem(str(val))
                item.setBackground(row_color)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter if is_num else Qt.AlignCenter)
                self.table.setItem(row_idx, c, item)

            add_cell(0, ts_str)
            add_cell(1, r.get("sample_name", ""))
            add_cell(2, f"Модель {r.get('mdl_nmb')}")

            col = 3
            for el in self.elements_config:
                nmb = el["number"]
                c_cor = float(r.get(f"c_cor_{nmb:02d}", 0.0))
                c_chem = float(r.get(f"c_chem_{nmb:02d}", 0.0))
                dc = c_cor - c_chem if c_chem != 0 else 0.0

                add_cell(col, c_cor, True)
                add_cell(col + 1, c_chem if c_chem != 0 else "-", True)
                add_cell(col + 2, dc if c_chem != 0 else "-", True)
                col += 3

        self.table.resizeColumnsToContents()
        self.table.blockSignals(False)

    def refresh(self):
        self.load_products()
        if self.combo_pr.count() > 0: self.load_data()
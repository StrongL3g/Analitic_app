from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QComboBox, QLabel,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from database.db import Database


class CfgMainPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.products = {}
        self.samplers = {}
        self.init_ui()
        self.refresh_references()
        self.load_config_for_ac()

    def init_ui(self):
        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Выберите прибор:"))
        self.ac_combo = QComboBox()
        self.ac_combo.setFixedWidth(300)
        self.ac_combo.blockSignals(True)
        top_layout.addWidget(self.ac_combo)

        self.save_btn = QPushButton("Сохранить всё")
        self.save_btn.setStyleSheet("background-color: #c8e6c9;")
        self.save_btn.clicked.connect(self.save_data)
        top_layout.addWidget(self.save_btn)
        layout.addLayout(top_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["№ Изм.", "Кювета", "Продукт", "Сэмплер", "Поток (1-6)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.ac_combo.blockSignals(False)
        self.ac_combo.currentIndexChanged.connect(self.load_config_for_ac)

    def refresh_references(self):
        analyzers = self.db.fetch_all("SELECT ac_nmb, ac_name, meas_nmb FROM cfg00 ORDER BY ac_nmb")
        self.ac_combo.clear()
        for ac in analyzers:
            self.ac_combo.addItem(f"№{ac['ac_nmb']} - {ac['ac_name']}", ac)

        pr_data = self.db.fetch_all("SELECT pr_nmb, pr_name FROM cfg02 ORDER BY pr_nmb")
        self.products = {-1: "--- Нет продукта ---"}
        self.products.update({p['pr_nmb']: p['pr_name'] for p in pr_data})

        sp_data = self.db.fetch_all("SELECT sp_nmb, sp_name FROM cfg04 ORDER BY sp_nmb")
        self.samplers = {-1: "--- Нет пробоотборника ---"}
        self.samplers.update({s['sp_nmb']: s['sp_name'] for s in sp_data})

    def _create_combo(self, items_dict, selected_id):
        combo = QComboBox()
        for id_val, name in items_dict.items():
            combo.addItem(f"{id_val}: {name}", id_val)
        idx = combo.findData(selected_id)
        combo.setCurrentIndex(idx if idx >= 0 else 0)
        return combo

    def load_config_for_ac(self):
        idx = self.ac_combo.currentIndex()
        if idx < 0: return
        ac_data = self.ac_combo.itemData(idx)
        ac_nmb = ac_data['ac_nmb']
        expected_meas = ac_data['meas_nmb'] or 0

        self.table.setRowCount(expected_meas)
        query = "SELECT meas_nmb, cuv_nmb, pr_nmb, sp_nmb, flow_array_nmb FROM cfg01 WHERE ac_nmb = ? ORDER BY meas_nmb"
        existing_rows = {r['meas_nmb']: r for r in self.db.fetch_all(query, (ac_nmb,))}

        for i in range(expected_meas):
            meas_idx = i + 1
            row_data = existing_rows.get(meas_idx)

            self.table.setItem(i, 0, QTableWidgetItem(str(meas_idx)))
            cuv = str(row_data['cuv_nmb']) if row_data else ("1" if meas_idx % 2 != 0 else "2")
            self.table.setItem(i, 1, QTableWidgetItem(cuv))

            # Просто создаем комбобоксы, без сигналов связи
            self.table.setCellWidget(i, 2,
                                     self._create_combo(self.products, row_data.get('pr_nmb', -1) if row_data else -1))
            self.table.setCellWidget(i, 3,
                                     self._create_combo(self.samplers, row_data.get('sp_nmb', -1) if row_data else -1))

            flow_combo = QComboBox()
            flow_combo.addItem("---", -1)
            for f in range(1, 7): flow_combo.addItem(str(f), f)

            if row_data and row_data['flow_array_nmb'] is not None and row_data['flow_array_nmb'] != -1:
                ui_flow = (row_data['flow_array_nmb'] % 6) + 1
                flow_combo.setCurrentIndex(flow_combo.findData(ui_flow))
            self.table.setCellWidget(i, 4, flow_combo)

    def save_data(self):
        ac_nmb = self.ac_combo.itemData(self.ac_combo.currentIndex())['ac_nmb']
        try:
            self.db.execute("DELETE FROM cfg01 WHERE ac_nmb = ?", (ac_nmb,))
            for i in range(self.table.rowCount()):
                meas_nmb = int(self.table.item(i, 0).text())
                cuv = int(self.table.item(i, 1).text())

                pr = self.table.cellWidget(i, 2).currentData()
                sp = self.table.cellWidget(i, 3).currentData()
                ui_flow = self.table.cellWidget(i, 4).currentData()

                # ЛОГИКА ПРОВЕРКИ ПРИ СОХРАНЕНИИ:
                # Если хоть что-то из трех выбрано как "пусто" (-1),
                # принудительно ставим все в -1 в базе
                if pr == -1 or sp == -1 or ui_flow == -1:
                    db_flow = -1
                    pr = -1
                    sp = -1
                else:
                    db_flow = (ui_flow - 1) + (6 if cuv == 2 else 0)

                self.db.execute(
                    "INSERT INTO cfg01 (meas_nmb, cuv_nmb, pr_nmb, sp_nmb, ac_nmb, flow_array_nmb) VALUES (?,?,?,?,?,?)",
                    (meas_nmb, cuv, pr, sp, ac_nmb, db_flow))
            QMessageBox.information(self, "Успех", "Сохранено!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))
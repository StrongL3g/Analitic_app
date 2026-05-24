from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QComboBox, QLabel,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from database.db import Database


class CfgMainPage(QWidget):
    """Главный конфигуратор последовательности измерений (Таблица cfg01)"""

    # В класс CfgMainPage добавить:
    def refresh(self):
        """Метод для обновления данных при входе на страницу"""
        self.refresh_references()
        self.load_config_for_ac()


    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.products = {}  # {id: name}
        self.samplers = {}  # {id: name}

        self.init_ui()
        # КРИТИЧНО: Сначала грузим справочники, потом всё остальное
        self.refresh_references()
        # После загрузки справочников вызываем загрузку таблицы для первого прибора
        self.load_config_for_ac()

    def init_ui(self):
        layout = QVBoxLayout(self)

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Выберите прибор:"))
        self.ac_combo = QComboBox()
        self.ac_combo.setFixedWidth(300)
        # Отключаем сигнал на время инициализации, чтобы не было лишних вызовов
        self.ac_combo.blockSignals(True)
        top_layout.addWidget(self.ac_combo)

        top_layout.addStretch()

        self.gen_btn = QPushButton("Сгенерировать по умолчанию")
        self.gen_btn.clicked.connect(self.generate_default_mapping)
        top_layout.addWidget(self.gen_btn)

        self.save_btn = QPushButton("Сохранить всё")
        self.save_btn.setStyleSheet("background-color: #c8e6c9;")
        self.save_btn.clicked.connect(self.save_data)
        top_layout.addWidget(self.save_btn)

        layout.addLayout(top_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "№ Измерения", "Кювета (1/2)", "Продукт (PR)", "Пробоотборник (SP)"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        # Включаем сигнал обратно
        self.ac_combo.blockSignals(False)
        self.ac_combo.currentIndexChanged.connect(self.load_config_for_ac)

    def refresh_references(self):
        """Загружает актуальные списки из БД"""
        try:
            # 1. Приборы
            analyzers = self.db.fetch_all("SELECT ac_nmb, ac_name, meas_nmb FROM cfg00 ORDER BY ac_nmb")
            self.ac_combo.blockSignals(True)
            self.ac_combo.clear()
            for ac in analyzers:
                self.ac_combo.addItem(f"№{ac['ac_nmb']} - {ac['ac_name']}", ac)
            self.ac_combo.blockSignals(False)

            # 2. Продукты
            pr_data = self.db.fetch_all("SELECT pr_nmb, pr_name FROM cfg02 ORDER BY pr_nmb")
            self.products = {p['pr_nmb']: p['pr_name'] for p in pr_data}

            # 3. Сэмплеры
            sp_data = self.db.fetch_all("SELECT sp_nmb, sp_name FROM cfg04 ORDER BY sp_nmb")
            self.samplers = {s['sp_nmb']: s['sp_name'] for s in sp_data}

            print(f"Справочники загружены: PR={len(self.products)}, SP={len(self.samplers)}")
        except Exception as e:
            print(f"Ошибка загрузки справочников: {e}")

    def load_config_for_ac(self):
        """Загружает конфигурацию для выбранного прибора"""
        idx = self.ac_combo.currentIndex()
        if idx < 0: return

        ac_data = self.ac_combo.itemData(idx)
        ac_nmb = ac_data['ac_nmb']
        expected_meas = ac_data['meas_nmb'] or 0

        self.table.setRowCount(0)
        self.table.setRowCount(expected_meas)

        try:
            query = "SELECT meas_nmb, cuv_nmb, pr_nmb, sp_nmb FROM cfg01 WHERE ac_nmb = ? ORDER BY meas_nmb"
            existing_rows = self.db.fetch_all(query, (ac_nmb,))
            config_map = {r['meas_nmb']: r for r in existing_rows}

            for i in range(expected_meas):
                meas_idx = i + 1
                row_data = config_map.get(meas_idx)

                # 1. Номер (ReadOnly)
                item_meas = QTableWidgetItem(str(meas_idx))
                item_meas.setFlags(item_meas.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, 0, item_meas)

                # 2. Кювета
                cuv_val = str(row_data['cuv_nmb']) if row_data else ("1" if meas_idx % 2 != 0 else "2")
                self.table.setItem(i, 1, QTableWidgetItem(cuv_val))

                # 3. Продукты (ComboBox)
                pr_combo = QComboBox()
                for p_id, p_name in self.products.items():
                    pr_combo.addItem(f"{p_id}: {p_name}", p_id)

                # Если в БД уже есть значение, выбираем его
                if row_data and row_data['pr_nmb'] in self.products:
                    pr_combo.setCurrentIndex(pr_combo.findData(row_data['pr_nmb']))
                else:
                    pr_combo.setCurrentIndex(0)  # Ставим первый по списку, чтобы не было NULL

                self.table.setCellWidget(i, 2, pr_combo)

                # 4. Сэмплеры (ComboBox)
                sp_combo = QComboBox()
                for s_id, s_name in self.samplers.items():
                    sp_combo.addItem(f"{s_id}: {s_name}", s_id)

                if row_data and row_data['sp_nmb'] in self.samplers:
                    sp_combo.setCurrentIndex(sp_combo.findData(row_data['sp_nmb']))
                else:
                    sp_combo.setCurrentIndex(0)

                self.table.setCellWidget(i, 3, sp_combo)

        except Exception as e:
            print(f"Ошибка заполнения таблицы: {e}")

    def generate_default_mapping(self):
        """Автозаполнение по твоей схеме"""
        for i in range(self.table.rowCount()):
            meas_nmb = i + 1
            # Кюветы 1-2-1-2
            self.table.item(i, 1).setText("1" if meas_nmb % 2 != 0 else "2")

            # Продукты и сэмплеры (пробуем сопоставить ID с номером измерения)
            for col in [2, 3]:
                combo = self.table.cellWidget(i, col)
                if combo:
                    idx = combo.findData(meas_nmb)
                    combo.setCurrentIndex(idx if idx >= 0 else 0)

    def save_data(self):
        """Сохранение с защитой от NULL"""
        idx = self.ac_combo.currentIndex()
        if idx < 0: return
        ac_nmb = self.ac_combo.itemData(idx)['ac_nmb']

        try:
            self.db.execute("DELETE FROM cfg01 WHERE ac_nmb = ?", (ac_nmb,))

            for i in range(self.table.rowCount()):
                meas_nmb = int(self.table.item(i, 0).text())

                cuv_text = self.table.item(i, 1).text()
                cuv_nmb = int(cuv_text) if cuv_text.isdigit() else 1

                pr_nmb = self.table.cellWidget(i, 2).currentData()
                sp_nmb = self.table.cellWidget(i, 3).currentData()

                # Валидация перед отправкой в БД
                if pr_nmb is None or sp_nmb is None:
                    # Если данных нет (справочник пуст), берем 1 как заглушку,
                    # чтобы не падал SQL, но лучше предупредить пользователя
                    pr_nmb = pr_nmb if pr_nmb is not None else 1
                    sp_nmb = sp_nmb if sp_nmb is not None else 1

                query = "INSERT INTO cfg01 (meas_nmb, cuv_nmb, pr_nmb, sp_nmb, ac_nmb) VALUES (?, ?, ?, ?, ?)"
                self.db.execute(query, (meas_nmb, cuv_nmb, pr_nmb, sp_nmb, ac_nmb))

            QMessageBox.information(self, "Успех", "Конфигурация сохранена!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")
# views/data/regression.py
import json
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QLineEdit, QGroupBox, QSplitter, QTabWidget,
    QMessageBox
)
from PySide6.QtCore import Qt
from database.db import Database
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from views.data.sample_dialog import SampleDialog

class RegressionPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.current_sample = []
        self.current_element = None
        self.current_meas_type = 0  # 0 - по интенсивностям, 1 - по концентрациям
        self.init_ui()

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

        # === Таблица коэффициентов ===
        left_top_layout.addWidget(QLabel("Сводная таблица коэффициентов:"))
        self.coeff_table = QTableWidget()
        self.coeff_table.setRowCount(6)  # A0–A5 → 6 строк
        self.coeff_table.setColumnCount(4)
        self.coeff_table.setHorizontalHeaderLabels(["Коэффициент", "Множитель", "Значение", "Значимость"])
        self.coeff_table.verticalHeader().setVisible(False)  # ← скрываем вертикальные заголовки

        # Заполняем первый столбец именами коэффициентов + стилизуем
        gray_bg = "#f0f0f0"
        for row, name in enumerate(["A0", "A1", "A2", "A3", "A4", "A5"]):
            item = QTableWidgetItem(name)
            item.setBackground(Qt.GlobalColor.lightGray)  # или QColor(gray_bg)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # только для чтения
            self.coeff_table.setItem(row, 0, item)

        left_top_layout.addWidget(self.coeff_table)

        # === Таблица характеристик уравнения ===
        left_top_layout.addWidget(QLabel("Характеристики уравнения:"))
        self.stats_table = QTableWidget()
        self.stats_table.setRowCount(6)
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        self.stats_table.verticalHeader().setVisible(False)

        # Параметры в первом столбце
        stats_labels = [
            "СКО σ",
            "Отн. СКО",
            "Смин",
            "Смакс",
            "Ссред",
            "Корреляция R²"
        ]

        for row, label in enumerate(stats_labels):
            item = QTableWidgetItem(label)
            item.setBackground(Qt.GlobalColor.lightGray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.stats_table.setItem(row, 0, item)

        left_top_layout.addWidget(self.stats_table)

        left_top_group.setLayout(left_top_layout)

        # === Верхняя правая часть (график) ===
        right_top_group = QGroupBox("График зависимости C_хим от C_расч")
        right_top_layout = QVBoxLayout()

        # Создаем график
        self.fig, self.ax = plt.subplots(figsize=(5, 4))
        self.canvas = FigureCanvas(self.fig)
        right_top_layout.addWidget(self.canvas)

        right_top_group.setLayout(right_top_layout)

        # Добавляем левую и правую части в верхний layout
        top_layout.addWidget(left_top_group, 40)
        top_layout.addWidget(right_top_group, 60)
        top_widget.setLayout(top_layout)

        # === Нижняя часть ===
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()

        # Комбо-боксы
        combo_layout = QHBoxLayout()

        # Комбобокс элемента
        self.combo_element = QComboBox()
        combo_layout.addWidget(QLabel("Элемент:"))
        combo_layout.addWidget(self.combo_element)

        # Комбобокс проб
        self.combo_meas_type = QComboBox()
        self.combo_meas_type.addItems(["Все пробы", "Ручные", "Цикл"])
        combo_layout.addWidget(QLabel("Пробы:"))
        combo_layout.addWidget(self.combo_meas_type)

        # 5 комбо-боксов для членов уравнения
        self.combo_equation_terms = []
        combo_layout.addWidget(QLabel("Члены уравнения:"))
        for i in range(5):
            combo = QComboBox()
            self.combo_equation_terms.append(combo)
            combo_layout.addWidget(combo)

        combo_layout.addStretch()
        bottom_layout.addLayout(combo_layout)

        # Таблица выборки
        bottom_layout.addWidget(QLabel("Таблица выборки:"))
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(11)
        self.data_table.setHorizontalHeaderLabels([
            "Продукт", "Дата/Время", "", "",
            "", "", "", "C_хим", "C_расч", "ΔC", "δC=|ΔC/C_хим|"
        ])
        bottom_layout.addWidget(self.data_table)

        bottom_widget.setLayout(bottom_layout)

        # === Объединяем все части ===
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([400, 300])

        layout.addWidget(main_splitter)
        self.setLayout(layout)

        # Загружаем начальные данные
        self.ini_load_elements()
        self.combo_element.currentIndexChanged.connect(self.load_data)
        self.combo_meas_type.currentIndexChanged.connect(self.load_data)

        # запускаем выгрузку данных по текущим параметра json файла выбоки
        self.load_data()

    def ini_load_elements(self):
        """Загрузка элементов из JSON файла"""
        try:
            elements_path = "config/elements.json"
            if os.path.exists(elements_path):
                with open(elements_path, "r", encoding="utf-8") as f:
                    elements_data = json.load(f)

                # Фильтруем только элементы без "-"
                valid_elements = [elem for elem in elements_data if elem.get("name") != "-"]

                self.combo_element.clear()
                for elem in valid_elements:
                    self.combo_element.addItem(elem["name"], elem["number"])

                print(f"Загружено элементов: {len(valid_elements)}")
            else:
                print("Файл elements.json не найден")
                # Заполняем тестовыми данными
                self.combo_element.addItems(["Cu", "Ni", "Fe", "ТФ"])

        except Exception as e:
            print(f"Ошибка загрузки элементов: {e}")
            self.combo_element.addItems(["Cu", "Ni", "Fe", "ТФ"])

    def open_sample_dialog(self):
        """Открывает диалог формирования выборки"""
        dialog = SampleDialog(self.db, self)
        if dialog.exec():
            print(f"Получена выборка: {len(self.current_sample)} строк")
            self.load_data()

    def load_data(self):
        """Выгрузка параметров, данных и начального уравнения → буфер"""
        try:
            # 1. Загружаем параметры выборки (config/sample/s_regress.json)
            sample_path = "config/sample/s_regress.json"
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
                QMessageBox.critical(self, "Ошибка", "В выборке отсутствует product_id")
                return

            # 2. Получаем el_nmb из UI
            el_nmb = self.combo_element.currentData()  # original_number, например 1 → Cu
            if el_nmb is None:
                QMessageBox.warning(self, "Ошибка", "Сначала выберите элемент")
                return

            # 3. Запрашиваем PR_SET: meas_type + начальное уравнение
            query_pr_set = """
                SELECT *
                FROM PR_SET
                WHERE pr_nmb = ? AND el_nmb = ? AND active_model = 1
            """
            pr_set_row = self.db.fetch_one(query_pr_set, [pr_nmb, el_nmb])
            if not pr_set_row:
                QMessageBox.critical(self, "Ошибка",
                                    f"Не найдена активная градуировка:\npr_nmb={pr_nmb}, el_nmb={el_nmb}")
                return

            meas_type = pr_set_row["meas_type"]
            self.current_meas_type = meas_type
            print(f"✅ PR_SET: pr_nmb={pr_nmb}, el_nmb={el_nmb}, meas_type={meas_type}")

            # 4. Заполняем 5 комбобоксов членами уравнения
            self._load_equation_terms(meas_type, el_nmb)

            # 5. Выгружаем данные из PR_MEAS → raw_buffer
            self.raw_buffer = self._fetch_pr_meas_data(sample_config, el_nmb, meas_type)
            print(f"📥 Получено строк: {len(self.raw_buffer)}")
            if not self.raw_buffer:
                QMessageBox.warning(self, "Информация", "По условиям выборки данных не найдено.")
                self.clear_tables()
                return

            # 6. Подгружаем НАЧАЛЬНОЕ уравнение из PR_SET в UI
            #self._apply_initial_equation(pr_set_row)

            # 7. Обновляем таблицу данных (только базовые колонки)
            self._update_data_table_from_buffer()

            QMessageBox.information(self, "Готово", f"Буфер загружен: {len(self.raw_buffer)} записей")

        except Exception as e:
            import traceback
            print("❌ Ошибка в load_data():")
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"load_data() провалился:\n{str(e)}")

    def _load_equation_terms(self, meas_type, el_nmb):
        """Заполняет 5 комбобоксов на основе meas_type и el_nmb"""
        try:
            json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
            json_path = f"config/{json_file}"

            if not os.path.exists(json_path):
                print(f"❌ {json_path} не найден")
                terms_list = []
            else:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                terms_list = []
                if meas_type == 0:
                    # lines: единый список interactions
                    interactions = data.get("interactions", [])
                    terms_list = [term["description"] for term in interactions
                                if term.get("description") and term["description"].strip()]
                else:
                    # elements: ищем по element_original_number
                    for group in data.get("interactions", []):
                        if group.get("element_original_number") == el_nmb:
                            interactions = group.get("interactions", [])
                            terms_list = [term["description"] for term in interactions
                                        if term.get("description") and term["description"].strip()]
                            break

            for combo in self.combo_equation_terms:
                combo.clear()
                combo.addItem("")
                combo.addItems(terms_list)
                combo.setPlaceholderText("Член уравнения")

        except Exception as e:
            print(f"❌ Ошибка в _load_equation_terms: {e}")
            for combo in self.combo_equation_terms:
                combo.clear()
                combo.addItem("")

    def _fetch_pr_meas_data(self, sample_config, el_nmb, meas_type):
        """Возвращает list[dict] — буфер данных из PR_MEAS"""
        all_rows = []

        for cond in sample_config:
            pr_nmb = cond["product_id"]
            start_dt = f"{cond['date_from']} {cond['time_from']}"
            end_dt = f"{cond['date_to']} {cond['time_to']}"

            # Базовые колонки
            cols = ["pr_nmb", "meas_dt"]
            # Добавляем i_00_00..i_00_19 или c_cor_01..c_cor_08
            if meas_type == 0:
                cols.extend([f"i_00_{i:02d}" for i in range(20)])  # i_00_00 … i_00_19
            else:
                cols.extend([f"c_cor_{i:02d}" for i in range(1, 9)])  # c_cor_01 … c_cor_08

            # Целевая переменная: c_chem_0{el_nmb}
            chem_col = f"c_chem_0{el_nmb}"
            cor_col = f"c_cor_0{el_nmb}"
            cols.extend([chem_col, cor_col])

            # Формируем SELECT
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
                AND pr_nmb = ?
                AND {chem_col} <> 0
                AND active_model = 1
            """
            # Добавляем фильтр по meas_type, если выбрано не «Все пробы»
            meas_index = self.combo_meas_type.currentIndex()
            if meas_index == 1:  # Ручные → meas_type=0
                query += " AND meas_type = 0"
            elif meas_index == 2:  # Цикл → meas_type=1
                query += " AND meas_type = 1"

            query += " ORDER BY meas_dt, timestamp"

            try:
                rows = self.db.fetch_all(query, [start_dt, end_dt, pr_nmb])
                all_rows.extend(rows)
            except Exception as e:
                print(f"⚠️ Ошибка запроса для pr_nmb={pr_nmb}: {e}")

        return all_rows

    def _apply_initial_equation(self, row):
        """Подгружает начальное уравнение из PR_SET в таблицы и комбобоксы"""
        # Сопоставление: coeff_table[row] ↔ A0..A5
        coeff_map = [
            ("k_i_klin00", "k_c_klin00"),  # A0
            ("k_i_klin01", "k_c_klin01"),  # A1
            ("k_i_alin01", "k_c_alin01"),  # A2
            ("k_i_alin02", "k_c_alin02"),  # A3
            ("k_i_alin03", "k_c_alin03"),  # A4
            ("k_i_alin04", "k_c_alin04"),  # A5
        ]
        operand_map = [
            ("operand_i_01_01", "operand_i_02_01", "operator_i_01"),  # член 1
            ("operand_i_01_02", "operand_i_02_02", "operator_i_02"),  # член 2
            ("operand_i_01_03", "operand_i_02_03", "operator_i_03"),  # член 3
            ("operand_i_01_04", "operand_i_02_04", "operator_i_04"),  # член 4
            ("operand_i_01_05", "operand_i_02_05", "operator_i_05"),  # член 5
        ]

        # 1. Коэффициенты (A0..A5)
        for i, (k_i, k_c) in enumerate(coeff_map):
            k_val = row.get(k_i) or row.get(k_c) or 0.0
            item = QTableWidgetItem(str(k_val))
            self.coeff_table.setItem(i, 2, item)  # колонка "Значение"

        # 2. Множители (члены уравнения) — пока пусто (нужно lookup в JSON)
        # Пока оставим как "-", как в Excel
        for i in range(1, 6):  # A1..A5
            item = QTableWidgetItem("-")
            self.coeff_table.setItem(i, 1, item)

        # 3. Заполняем 5 комбобоксов — из PR_SET (если есть описание)
        # (пока упрощённо: оставим пустыми — позже сделаем lookup по (x1,x2,op))
        for i, combo in enumerate(self.combo_equation_terms):
            combo.setCurrentIndex(0)  # сброс в пустой

    def _update_data_table_from_buffer(self):
        """Заполняет data_table из self.raw_buffer (базовые колонки)"""
        self.data_table.setRowCount(0)
        if not self.raw_buffer:
            return

        self.data_table.setRowCount(len(self.raw_buffer))
        for row_idx, rec in enumerate(self.raw_buffer):
            # G: Продукт
            self.data_table.setItem(row_idx, 0, QTableWidgetItem(str(rec.get("pr_nmb", ""))))
            # H: Дата/Время
            dt = rec.get("meas_dt", "")
            self.data_table.setItem(row_idx, 1, QTableWidgetItem(str(dt)))
            # N: C_хим = c_chem_0X
            el_nmb = self.combo_element.currentData()
            c_chem = rec.get(f"c_chem_0{el_nmb}", "")
            self.data_table.setItem(row_idx, 7, QTableWidgetItem(str(c_chem)))
            # O: C_расч = c_cor_0X (начальное приближение)
            c_cor = rec.get(f"c_cor_0{el_nmb}", "")
            self.data_table.setItem(row_idx, 8, QTableWidgetItem(str(c_cor)))
            # P: ΔC = dc
            dc = rec.get("dc", "")
            self.data_table.setItem(row_idx, 9, QTableWidgetItem(str(dc)))
            # Q: δC = ddc
            ddc = rec.get("ddc", "")
            self.data_table.setItem(row_idx, 10, QTableWidgetItem(str(ddc)))

    def start_regress(self):
        print("Процедура регрессии...")

        # TODO: Реализовать работу с данными
        QMessageBox.information(self, "Info", "Расчет регрессии будет реализована в следующей итерации")

    def save_equation(self):
        """Сохранение уравнения - заглушка"""
        print("Сохранение уравнения...")
        QMessageBox.information(self, "Info", "Сохранение уравнения будет реализовано позже")

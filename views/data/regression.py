# views/data/regression.py
import json
import os
import numpy as np
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

        # === Таблица коэффициентов ===
        left_top_layout.addWidget(QLabel("Сводная таблица коэффициентов:"))
        self.coeff_table = QTableWidget()
        self.coeff_table.setRowCount(6)  # A0–A5 → 6 строк
        self.coeff_table.setColumnCount(4)
        self.coeff_table.setHorizontalHeaderLabels(["Коэффициент", "Множитель", "Значение", "Значимость"])
        self.coeff_table.verticalHeader().setVisible(False)

        # Заполняем имена коэффициентов
        gray_bg = "#f0f0f0"
        for row, name in enumerate(["A0", "A1", "A2", "A3", "A4", "A5"]):
            # Имя коэффициента
            item = QTableWidgetItem(name)
            item.setBackground(Qt.GlobalColor.lightGray)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.coeff_table.setItem(row, 0, item)

            # ★ Инициализация столбца множителей
            multiplier_item = QTableWidgetItem("-")
            multiplier_item.setFlags(multiplier_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.coeff_table.setItem(row, 1, multiplier_item)

            # Значение
            value_item = QTableWidgetItem("0.0")
            self.coeff_table.setItem(row, 2, value_item)

            # Значимость
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
            "Продукт", "Дата/Время", "X1", "X2", "X3", "X4", "X5",
            "C_хим", "C_расч", "ΔC", "δC=|ΔC/C_хим|"
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

    def ini_load_elements(self):
        """Загрузка элементов из JSON файла"""
        try:
            elements_path = get_config_path() / "elements.json"
            if os.path.exists(elements_path):
                with open(elements_path, "r", encoding="utf-8") as f:
                    elements_data = json.load(f)

                valid_elements = [elem for elem in elements_data if elem.get("name") != "-"]

                self.combo_element.clear()
                for elem in valid_elements:
                    self.combo_element.addItem(elem["name"], elem["number"])

                print(f"Загружено элементов: {len(valid_elements)}")
            else:
                print("Файл elements.json не найден")
                self.combo_element.addItems(["Cu", "Ni", "Fe", "ТФ"])

        except Exception as e:
            print(f"Ошибка загрузки элементов: {e}")
            self.combo_element.addItems(["Cu", "Ni", "Fe", "ТФ"])

    def _reset_coefficients(self):
        """Сброс коэффициентов к нулевым значениям"""
        for i in range(6):
            value_item = self.coeff_table.item(i, 2)
            if value_item:
                value_item.setText("0.0")

            significance_item = self.coeff_table.item(i, 3)
            if significance_item:
                significance_item.setText("0.0")

        # Сбрасываем статистику
        for i in range(6):
            item = self.stats_table.item(i, 1)
            if item:
                item.setText("0.0")

        # Очищаем график
        self.ax.clear()
        self.ax.set_xlabel("C_хим")
        self.ax.set_ylabel("C_расч")
        self.ax.set_title("График зависимости C_хим от C_расч")
        self.canvas.draw()

    def open_sample_dialog(self):
        """Открывает диалог формирования выборки"""
        dialog = SampleDialog(self.db, self)
        if dialog.exec():
            print(f"Получена выборка: {len(self.current_sample)} строк")
            self.load_data()

    def load_data(self):

        try:
            # 1. Загружаем параметры выборки
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
                QMessageBox.critical(self, "Ошибка", "В выборке отсутствует product_id")
                return

            # 2. Получаем el_nmb из UI
            el_nmb = self.combo_element.currentData()
            if el_nmb is None:
                QMessageBox.warning(self, "Ошибка", "Сначала выберите элемент")
                return

            # 3. Запрашиваем PR_SET для получения meas_type
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

            # 4. Заполняем комбобоксы членами уравнения
            self._load_equation_terms(meas_type, el_nmb)

            # 5. Выгружаем данные из PR_MEAS → raw_buffer
            self.raw_buffer = self._fetch_pr_meas_data(sample_config, el_nmb, meas_type)
            print(f"📥 Получено строк: {len(self.raw_buffer)}")

            if not self.raw_buffer:
                QMessageBox.warning(self, "Информация", "По условиям выборки данных не найдено.")
                self.data_table.setRowCount(0)
                return

            # 6. Загружаем начальное уравнение в комбобоксы
            self._apply_initial_equation(pr_set_row, meas_type)

            # 7. Обновляем таблицу данных (только базовые колонки)
            self._update_data_table_from_buffer()

            # 8. Обновляем множители и выполняем регрессию
            self.perform_regression()

            QMessageBox.information(self, "Готово", f"Данные загружены: {len(self.raw_buffer)} записей")

        except Exception as e:
            import traceback
            print("❌ Ошибка в load_data():")
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка", f"load_data() провалился:\n{str(e)}")

    def _load_equation_terms(self, meas_type, el_nmb):
        """Заполняет 5 комбобоксов на основе meas_type и el_nmb"""
        try:
            json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
            json_path = get_config_path() / json_file

            if not os.path.exists(json_path):
                print(f"❌ {json_path} не найден")
                terms_list = []
            else:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                terms_list = []
                if meas_type == 0:
                    interactions = data.get("interactions", [])
                    terms_list = [term["description"] for term in interactions
                                if term.get("description") and term["description"].strip()]
                else:
                    for group in data.get("interactions", []):
                        if group.get("element_original_number") == el_nmb:
                            interactions = group.get("interactions", [])
                            terms_list = [term["description"] for term in interactions
                                        if term.get("description") and term["description"].strip()]
                            break

            for combo in self.combo_equation_terms:
                combo.blockSignals(True)  # Блокируем сигналы во время обновления
                combo.clear()
                combo.addItem("")
                combo.addItems(terms_list)
                combo.setPlaceholderText("Член уравнения")
                combo.blockSignals(False)

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

            cols = ["pr_nmb", "meas_dt"]
            if meas_type == 0:
                cols.extend([f"i_00_{i:02d}" for i in range(20)])
            else:
                cols.extend([f"c_cor_{i:02d}" for i in range(1, 9)])

            chem_col = f"c_chem_0{el_nmb}"
            cor_col = f"c_cor_0{el_nmb}"
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
                AND pr_nmb = ?
                AND {chem_col} <> 0
                AND active_model = 1
            """

            meas_index = self.combo_meas_type.currentIndex()
            if meas_index == 1:
                query += " AND meas_type = 0"
            elif meas_index == 2:
                query += " AND meas_type = 1"

            query += " ORDER BY meas_dt, timestamp"

            try:
                rows = self.db.fetch_all(query, [start_dt, end_dt, pr_nmb])
                all_rows.extend(rows)
            except Exception as e:
                print(f"⚠️ Ошибка запроса для pr_nmb={pr_nmb}: {e}")

        return all_rows

    def _apply_initial_equation(self, pr_set_row, meas_type):
        """Загружает начальное уравнение в комбобоксы"""
        try:
            k_prefix = "k_i_" if meas_type == 0 else "k_c_"
            op_prefix = "operand_i_" if meas_type == 0 else "operand_c_"
            op_type = "operator_i_" if meas_type == 0 else "operator_c_"

            json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
            json_path = get_config_path() / json_file

            if not os.path.exists(json_path):
                print(f"⚠️ {json_path} не найден — пропускаем заполнение членов")
                return

            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)

            term_lookup = {}
            if meas_type == 0:
                for term in json_data.get("interactions", []):
                    desc = term.get("description", "").strip()
                    if desc:
                        key = (term["x1"], term["x2"], term["op"])
                        term_lookup[key] = desc
            else:
                el_nmb = self.combo_element.currentData()
                for group in json_data.get("interactions", []):
                    if group.get("element_original_number") == el_nmb:
                        for term in group.get("interactions", []):
                            desc = term.get("description", "").strip()
                            if desc:
                                key = (term["x1"], term["x2"], term["op"])
                                term_lookup[key] = desc
                        break

            term_specs = [
                (f"{op_prefix}01_01", f"{op_prefix}02_01", f"{op_type}01"),
                (f"{op_prefix}01_02", f"{op_prefix}02_02", f"{op_type}02"),
                (f"{op_prefix}01_03", f"{op_prefix}02_03", f"{op_type}03"),
                (f"{op_prefix}01_04", f"{op_prefix}02_04", f"{op_type}04"),
                (f"{op_prefix}01_05", f"{op_prefix}02_05", f"{op_type}05"),
            ]

            found_terms = []
            for i, (x1_key, x2_key, op_key) in enumerate(term_specs, start=1):
                x1 = pr_set_row.get(x1_key, 0)
                x2 = pr_set_row.get(x2_key, 0)
                op = pr_set_row.get(op_key, 0)

                desc = term_lookup.get((x1, x2, op), "-")
                found_terms.append(desc)

            for i, combo in enumerate(self.combo_equation_terms):
                combo.blockSignals(True)
                if i < len(found_terms) and found_terms[i] != "-":
                    for idx in range(combo.count()):
                        if combo.itemText(idx) == found_terms[i]:
                            combo.setCurrentIndex(idx)
                            break
                else:
                    combo.setCurrentIndex(0)
                combo.blockSignals(False)

            print(f"✅ Уравнение загружено: {found_terms}")

        except Exception as e:
            import traceback
            print("❌ Ошибка в _apply_initial_equation:")
            traceback.print_exc()

    def _update_data_table_from_buffer(self):
        """Заполняет data_table из self.raw_buffer (базовые колонки)"""
        self.data_table.setRowCount(0)
        if not self.raw_buffer:
            return

        self.data_table.setRowCount(len(self.raw_buffer))
        for row_idx, rec in enumerate(self.raw_buffer):
            self.data_table.setItem(row_idx, 0, QTableWidgetItem(str(rec.get("pr_nmb", ""))))
            self.data_table.setItem(row_idx, 1, QTableWidgetItem(str(rec.get("meas_dt", ""))))

            el_nmb = self.combo_element.currentData()
            c_chem = rec.get(f"c_chem_0{el_nmb}", "")
            self.data_table.setItem(row_idx, 7, QTableWidgetItem(str(c_chem)))

            # Колонки C_расч, ΔC, δC оставляем пустыми до регрессии
            self.data_table.setItem(row_idx, 8, QTableWidgetItem(""))  # C_расч
            self.data_table.setItem(row_idx, 9, QTableWidgetItem(""))  # ΔC
            self.data_table.setItem(row_idx, 10, QTableWidgetItem(""))  # δC

    def perform_regression(self):
        """Выполняет регрессию (LINEST) → обновляет все таблицы и график"""
        if not hasattr(self, 'raw_buffer') or not self.raw_buffer:
            return

        try:
            # 1. Собираем матрицу признаков X и вектор y
            X_matrix, y_vector = self._build_regression_data()

            if X_matrix is None or y_vector is None:
                return

            # 2. Выполняем регрессию
            coefficients, statistics, standard_errors, t_stats, p_values = self._calculate_regression(X_matrix, y_vector)

            # 3. Обновляем таблицы
            self._update_coefficients_table(coefficients, p_values)
            self._update_statistics_table(statistics, y_vector)

            # 4. Применяем уравнение для расчета C_расч
            self.apply_current_equation()

            # 5. Строим график
            self._update_plot(y_vector)

        except Exception as e:
            import traceback
            print("❌ Ошибка в perform_regression():")
            traceback.print_exc()

    def _build_regression_data(self):
        """Строит матрицу признаков X и вектор целевых значений y"""
        try:
            n_samples = len(self.raw_buffer)
            if n_samples == 0:
                return None, None

            # Вектор y (C_хим)
            el_nmb = self.combo_element.currentData()
            y_vector = np.array([rec.get(f"c_chem_0{el_nmb}", 0.0) for rec in self.raw_buffer])

            # Матрица X: [1, X1, X2, X3, X4, X5]
            X_matrix = np.ones((n_samples, 6))  # 6 колонок: A0 + A1..A5

            # Заполняем признаки X1..X5
            for i, combo in enumerate(self.combo_equation_terms):
                term_desc = combo.currentText().strip()
                if term_desc and term_desc != "":
                    feature_values = self._compute_feature(term_desc, self.current_meas_type, el_nmb)
                    X_matrix[:, i+1] = feature_values  # i+1 потому что первый столбец - единицы для A0

            return X_matrix, y_vector

        except Exception as e:
            print(f"❌ Ошибка в _build_regression_data: {e}")
            return None, None

    def _calculate_regression(self, X, y):
        """Выполняет линейную регрессию и возвращает коэффициенты, статистику и значимость"""
        try:
            n_samples, n_features = X.shape

            # Решаем систему (X.T * X)^-1 * X.T * y
            coefficients = np.linalg.lstsq(X, y, rcond=None)[0]

            # Предсказанные значения
            y_pred = X @ coefficients
            residuals = y - y_pred

            # Среднеквадратичная ошибка
            mse = np.sum(residuals**2) / (n_samples - n_features)
            rmse = np.sqrt(mse)

            # R²
            ss_res = np.sum(residuals**2)
            ss_tot = np.sum((y - np.mean(y))**2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

            # Стандартные ошибки коэффициентов
            try:
                XTX_inv = np.linalg.inv(X.T @ X)
                standard_errors = np.sqrt(np.diag(XTX_inv) * mse)

                # t-статистики
                t_stats = coefficients / standard_errors

                # p-values (двусторонний тест)
                from scipy import stats
                p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), n_samples - n_features))
            except:
                # Если матрица вырождена, используем нули
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
            print(f"❌ Ошибка в _calculate_regression: {e}")
            return np.zeros(6), {}, np.zeros(6), np.zeros(6), np.ones(6)

    def _update_coefficients_table(self, coefficients, p_values):
        """Обновляет столбец 'Множитель' в таблице коэффициентов"""
        # A0 не имеет множителя (константа)
        a0_item = self.coeff_table.item(0, 1)
        if a0_item:
            a0_item.setText("-")  # или можно оставить пустым

        # A1..A5 - множители из комбобоксов
        for i in range(1, 6):  # A1..A5
            combo = self.combo_equation_terms[i-1]
            term_desc = combo.currentText().strip()
            multiplier_item = self.coeff_table.item(i, 1)

            if multiplier_item:
                if term_desc and term_desc != "":
                    multiplier_item.setText(term_desc)
                else:
                    multiplier_item.setText("-")

        """Обновляет таблицу коэффициентов со значимостью"""
        for i, (coeff, p_value) in enumerate(zip(coefficients, p_values)):
            # Значение коэффициента
            value_item = self.coeff_table.item(i, 2)
            if value_item:
                value_item.setText(f"{coeff:.6g}")

            # Значимость (p-value)
            significance_item = self.coeff_table.item(i, 3)
            if significance_item:
                significance_item.setText(f"{p_value:.4f}")

                # Подсветка значимых коэффициентов
                if p_value < 0.05:
                    significance_item.setBackground(Qt.GlobalColor.green)
                elif p_value < 0.1:
                    significance_item.setBackground(Qt.GlobalColor.yellow)
                else:
                    significance_item.setBackground(Qt.GlobalColor.white)

    def _update_statistics_table(self, statistics, y_vector=None):
        """Обновляет таблицу статистики"""
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
            if item:
                item.setText(f"{value:.6g}")

    def _update_plot(self, y_vector):
        """Обновляет график зависимости C_хим от C_расч"""
        try:
            self.ax.clear()

            # Собираем C_хим и C_расч из таблицы
            c_chem_values = []
            c_calc_values = []

            for row in range(self.data_table.rowCount()):
                chem_item = self.data_table.item(row, 7)
                calc_item = self.data_table.item(row, 8)

                if chem_item and calc_item and chem_item.text() and calc_item.text():
                    try:
                        c_chem = float(chem_item.text())
                        c_calc = float(calc_item.text())
                        c_chem_values.append(c_chem)
                        c_calc_values.append(c_calc)
                    except ValueError:
                        continue

            if c_chem_values and c_calc_values:
                self.ax.scatter(c_chem_values, c_calc_values, alpha=0.6, label='Данные')

                # Линия идеальной корреляции
                min_val = min(min(c_chem_values), min(c_calc_values))
                max_val = max(max(c_chem_values), max(c_calc_values))
                self.ax.plot([min_val, max_val], [min_val, max_val], 'r--', label='Идеальная корреляция')

                self.ax.set_xlabel("C_хим")
                self.ax.set_ylabel("C_расч")
                self.ax.set_title("График зависимости C_хим от C_расч")
                self.ax.legend()
                self.ax.grid(True, alpha=0.3)

            self.canvas.draw()

        except Exception as e:
            print(f"❌ Ошибка в _update_plot: {e}")

    def apply_current_equation(self):
        """Рассчитывает C_расч, ΔC, δC по текущим коэффициентам и выбранным членам"""
        try:
            if not hasattr(self, 'raw_buffer') or not self.raw_buffer:
                return

            # Читаем текущие коэффициенты из coeff_table
            coeffs = []
            for i in range(6):
                item = self.coeff_table.item(i, 2)
                try:
                    val = float(item.text()) if item and item.text() else 0.0
                except:
                    val = 0.0
                coeffs.append(val)

            A0, A1, A2, A3, A4, A5 = coeffs

            # Вычисляем признаки для всех членов уравнения
            el_nmb = self.combo_element.currentData()
            features = []
            for combo in self.combo_equation_terms:
                desc = combo.currentText().strip()
                feat_vals = self._compute_feature(desc, self.current_meas_type, el_nmb)
                features.append(feat_vals)
                self._fill_feature_column(len(features)-1, feat_vals)

            # Рассчитываем C_расч для каждой строки
            for row_idx in range(len(self.raw_buffer)):
                c_chem = self.raw_buffer[row_idx].get(f"c_chem_0{el_nmb}", 0.0)

                # Собираем X-вектор: [1, X1, X2, X3, X4, X5]
                X_row = [1.0] + [features[i][row_idx] for i in range(5)]

                # C_расч = A0*X0 + A1*X1 + ... + A5*X5
                c_calc = sum(coeffs[i] * X_row[i] for i in range(6))

                # ΔC, δC
                dC = c_calc - c_chem
                ddc = abs(dC) / c_chem if c_chem != 0 else 0.0

                # Обновляем таблицу
                self.data_table.setItem(row_idx, 8, QTableWidgetItem(f"{c_calc:.6g}"))
                self.data_table.setItem(row_idx, 9, QTableWidgetItem(f"{dC:.6g}"))
                self.data_table.setItem(row_idx, 10, QTableWidgetItem(f"{ddc:.6g}"))

            print(f"✅ Расчёт завершён: {len(self.raw_buffer)} строк")

        except Exception as e:
            import traceback
            print("❌ Ошибка в apply_current_equation():")
            traceback.print_exc()

    def _compute_feature(self, feature_desc: str, meas_type: int, el_nmb: int) -> list:
        """Вычисляет один признак для всего self.raw_buffer"""
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
                    if found:
                        break

        if not found:
            return [0.0] * len(self.raw_buffer)

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
            except Exception as e:
                result.append(0.0)

        return result

    def _fill_feature_column(self, col_index: int, values: list):
        """Заполняет колонки признаков в data_table"""
        if 0 <= col_index <= 4:
            for row_idx, val in enumerate(values):
                self.data_table.setItem(row_idx, 2 + col_index, QTableWidgetItem(f"{val:.6g}"))

    def save_equation(self):
        """Сохранение уравнения - заглушка"""
        print("Сохранение уравнения...")
        QMessageBox.information(self, "Info", "Сохранение уравнения будет реализовано позже")

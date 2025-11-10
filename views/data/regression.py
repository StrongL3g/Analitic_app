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

    def load_equation_terms(self):
        """
        Заполняет 5 комбобоксов self.combo_equation_terms
        на основе: product_id (из s_regress.json), el_nmb (из combo_element), meas_type (из БД)
        """
        # 1. Проверяем, есть ли хотя бы одно условие в s_regress.json
        filter_path = "config/sample/s_regress.json"
        try:
            if not os.path.exists(filter_path):
                print("Файл config/sample/s_regress.json не найден")
                terms_list = []
            else:
                with open(filter_path, "r", encoding="utf-8") as f:
                    filter_config = json.load(f)

                if not filter_config:
                    print("Файл s_regress.json пуст")
                    terms_list = []
                else:
                    # Берём product_id первого условия
                    pr_nmb = filter_config[0].get("product_id")
                    if pr_nmb is None:
                        raise ValueError("product_id отсутствует в первом условии")

                    # 2. Получаем el_nmb из UI
                    el_nmb = self.combo_element.currentData()  # original_number, например, 1 для Cu
                    if el_nmb is None:
                        print("Элемент не выбран")
                        terms_list = []
                    else:
                        # 3. Запрашиваем meas_type из БД
                        query = """
                            SELECT meas_type
                            FROM PR_SET
                            WHERE pr_nmb = ? AND el_nmb = ? AND active_model = 1
                        """
                        row = self.db.fetch_one(query, [pr_nmb, el_nmb])
                        if not row or row.get("meas_type") is None:
                            print(f"Не найдена настройка meas_type для pr_nmb={pr_nmb}, el_nmb={el_nmb}")
                            terms_list = []
                        else:
                            meas_type = row["meas_type"]
                            print(f"meas_type = {meas_type} (pr_nmb={pr_nmb}, el_nmb={el_nmb})")

                            # 4. Выбираем JSON-файл
                            json_file = "lines_math_interactions.json" if meas_type == 0 else "math_interactions.json"
                            json_path = f"config/{json_file}"

                            if not os.path.exists(json_path):
                                print(f"Файл {json_path} не найден")
                                terms_list = []
                            else:
                                with open(json_path, "r", encoding="utf-8") as f:
                                    data = json.load(f)

                                # 5. Извлекаем список description
                                terms_list = []
                                try:
                                    if meas_type == 0:
                                        # lines_math_interactions.json → глобальный список interactions
                                        interactions = data.get("interactions", [])
                                        terms_list = [
                                            term["description"]
                                            for term in interactions
                                            if term.get("description") and term["description"].strip()
                                        ]
                                    else:
                                        # math_interactions.json → ищем по element_original_number
                                        interactions_groups = data.get("interactions", [])
                                        target_group = None
                                        for group in interactions_groups:
                                            if group.get("element_original_number") == el_nmb:
                                                target_group = group
                                                break
                                        if target_group:
                                            interactions = target_group.get("interactions", [])
                                            terms_list = [
                                                term["description"]
                                                for term in interactions
                                                if term.get("description") and term["description"].strip()
                                            ]
                                        else:
                                            print(f"В {json_file} не найдена группа для element_original_number={el_nmb}")
                                            terms_list = []
                                except Exception as e:
                                    print(f"Ошибка обработки {json_file}: {e}")
                                    terms_list = []

        except Exception as e:
            print(f"Ошибка в load_equation_terms: {e}")
            terms_list = []

        # 6. Заполняем 5 комбобоксов
        for combo in self.combo_equation_terms:
            combo.clear()
            combo.addItem("")  # пустой выбор
            combo.addItems(terms_list)
            combo.setPlaceholderText("Выберите член уравнения")

    def load_data(self):
        """Выгрузка данных - заглушка для первой итерации"""
        print("Выгрузка данных...")
        print(f"Элемент: {self.combo_element.currentText()}")
        print(f"Тип измерения: {self.current_meas_type}")

        # TODO: Реализовать actual data loading
        QMessageBox.information(self, "Info", "Выгрузка данных будет реализована в следующей итерации")

        #
        self.load_equation_terms()

        # Расчет регрессии
        self.start_regress()

    def start_regress(self):
        print("Процедура регрессии...")

        # TODO: Реализовать работу с данными
        QMessageBox.information(self, "Info", "Расчет регрессии будет реализована в следующей итерации")

    def save_equation(self):
        """Сохранение уравнения - заглушка"""
        print("Сохранение уравнения...")
        QMessageBox.information(self, "Info", "Сохранение уравнения будет реализовано позже")

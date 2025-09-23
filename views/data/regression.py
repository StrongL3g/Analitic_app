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

        # Таблица коэффициентов
        left_top_layout.addWidget(QLabel("Сводная таблица коэффициентов:"))
        self.coeff_table = QTableWidget()
        self.coeff_table.setRowCount(7)
        self.coeff_table.setColumnCount(4)
        self.coeff_table.setHorizontalHeaderLabels(["Множитель", "Коэффициент", "Значимость"])
        self.coeff_table.setVerticalHeaderLabels(["A0", "A1", "A2", "A3", "A4", "A5"])
        left_top_layout.addWidget(self.coeff_table)

        # Таблица характеристик уравнения
        left_top_layout.addWidget(QLabel("Характеристики уравнения:"))
        self.stats_table = QTableWidget()
        self.stats_table.setRowCount(6)
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
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
        self.load_elements()
        self.combo_element.currentIndexChanged.connect(self.on_element_changed)
        self.combo_meas_type.currentIndexChanged.connect(self.on_meas_type_changed)

    def load_elements(self):
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

    def load_equation_terms(self):
        """Загрузка членов уравнения в комбобоксы"""
        if not self.current_element:
            return

        try:
            # Определяем какой файл использовать
            json_file = "line_math_interactions.json" if self.current_meas_type == 0 else "math_interactions.json"
            json_path = f"config/{json_file}"

            if not os.path.exists(json_path):
                print(f"Файл {json_file} не найден")
                return

            with open(json_path, "r", encoding="utf-8") as f:
                interactions_data = json.load(f)

            # Находим взаимодействия для выбранного элемента
            terms_to_load = []

            if self.current_meas_type == 0:  # По линиям
                # Ищем по original_number
                for interaction_group in interactions_data.get("interactions", []):
                    if interaction_group.get("element_original_number") == self.current_element:
                        terms_to_load = [term["description"] for term in interaction_group.get("interactions", [])
                                      if term.get("description")]
                        break
            else:  # По элементам
                # Ищем по имени элемента
                element_name = self.combo_element.currentText()
                for interaction_group in interactions_data.get("interactions", []):
                    if interaction_group.get("element_name") == element_name:
                        terms_to_load = [term["description"] for term in interaction_group.get("interactions", [])
                                      if term.get("description")]
                        break

            # Заполняем комбобоксы
            for combo in self.combo_equation_terms:
                combo.clear()
                combo.addItems([""] + terms_to_load)

            print(f"Загружено членов уравнения: {len(terms_to_load)}")

        except Exception as e:
            print(f"Ошибка загрузки членов уравнения: {e}")

    def on_element_changed(self, index):
        """Обработчик изменения элемента"""
        if index >= 0:
            self.current_element = self.combo_element.currentData()
            self.load_equation_terms()

    def on_meas_type_changed(self, index):
        """Обработчик изменения типа измерения"""
        # 0: Все пробы, 1: Ручные, 2: Цикл
        # Пока просто используем 0 для интенсивностей, нужно уточнить логику
        self.current_meas_type = 0 if index == 0 else 1
        self.load_equation_terms()

    def open_sample_dialog(self):
        """Открывает диалог формирования выборки"""
        dialog = SampleDialog(self.db, self)
        if dialog.exec():
            self.load_sample_from_file()
            print(f"Получена выборка: {len(self.current_sample)} строк")
            self.update_sample_table()

    def load_sample_from_file(self):
        """Загружает выборку из файла"""
        try:
            sample_path = "config/sample.json"
            if os.path.exists(sample_path):
                with open(sample_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.current_sample = data if isinstance(data, list) else []
            else:
                self.current_sample = []
        except Exception as e:
            print(f"Ошибка загрузки выборки: {e}")
            self.current_sample = []

    def update_sample_table(self):
        """Обновляет таблицу выборки"""
        self.data_table.setRowCount(0)

        if not self.current_sample:
            return

        self.data_table.setRowCount(len(self.current_sample))

        for row, item in enumerate(self.current_sample):
            # Заполняем базовые данные
            self.data_table.setItem(row, 0, QTableWidgetItem(str(item.get('product_id', ''))))
            self.data_table.setItem(row, 1, QTableWidgetItem(
                f"{item.get('date_from', '')} {item.get('time_from', '')} - "
                f"{item.get('date_to', '')} {item.get('time_to', '')}"
            ))

            # Остальные колонки пока пустые, заполнятся после выгрузки данных
            for col in range(2, 11):
                self.data_table.setItem(row, col, QTableWidgetItem(""))

    def load_data(self):
        """Выгрузка данных - заглушка для первой итерации"""
        print("Выгрузка данных...")
        print(f"Элемент: {self.combo_element.currentText()}")
        print(f"Тип измерения: {self.current_meas_type}")
        print(f"Выборка: {len(self.current_sample)} записей")

        # TODO: Реализовать actual data loading
        QMessageBox.information(self, "Info", "Выгрузка данных будет реализована в следующей итерации")

    def save_equation(self):
        """Сохранение уравнения - заглушка"""
        print("Сохранение уравнения...")
        QMessageBox.information(self, "Info", "Сохранение уравнения будет реализовано позже")

    def clear_tables(self):
        """Очистка таблиц"""
        self.coeff_table.clearContents()
        self.stats_table.clearContents()
        self.data_table.setRowCount(0)

        # Очищаем график
        self.ax.clear()
        self.ax.grid(True, alpha=0.3)
        self.canvas.draw()

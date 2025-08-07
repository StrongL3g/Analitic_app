# views/data/regression.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem,
    QComboBox, QLineEdit, QGroupBox, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt
from database.db import Database
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


class RegressionPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # === Заголовок ===
        title = QLabel("Регрессионный анализ")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # === Основной сплиттер (горизонтальный) ===
        main_splitter = QSplitter(Qt.Vertical)

        # === Верхняя часть ===
        top_widget = QWidget()
        top_layout = QHBoxLayout()

        # === Левая верхняя часть (сводные данные и кнопки) ===
        left_top_group = QGroupBox("Результаты и управление")
        left_top_layout = QVBoxLayout()

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_change_selection = QPushButton("Изменить выборку")
        btn_save_equation = QPushButton("Сохранить уравнение")
        btn_load_data = QPushButton("Выгрузка данных")

        btn_layout.addWidget(btn_change_selection)
        btn_layout.addWidget(btn_save_equation)
        btn_layout.addWidget(btn_load_data)
        btn_layout.addStretch()
        left_top_layout.addLayout(btn_layout)

        # Таблица коэффициентов
        left_top_layout.addWidget(QLabel("Сводная таблица коэффициентов:"))
        coeff_table = QTableWidget()
        coeff_table.setRowCount(6)
        coeff_table.setColumnCount(3)
        coeff_table.setHorizontalHeaderLabels(["Множитель", "Коэффициент", "Значимость"])
        coeff_table.setVerticalHeaderLabels(["A0", "A1", "A2", "A3", "A4", "A5"])
        # Заполним тестовыми данными
        coeff_data = [
            ["-", "-2.26E-01", "0.99"],
            ["Cu_Ka", "5.03E-05", "2.93"],
            ["Cu_Ka * Ni_Ka", "-5.87E-09", "3.36"],
            ["", "0", "0"],
            ["", "0", "0"],
            ["", "0", "0"],
        ]
        for row, rowData in enumerate(coeff_data):
            for col, value in enumerate(rowData):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                coeff_table.setItem(row, col, item)
        left_top_layout.addWidget(coeff_table)

        # Таблица характеристик уравнения
        left_top_layout.addWidget(QLabel("Характеристики уравнения:"))
        stats_table = QTableWidget()
        stats_table.setRowCount(6)
        stats_table.setColumnCount(2)
        stats_table.setHorizontalHeaderLabels(["Параметр", "Значение"])
        # Заполним тестовыми данными
        stats_data = [
            ["CKO σ", "0.0469"],
            ["Отн. CKO", "14%"],
            ["Сmin", "0.20"],
            ["Сmax", "0.47"],
            ["Сср", "0.335"],
            ["Корреляция R²", "0.336"]
        ]
        for row, rowData in enumerate(stats_data):
            for col, value in enumerate(rowData):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignCenter)
                stats_table.setItem(row, col, item)
        left_top_layout.addWidget(stats_table)

        left_top_group.setLayout(left_top_layout)

        # === Верхняя правая часть (график) ===
        right_top_group = QGroupBox("График зависимости C_хим от C_расч")
        right_top_layout = QVBoxLayout()

        # Создаем график
        fig, ax = plt.subplots(figsize=(5, 4))
        canvas = FigureCanvas(fig)
        # Пример графика y=x с точками
        ax.plot([0, 0.5], [0, 0.5], 'r--', alpha=0.7)  # Линия y=x
        ax.scatter([0.1, 0.2, 0.3, 0.4], [0.12, 0.19, 0.31, 0.39], alpha=0.7)  # Точки
        ax.set_title("График зависимости C_хим от C_расч")
        ax.set_xlabel("C_хим, %")
        ax.set_ylabel("C_расч, %")
        ax.grid(True, alpha=0.3)
        right_top_layout.addWidget(canvas)

        right_top_group.setLayout(right_top_layout)

        # Добавляем левую и правую части в верхний layout
        top_layout.addWidget(left_top_group, 40)  # 40% ширины
        top_layout.addWidget(right_top_group, 60)  # 60% ширины
        top_widget.setLayout(top_layout)

        # === Нижняя часть (комбо-боксы и таблица выборки) ===
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()

        # Комбо-боксы
        combo_layout = QHBoxLayout()

        combo_element = QComboBox()
        combo_element.addItems(["Cu", "Fe", "Ni", "Тф"])  # Пример элементов

        combo_all_probes = QComboBox()
        combo_all_probes.addItems(["Все пробы", "Ручные", "Цикл"])

        combo_layout.addWidget(QLabel("Элемент:"))
        combo_layout.addWidget(combo_element)
        combo_layout.addWidget(QLabel("Пробы:"))
        combo_layout.addWidget(combo_all_probes)

        # 5 комбо-боксов для членов уравнения
        combo_layout.addWidget(QLabel("Члены уравнения:"))
        combo_equation_terms = []
        for i in range(5):
            combo = QComboBox()
            combo.addItems(["", "Cu_Ka", "Ni_Ka", "Fe_Ka", "Cu_Ka * Ni_Ka"])  # Пример членов
            combo_equation_terms.append(combo)
            combo_layout.addWidget(combo)

        combo_layout.addStretch()
        bottom_layout.addLayout(combo_layout)

        # Таблица выборки
        bottom_layout.addWidget(QLabel("Таблица выборки:"))
        data_table = QTableWidget()
        data_table.setRowCount(10)
        data_table.setColumnCount(11)
        data_table.setHorizontalHeaderLabels([
            "Продукт", "Дата/Время", "Cu_Ka", "Cu_Ka * Ni_Ka",
            "", "", "", "C_хим", "C_расч", "ΔC", "δC=|ΔC/C_хим|"
        ])
        # Заполним тестовыми данными
        for row in range(10):
            for col in range(11):
                item = QTableWidgetItem(f"Данные {row+1},{col+1}")
                item.setTextAlignment(Qt.AlignCenter)
                data_table.setItem(row, col, item)
        bottom_layout.addWidget(data_table)

        bottom_widget.setLayout(bottom_layout)

        # === Объединяем все части ===
        main_splitter.addWidget(top_widget)
        main_splitter.addWidget(bottom_widget)
        main_splitter.setSizes([400, 300])  # Примерные размеры

        layout.addWidget(main_splitter)

        self.setLayout(layout)

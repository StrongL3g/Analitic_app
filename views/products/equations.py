from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QFrame,
                               QHBoxLayout, QSplitter, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox)
from PySide6.QtCore import Qt
import json
from database.db import Database


class EquationsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}
        self.elements_config = self.load_elements_config()
        self.range_config = self.load_range_config()
        self.init_ui()
        self.setup_connections()

    def load_elements_config(self):
        try:
            with open('Analitic_app/config/elements.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки elements.json: {e}")
            return []

    def load_range_config(self):
        try:
            with open('Analitic_app/config/range.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки range.json: {e}")
            return []

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setMinimumWidth(1000)
        self.setMinimumHeight(600)

        # Верхняя панель с комбобоксами
        top_frame = QFrame()
        top_frame.setFrameStyle(QFrame.Box)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        top_layout.setContentsMargins(10, 5, 10, 5)
        top_frame.setLayout(top_layout)

        # Выбор продукта
        product_layout = QVBoxLayout()
        product_layout.setSpacing(2)
        product_label = QLabel("Продукт:")
        product_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        product_label.setFixedHeight(20)

        self.product_combo = QComboBox()
        products = [f"Продукт {i}" for i in range(1, 9)]
        self.product_combo.addItems(products)
        self.product_combo.setFixedSize(150, 30)

        product_layout.addWidget(product_label)
        product_layout.addWidget(self.product_combo)
        top_layout.addLayout(product_layout)

        # Выбор модели
        model_layout = QVBoxLayout()
        model_layout.setSpacing(2)
        model_label = QLabel("Модель:")
        model_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        model_label.setFixedHeight(20)

        self.model_combo = QComboBox()
        models = [f"Модель {i}" for i in range(1, 4)]
        self.model_combo.addItems(models)
        self.model_combo.setFixedSize(150, 30)

        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        top_layout.addLayout(model_layout)

        top_layout.addStretch()
        top_frame.setFixedHeight(70)

        # Таблица с уравнениями
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(2)
        self.table_widget.setHorizontalHeaderLabels(["Коэффициенты корректировки", "Уравнения расчета концентраций"])
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_widget.setAlternatingRowColors(True)

        # Добавляем разделитель
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(top_frame)
        splitter.addWidget(self.table_widget)
        splitter.setSizes([70, 500])

        main_layout.addWidget(splitter)

    def setup_connections(self):
        self.product_combo.currentIndexChanged.connect(self.load_equations)
        self.model_combo.currentIndexChanged.connect(self.load_equations)

    def load_equations(self):
        try:
            product_nmb = self.product_combo.currentIndex() + 1
            model_nmb = self.model_combo.currentIndex() + 1

            query = """
            SELECT * FROM PR_SET 
            WHERE pr_nmb = ? AND mdl_nmb = ?
            ORDER BY el_nmb
            """

            params = [product_nmb, model_nmb]
            results = self.db.fetch_all(query, params)

            if not results:
                self.table_widget.setRowCount(0)
                QMessageBox.information(self, "Информация", "Данные для выбранного продукта и модели не найдены.")
                return

            self.table_widget.setRowCount(len(results))

            for row_idx, row in enumerate(results):
                equation = self.build_equation(row)
                correction_coeffs = self.build_correction_coeffs(row)

                # Колонка с коэффициентами корректировки
                coeff_item = QTableWidgetItem(correction_coeffs)
                coeff_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table_widget.setItem(row_idx, 0, coeff_item)

                # Колонка с уравнениями
                equation_item = QTableWidgetItem(equation)
                equation_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table_widget.setItem(row_idx, 1, equation_item)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки уравнений: {str(e)}")
            self.table_widget.setRowCount(0)

    def build_correction_coeffs(self, row):
        meas_type = row.get('meas_type', 0)
        coeffs = []

        if meas_type == 0:  # Интенсивности
            k0 = row.get('k_i_klin00', 0)
            k1 = row.get('k_i_klin01', 0)
            coeffs.append(f"k0 {self.format_number(k0)}")
            coeffs.append(f"k1 {self.format_number(k1)}")
        else:  # Концентрации
            k0 = row.get('k_c_klin00', 0)
            k1 = row.get('k_c_klin01', 0)
            coeffs.append(f"k0 {self.format_number(k0)}")
            coeffs.append(f"k1 {self.format_number(k1)}")

        return "\n".join(coeffs)

    def format_number(self, num):
        """Форматирование числа с удалением лишних нулей"""
        if num == 0:
            return "0"
        return f"{float(num):.9f}".rstrip('0').rstrip('.')

    def build_equation(self, row):
        el_nmb = row.get('el_nmb', 0)
        element_name = self.get_element_name(el_nmb)
        meas_type = row.get('meas_type', 0)

        equation_parts = [f"C({element_name}) = "]

        # Нулевой коэффициент
        if meas_type == 0:
            k0 = row.get('k_i_alin00', 0)
        else:
            k0 = row.get('k_c_alin00', 0)

        equation_parts.append(self.format_number(k0))

        # Добавляем остальные члены уравнения
        for i in range(1, 6):  # alin01 to alin05
            k_key = f'k_i_alin{i:02d}' if meas_type == 0 else f'k_c_alin{i:02d}'
            k_value = row.get(k_key, 0)

            if k_value == 0:
                continue

            operator_key = f'operator_i_{i:02d}' if meas_type == 0 else f'operator_c_{i:02d}'
            operator = row.get(operator_key, 0)

            if operator == 0:
                continue

            operand1_key = f'operand_i_01_{i:02d}' if meas_type == 0 else f'operand_c_01_{i:02d}'
            operand2_key = f'operand_i_02_{i:02d}' if meas_type == 0 else f'operand_c_02_{i:02d}'

            operand1 = row.get(operand1_key, 0)
            operand2 = row.get(operand2_key, 0)

            expression = self.build_expression(operand1, operand2, operator, meas_type)

            if expression == "0":
                continue

            sign = "+" if k_value > 0 else "-"
            abs_k_value = abs(k_value)
            formatted_k = self.format_number(abs_k_value)
            equation_parts.append(f" {sign} {formatted_k}*({expression})")

        return "".join(equation_parts)

    def build_expression(self, operand1, operand2, operator, meas_type):
        prefix = "I_" if meas_type == 0 else "C_"

        # Проверка для оператора 7 (только для интенсивностей)
        if operator == 7 and meas_type != 0:
            return "0"

        if operator == 0:  # 0 - пустая операция
            return "0"

        elif operator == 1:  # 1 - берем только operand_i_01_01
            if operand1 > 0:
                name1 = self.get_range_name(operand1)
                return f"{prefix}{name1}"
            return "0"

        elif operator == 2:  # 2 - operand_i_01_01 * operand_i_02_01
            if operand1 > 0 and operand2 > 0:
                name1 = self.get_range_name(operand1)
                name2 = self.get_range_name(operand2)
                return f"{prefix}{name1}*{prefix}{name2}"
            return "0"

        elif operator == 3:  # 3 - operand_i_01_01 / operand_i_02_01
            if operand1 > 0 and operand2 > 0:
                name1 = self.get_range_name(operand1)
                name2 = self.get_range_name(operand2)
                return f"{prefix}{name1}/{prefix}{name2}"
            return "0"

        elif operator == 4:  # 4 - operand_i_01_01 * operand_i_01_01
            if operand1 > 0:
                name1 = self.get_range_name(operand1)
                return f"{prefix}{name1}*{prefix}{name1}"
            return "0"

        elif operator == 5:  # 5 - 1 / operand_i_01_01
            if operand1 > 0:
                name1 = self.get_range_name(operand1)
                return f"1/{prefix}{name1}"
            return "0"

        elif operator == 6:  # 6 - operand_i_01_01 / operand_i_02_01 * operand_i_02_01
            if operand1 > 0 and operand2 > 0:
                name1 = self.get_range_name(operand1)
                name2 = self.get_range_name(operand2)
                return f"{prefix}{name1}/{prefix}{name2}*{prefix}{name2}"
            return "0"

        elif operator == 7:  # 7 - 1 / operand_i_01_01 * operand_i_01_01
            if operand1 > 0:
                name1 = self.get_range_name(operand1)
                return f"1/{prefix}{name1}*{prefix}{name1}"
            return "0"

        # Добавьте другие операторы по необходимости
        return "0"

    def get_element_name(self, el_nmb):
        for element in self.elements_config:
            if element.get('number') == el_nmb:
                return element.get('name', f"Element_{el_nmb}")
        return f"Element_{el_nmb}"

    def get_range_name(self, range_nmb):
        if range_nmb <= 0:
            return ""

        for range_item in self.range_config:
            if range_item.get('number') == range_nmb + 1:
                return range_item.get('name', f"Range_{range_nmb}")
        return f"Range_{range_nmb}"

    def showEvent(self, event):
        super().showEvent(event)
        self.load_equations()
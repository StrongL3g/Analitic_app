from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QFrame,
                               QHBoxLayout, QSplitter, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox, QLineEdit, QRadioButton,
                               QButtonGroup, QPushButton, QGroupBox, QFormLayout,
                               QScrollArea, QApplication)
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Qt
import json
from database.db import Database
from pathlib import Path


class EquationsPage(QWidget):
    """Виджет для отображения уравнений расчета концентраций"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}
        self._config_dir = self._get_config_directory()
        self.elements_config = self._load_elements_config()
        self.range_config = self._load_range_config()
        self.current_editing_row = None
        self.current_equation_data = None
        self.init_ui()
        self.setup_connections()

    def _get_config_directory(self) -> Path:
        """Получает путь к директории конфигурации"""
        base_dir = Path(__file__).parent
        config_dir = base_dir.parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        return config_dir

    def _load_config_file(self, filename: str) -> list:
        """Загружает конфигурационный файл JSON"""
        config_path = self._config_dir / filename

        if not config_path.exists():
            print(f"Файл конфигурации не найден: {config_path}")
            return []

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки файла {filename}: {e}")
            return []

    def _load_elements_config(self) -> list:
        """Загружает конфигурацию элементов"""
        return self._load_config_file("elements.json")

    def _load_range_config(self) -> list:
        """Загружает конфигурацию диапазонов"""
        return self._load_config_file("range.json")

    def _get_configured_elements_count(self) -> int:
        """Получает количество сконфигурированных элементов (исключая '-')"""
        count = 0
        for element in self.elements_config:
            if isinstance(element, dict):
                name = element.get('name', '').strip()
                if name and name != '-':
                    count += 1
        return count

    def _get_configured_element_numbers(self) -> list:
        """Получает список номеров сконфигурированных элементов"""
        numbers = []
        for element in self.elements_config:
            if isinstance(element, dict):
                name = element.get('name', '').strip()
                if name and name != '-':
                    numbers.append(element.get('number', 0))
        return numbers

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(800)

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
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)

        # Добавляем разделитель
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(top_frame)
        splitter.addWidget(self.table_widget)
        splitter.setSizes([70, 400])

        main_layout.addWidget(splitter)

        # Область редактирования уравнений
        self.edit_widget = self.create_edit_area()
        main_layout.addWidget(self.edit_widget)
        self.edit_widget.setVisible(False)

    def create_edit_area(self):
        """Создает область редактирования уравнения"""
        edit_widget = QGroupBox("Редактирование уравнения")
        edit_layout = QVBoxLayout()
        edit_layout.setSpacing(10)

        # Первая строка: Продукт №  Модель № Элемент:
        header_layout1 = QHBoxLayout()
        self.product_model_label = QLabel("Продукт №:  Модель №:  Элемент: ")
        header_layout1.addWidget(self.product_model_label)
        header_layout1.addStretch()
        edit_layout.addLayout(header_layout1)

        # Вторая строка: Выбор типа уравнения
        header_layout2 = QHBoxLayout()
        self.regression_radio = QRadioButton("Уравнение регрессии (интенсивности)")
        self.correlation_radio = QRadioButton("Уравнение корреляции (концентрации)")
        self.meas_type_group = QButtonGroup()
        self.meas_type_group.addButton(self.regression_radio, 0)
        self.meas_type_group.addButton(self.correlation_radio, 1)

        header_layout2.addWidget(self.regression_radio)
        header_layout2.addWidget(self.correlation_radio)
        header_layout2.addStretch()
        edit_layout.addLayout(header_layout2)

        # Третья строка: Критерии и диапазоны концентраций
        criteria_layout = QHBoxLayout()

        # Критерий Вода и C мин
        water_layout = QHBoxLayout()
        water_layout.setSpacing(1)
        water_label = QLabel("Критерий \"Вода\", NC >")
        self.water_crit_edit = QLineEdit()
        self.water_crit_edit.setFixedWidth(100)
        self.water_crit_edit.setValidator(QDoubleValidator())
        water_layout.addWidget(water_label)
        water_layout.addWidget(self.water_crit_edit)

        cmin_layout = QHBoxLayout()
        cmin_layout.setSpacing(1)
        cmin_layout.addSpacing(30)
        cmin_label = QLabel("C мин:")
        self.c_min_edit = QLineEdit()
        self.c_min_edit.setFixedWidth(100)
        self.c_min_edit.setValidator(QDoubleValidator())
        cmin_layout.addWidget(cmin_label)
        cmin_layout.addWidget(self.c_min_edit)

        criteria_layout.addLayout(water_layout)
        criteria_layout.addLayout(cmin_layout)
        criteria_layout.addStretch()
        edit_layout.addLayout(criteria_layout)

        # Четвертая строка: Критерий Пусто и C макс
        empty_layout = QHBoxLayout()

        # Критерий Пусто и C макс
        empty_crit_layout = QHBoxLayout()
        empty_crit_layout.setSpacing(1)
        empty_label = QLabel("Критерий \"Пусто\", Fe <")
        self.empty_crit_edit = QLineEdit()
        self.empty_crit_edit.setFixedWidth(100)
        self.empty_crit_edit.setValidator(QDoubleValidator())
        empty_crit_layout.addWidget(empty_label)
        empty_crit_layout.addWidget(self.empty_crit_edit)

        cmax_layout = QHBoxLayout()
        cmax_layout.setSpacing(1)
        cmax_layout.addSpacing(30)
        cmax_label = QLabel("C макс:")
        self.c_max_edit = QLineEdit()
        self.c_max_edit.setFixedWidth(100)
        self.c_max_edit.setValidator(QDoubleValidator())
        cmax_layout.addWidget(cmax_label)
        cmax_layout.addWidget(self.c_max_edit)

        empty_layout.addLayout(empty_crit_layout)
        empty_layout.addLayout(cmax_layout)
        empty_layout.addStretch()
        edit_layout.addLayout(empty_layout)

        # Коэффициенты корректировки
        corr_group = QGroupBox("Коэффициенты корректировки")
        corr_layout = QHBoxLayout()
        self.k0_edit = QLineEdit()
        self.k0_edit.setFixedWidth(120)
        self.k0_edit.setValidator(QDoubleValidator())
        self.k1_edit = QLineEdit()
        self.k1_edit.setFixedWidth(120)
        self.k1_edit.setValidator(QDoubleValidator())
        corr_layout.addWidget(QLabel("k0:"))
        corr_layout.addWidget(self.k0_edit)
        corr_layout.addWidget(QLabel("k1:"))
        corr_layout.addWidget(self.k1_edit)
        corr_layout.addStretch()
        corr_group.setLayout(corr_layout)
        edit_layout.addWidget(corr_group)

        # Члены уравнения (A0-A5)
        members_group = QGroupBox("Члены уравнения")
        members_layout = QVBoxLayout()
        self.equation_members = []

        for i in range(6):  # A0-A5
            member_widget = self.create_member_widget(i)
            self.equation_members.append(member_widget)
            members_layout.addWidget(member_widget)

        members_group.setLayout(members_layout)
        edit_layout.addWidget(members_group)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.cancel_btn = QPushButton("Отменить")
        self.clear_btn = QPushButton("Очистить уравнение")

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()

        edit_layout.addLayout(btn_layout)
        edit_widget.setLayout(edit_layout)

        return edit_widget

    def create_member_widget(self, index):
        """Создает виджет для редактирования члена уравнения"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout()

        # Коэффициент An
        layout.addWidget(QLabel(f"A{index}:"))
        coeff_edit = QLineEdit("0.000000")
        coeff_edit.setFixedWidth(100)
        coeff_edit.setValidator(QDoubleValidator())
        layout.addWidget(coeff_edit)

        # Операнды и операция (только для A1-A5)
        if index > 0:  # Для A0 операнды не нужны
            element1_combo = QComboBox()
            element1_combo.setFixedWidth(120)
            element2_combo = QComboBox()
            element2_combo.setFixedWidth(120)
            operation_combo = QComboBox()
            operation_combo.setFixedWidth(200)

            # Заполняем комбобоксы
            self.populate_operand_combos(element1_combo, element2_combo)
            self.populate_operation_combo(operation_combo)

            layout.addWidget(QLabel("Элемент №1:"))
            layout.addWidget(element1_combo)
            layout.addWidget(QLabel("Элемент №2:"))
            layout.addWidget(element2_combo)
            layout.addWidget(QLabel("Операция:"))
            layout.addWidget(operation_combo)

            # Сохраняем ссылки на виджеты
            widget.element1_combo = element1_combo
            widget.element2_combo = element2_combo
            widget.operation_combo = operation_combo
        else:
            # Для A0 создаем заглушки
            widget.element1_combo = None
            widget.element2_combo = None
            widget.operation_combo = None
            # Добавляем пустое пространство
            layout.addStretch()

        layout.addStretch()
        widget.setLayout(layout)

        # Сохраняем ссылки на виджеты
        widget.coeff_edit = coeff_edit

        return widget

    def populate_operand_combos(self, combo1, combo2):
        """Заполняет комбобоксы операндов"""
        combo1.clear()
        combo2.clear()
        combo1.addItem("---", 0)
        combo2.addItem("---", 0)

        for item in self.range_config:
            if isinstance(item, dict):
                number = item.get('number', 0)
                name = item.get('name', '').strip()
                if name and name != '-':
                    # Добавляем 1 к номеру для соответствия базе данных
                    combo1.addItem(name, number)
                    combo2.addItem(name, number)

    def populate_operation_combo(self, combo):
        """Заполняет комбобокс операций"""
        combo.clear()
        operations = [
            ("---", 0),
            ("X1", 1),
            ("X1 * X2", 2),
            ("X1 / X2", 3),
            ("X1 * X1", 4),
            ("1 / X1", 5),
            ("X1 / X2 * X2", 6),
            ("1 / X1 * X1", 7)
        ]

        for text, value in operations:
            combo.addItem(text, value)

    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        self.product_combo.currentIndexChanged.connect(self.on_product_or_model_changed)
        self.model_combo.currentIndexChanged.connect(self.on_product_or_model_changed)
        self.table_widget.cellClicked.connect(self.on_table_cell_clicked)
        self.save_btn.clicked.connect(self.save_equation_changes)
        self.cancel_btn.clicked.connect(self.cancel_editing)
        self.clear_btn.clicked.connect(self.clear_equation)

    def on_product_or_model_changed(self, index):
        """Обработчик изменения продукта или модели - скрывает окно редактирования и перезагружает конфигурации"""
        # Скрываем окно редактирования
        self.edit_widget.setVisible(False)
        self.current_editing_row = None
        self.current_equation_data = None

        # Перезагружаем конфигурационные файлы
        self.elements_config = self._load_elements_config()
        self.range_config = self._load_range_config()

        # Перезагружаем данные
        self.load_equations()

    def load_equations(self):
        """Загружает уравнения из базы данных только для сконфигурированных элементов"""
        try:
            product_nmb = self.product_combo.currentIndex() + 1
            model_nmb = self.model_combo.currentIndex() + 1

            # Получаем номера сконфигурированных элементов
            configured_numbers = self._get_configured_element_numbers()

            if not configured_numbers:
                self.table_widget.setRowCount(0)
                QMessageBox.information(self, "Информация", "Нет сконфигурированных элементов.")
                return

            # Формируем условие WHERE для выборки только сконфигурированных элементов
            placeholders = ','.join(['?' for _ in configured_numbers])
            query = f"""
            SELECT * FROM PR_SET 
            WHERE pr_nmb = ? AND mdl_nmb = ? AND el_nmb IN ({placeholders})
            ORDER BY el_nmb
            """

            params = [product_nmb, model_nmb] + configured_numbers
            results = self.db.fetch_all(query, params)

            if not results:
                self.table_widget.setRowCount(0)
                QMessageBox.information(self, "Информация", "Данные для выбранного продукта и модели не найдены.")
                return

            self.table_widget.setRowCount(len(results))

            for row_idx, row in enumerate(results):
                equation = self._build_equation(row)
                correction_coeffs = self._build_correction_coeffs(row)

                # Колонка с коэффициентами корректировки
                coeff_item = QTableWidgetItem(correction_coeffs)
                coeff_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table_widget.setItem(row_idx, 0, coeff_item)

                # Колонка с уравнениями
                equation_item = QTableWidgetItem(equation)
                equation_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table_widget.setItem(row_idx, 1, equation_item)

                # Сохраняем исходные данные для редактирования
                self.table_widget.item(row_idx, 0).setData(Qt.UserRole, row)
                self.table_widget.item(row_idx, 1).setData(Qt.UserRole, row)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки уравнений: {str(e)}")
            self.table_widget.setRowCount(0)

    def on_table_cell_clicked(self, row, column):
        """Обработчик клика по ячейке таблицы"""
        if column == 1:  # Клик по уравнению
            self.load_equation_for_editing(row)

    def load_equation_for_editing(self, row):
        """Загружает уравнение для редактирования с проверкой конфигурационных файлов"""
        try:
            # Получаем данные уравнения
            item = self.table_widget.item(row, 1)
            if not item:
                return

            equation_data = item.data(Qt.UserRole)
            if not equation_data:
                return

            # Перезагружаем конфигурационные файлы для актуальных данных
            self.elements_config = self._load_elements_config()
            self.range_config = self._load_range_config()

            # Обновляем комбобоксы с новыми данными
            self.update_all_combos()

            self.current_editing_row = row
            self.current_equation_data = equation_data.copy()

            # Заполняем поля редактора
            pr_nmb = equation_data.get('pr_nmb', 0)
            mdl_nmb = equation_data.get('mdl_nmb', 0)
            el_nmb = equation_data.get('el_nmb', 0)
            element_name = self._get_element_name(el_nmb)

            self.product_model_label.setText(f"Продукт №{pr_nmb}  Модель №{mdl_nmb}  Элемент: {element_name}")

            # Устанавливаем тип измерения
            meas_type = equation_data.get('meas_type', 0)
            if meas_type == 0:
                self.regression_radio.setChecked(True)
            else:
                self.correlation_radio.setChecked(True)

            # Заполняем критерии и диапазоны
            self.water_crit_edit.setText(str(equation_data.get('water_crit', 0)))
            self.empty_crit_edit.setText(str(equation_data.get('empty_crit', 0)))
            self.c_min_edit.setText(str(equation_data.get('c_min', 0)))
            self.c_max_edit.setText(str(equation_data.get('c_max', 0)))

            # Заполняем коэффициенты корректировки
            if meas_type == 0:
                self.k0_edit.setText(str(equation_data.get('k_i_klin00', 0)))
                self.k1_edit.setText(str(equation_data.get('k_i_klin01', 0)))
            else:
                self.k0_edit.setText(str(equation_data.get('k_c_klin00', 0)))
                self.k1_edit.setText(str(equation_data.get('k_c_klin01', 0)))

            # Заполняем члены уравнения
            for i in range(6):
                member_widget = self.equation_members[i]

                # Коэффициент
                if meas_type == 0:
                    coeff_value = equation_data.get(f'k_i_alin{i:02d}', 0)
                else:
                    coeff_value = equation_data.get(f'k_c_alin{i:02d}', 0)
                member_widget.coeff_edit.setText(str(coeff_value))

                # Операнды и операции (только для A1-A5)
                if i > 0 and member_widget.element1_combo:  # Для A1-A5
                    if meas_type == 0:
                        element1_value = equation_data.get(f'operand_i_01_{i:02d}', 0)
                        element2_value = equation_data.get(f'operand_i_02_{i:02d}', 0)
                        operation_value = equation_data.get(f'operator_i_{i:02d}', 0)
                    else:
                        element1_value = equation_data.get(f'operand_c_01_{i:02d}', 0)
                        element2_value = equation_data.get(f'operand_c_02_{i:02d}', 0)
                        operation_value = equation_data.get(f'operator_c_{i:02d}', 0)

                    # Устанавливаем значения в комбобоксы (прибавляем 1 для корректного отображения)
                    self.set_combo_value(member_widget.element1_combo, element1_value + 1 if element1_value > 0 else 0)
                    self.set_combo_value(member_widget.element2_combo, element2_value + 1 if element2_value > 0 else 0)
                    self.set_combo_value(member_widget.operation_combo, operation_value)

            self.edit_widget.setVisible(True)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки уравнения для редактирования: {str(e)}")

    def update_all_combos(self):
        """Обновляет все комбобоксы с новыми данными из конфигурационных файлов"""
        # Обновляем комбобоксы операндов для каждого члена уравнения
        for member_widget in self.equation_members:
            if hasattr(member_widget, 'element1_combo') and member_widget.element1_combo:
                self.populate_operand_combos(member_widget.element1_combo, member_widget.element2_combo)
            if hasattr(member_widget, 'operation_combo') and member_widget.operation_combo:
                self.populate_operation_combo(member_widget.operation_combo)

    def set_combo_value(self, combo, value):
        """Устанавливает значение в комбобокс по данным"""
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)  # Устанавливаем значение по умолчанию

    def save_equation_changes(self):
        """Сохраняет изменения уравнения в базу"""
        try:
            if self.current_editing_row is None or not self.current_equation_data:
                return

            # Собираем данные из полей редактора
            meas_type = 0 if self.regression_radio.isChecked() else 1
            el_nmb = self.current_equation_data.get('el_nmb', 0)
            pr_nmb = self.current_equation_data.get('pr_nmb', 0)
            mdl_nmb = self.current_equation_data.get('mdl_nmb', 0)

            # Подготавливаем данные для обновления
            update_data = {
                'meas_type': meas_type,
                'pr_nmb': pr_nmb,
                'mdl_nmb': mdl_nmb,
                'el_nmb': el_nmb,
                'water_crit': float(self.water_crit_edit.text()) if self.water_crit_edit.text() else 0,
                'empty_crit': float(self.empty_crit_edit.text()) if self.empty_crit_edit.text() else 0,
                'c_min': float(self.c_min_edit.text()) if self.c_min_edit.text() else 0,
                'c_max': float(self.c_max_edit.text()) if self.c_max_edit.text() else 0
            }

            # Коэффициенты корректировки
            if meas_type == 0:
                update_data['k_i_klin00'] = float(self.k0_edit.text()) if self.k0_edit.text() else 0
                update_data['k_i_klin01'] = float(self.k1_edit.text()) if self.k1_edit.text() else 0
            else:
                update_data['k_c_klin00'] = float(self.k0_edit.text()) if self.k0_edit.text() else 0
                update_data['k_c_klin01'] = float(self.k1_edit.text()) if self.k1_edit.text() else 0

            # Члены уравнения
            for i in range(6):
                member_widget = self.equation_members[i]
                coeff_value = float(member_widget.coeff_edit.text()) if member_widget.coeff_edit.text() else 0

                if meas_type == 0:
                    update_data[f'k_i_alin{i:02d}'] = coeff_value
                    # Операнды и операции только для A1-A5
                    if i > 0 and member_widget.element1_combo:
                        element1_value = member_widget.element1_combo.itemData(
                            member_widget.element1_combo.currentIndex())
                        element2_value = member_widget.element2_combo.itemData(
                            member_widget.element2_combo.currentIndex())
                        operation_value = member_widget.operation_combo.itemData(
                            member_widget.operation_combo.currentIndex())
                        # Вычитаем 1 из номера для соответствия базе данных
                        update_data[f'operand_i_01_{i:02d}'] = element1_value - 1 if element1_value > 0 else 0
                        update_data[f'operand_i_02_{i:02d}'] = element2_value - 1 if element2_value > 0 else 0
                        update_data[f'operator_i_{i:02d}'] = operation_value if operation_value else 0
                else:
                    update_data[f'k_c_alin{i:02d}'] = coeff_value
                    # Операнды и операции только для A1-A5
                    if i > 0 and member_widget.element1_combo:
                        element1_value = member_widget.element1_combo.itemData(
                            member_widget.element1_combo.currentIndex())
                        element2_value = member_widget.element2_combo.itemData(
                            member_widget.element2_combo.currentIndex())
                        operation_value = member_widget.operation_combo.itemData(
                            member_widget.operation_combo.currentIndex())
                        # Вычитаем 1 из номера для соответствия базе данных
                        update_data[f'operand_c_01_{i:02d}'] = element1_value - 1 if element1_value > 0 else 0
                        update_data[f'operand_c_02_{i:02d}'] = element2_value - 1 if element2_value > 0 else 0
                        update_data[f'operator_c_{i:02d}'] = operation_value if operation_value else 0

            # Формируем SQL запрос
            if meas_type == 0:
                query = """
                UPDATE PR_SET SET 
                meas_type = ?, water_crit = ?, empty_crit = ?, c_min = ?, c_max = ?,
                k_i_klin00 = ?, k_i_klin01 = ?,
                k_i_alin00 = ?, 
                k_i_alin01 = ?, operand_i_01_01 = ?, operand_i_02_01 = ?, operator_i_01 = ?,
                k_i_alin02 = ?, operand_i_01_02 = ?, operand_i_02_02 = ?, operator_i_02 = ?,
                k_i_alin03 = ?, operand_i_01_03 = ?, operand_i_02_03 = ?, operator_i_03 = ?,
                k_i_alin04 = ?, operand_i_01_04 = ?, operand_i_02_04 = ?, operator_i_04 = ?,
                k_i_alin05 = ?, operand_i_01_05 = ?, operand_i_02_05 = ?, operator_i_05 = ?
                WHERE pr_nmb = ? AND mdl_nmb = ? AND el_nmb = ?
                """
                params = [
                    meas_type,
                    update_data['water_crit'], update_data['empty_crit'], update_data['c_min'], update_data['c_max'],
                    update_data['k_i_klin00'], update_data['k_i_klin01'],
                    update_data['k_i_alin00'],
                    update_data['k_i_alin01'], update_data['operand_i_01_01'], update_data['operand_i_02_01'],
                    update_data['operator_i_01'],
                    update_data['k_i_alin02'], update_data['operand_i_01_02'], update_data['operand_i_02_02'],
                    update_data['operator_i_02'],
                    update_data['k_i_alin03'], update_data['operand_i_01_03'], update_data['operand_i_02_03'],
                    update_data['operator_i_03'],
                    update_data['k_i_alin04'], update_data['operand_i_01_04'], update_data['operand_i_02_04'],
                    update_data['operator_i_04'],
                    update_data['k_i_alin05'], update_data['operand_i_01_05'], update_data['operand_i_02_05'],
                    update_data['operator_i_05'],
                    pr_nmb, mdl_nmb, el_nmb
                ]
            else:
                query = """
                UPDATE PR_SET SET 
                meas_type = ?, water_crit = ?, empty_crit = ?, c_min = ?, c_max = ?,
                k_c_klin00 = ?, k_c_klin01 = ?,
                k_c_alin00 = ?, 
                k_c_alin01 = ?, operand_c_01_01 = ?, operand_c_02_01 = ?, operator_c_01 = ?,
                k_c_alin02 = ?, operand_c_01_02 = ?, operand_c_02_02 = ?, operator_c_02 = ?,
                k_c_alin03 = ?, operand_c_01_03 = ?, operand_c_02_03 = ?, operator_c_03 = ?,
                k_c_alin04 = ?, operand_c_01_04 = ?, operand_c_02_04 = ?, operator_c_04 = ?,
                k_c_alin05 = ?, operand_c_01_05 = ?, operand_c_02_05 = ?, operator_c_05 = ?
                WHERE pr_nmb = ? AND mdl_nmb = ? AND el_nmb = ?
                """
                params = [
                    meas_type,
                    update_data['water_crit'], update_data['empty_crit'], update_data['c_min'], update_data['c_max'],
                    update_data['k_c_klin00'], update_data['k_c_klin01'],
                    update_data['k_c_alin00'],
                    update_data['k_c_alin01'], update_data['operand_c_01_01'], update_data['operand_c_02_01'],
                    update_data['operator_c_01'],
                    update_data['k_c_alin02'], update_data['operand_c_01_02'], update_data['operand_c_02_02'],
                    update_data['operator_c_02'],
                    update_data['k_c_alin03'], update_data['operand_c_01_03'], update_data['operand_c_02_03'],
                    update_data['operator_c_03'],
                    update_data['k_c_alin04'], update_data['operand_c_01_04'], update_data['operand_c_02_04'],
                    update_data['operator_c_04'],
                    update_data['k_c_alin05'], update_data['operand_c_01_05'], update_data['operand_c_02_05'],
                    update_data['operator_c_05'],
                    pr_nmb, mdl_nmb, el_nmb
                ]

            # Выполняем обновление
            self.db.execute(query, params)

            # Обновляем таблицу
            self.load_equations()

            # Не скрываем область редактирования - оставляем открытой
            # self.edit_widget.setVisible(False)
            # self.current_editing_row = None
            # self.current_equation_data = None

            QMessageBox.information(self, "Успех", "Уравнение успешно сохранено!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения уравнения: {str(e)}")

    def cancel_editing(self):
        """Отменяет редактирование"""
        self.edit_widget.setVisible(False)
        self.current_editing_row = None
        self.current_equation_data = None

    def clear_equation(self):
        """Очищает введенное уравнение"""
        try:
            # Очищаем коэффициенты корректировки
            self.k0_edit.setText("0")
            self.k1_edit.setText("0")

            # Очищаем критерии и диапазоны
            self.water_crit_edit.setText("0")
            self.empty_crit_edit.setText("0")
            self.c_min_edit.setText("0")
            self.c_max_edit.setText("0")

            # Очищаем члены уравнения
            for i in range(6):
                member_widget = self.equation_members[i]
                member_widget.coeff_edit.setText("0")

                # Очищаем операнды и операции (только для A1-A5)
                if i > 0 and member_widget.element1_combo:
                    member_widget.element1_combo.setCurrentIndex(0)
                    member_widget.element2_combo.setCurrentIndex(0)
                    member_widget.operation_combo.setCurrentIndex(0)

            QMessageBox.information(self, "Успех", "Уравнение очищено!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка очистки уравнения: {str(e)}")

    def _build_correction_coeffs(self, row: dict) -> str:
        """Формирует строку с коэффициентами корректировки"""
        meas_type = row.get('meas_type', 0)
        coeffs = []

        if meas_type == 0:  # Интенсивности
            k0 = row.get('k_i_klin00', 0)
            k1 = row.get('k_i_klin01', 0)
            coeffs.append(f"k0 = {self._format_number(k0)}")
            coeffs.append(f"k1 = {self._format_number(k1)}")
        else:  # Концентрации
            k0 = row.get('k_c_klin00', 0)
            k1 = row.get('k_c_klin01', 0)
            coeffs.append(f"k0 = {self._format_number(k0)}")
            coeffs.append(f"k1 = {self._format_number(k1)}")

        return "\n".join(coeffs)

    def _format_number(self, num) -> str:
        """Форматирование числа с удалением лишних нулей"""
        if num == 0:
            return "0"
        return f"{float(num):.9f}".rstrip('0').rstrip('.')

    def _build_equation(self, row: dict) -> str:
        """Формирует строку с уравнением"""
        el_nmb = row.get('el_nmb', 0)
        element_name = self._get_element_name(el_nmb)
        meas_type = row.get('meas_type', 0)

        equation_parts = [f"C({element_name}) = "]

        # Нулевой коэффициент
        if meas_type == 0:
            k0 = row.get('k_i_alin00', 0)
        else:
            k0 = row.get('k_c_alin00', 0)

        equation_parts.append(self._format_number(k0))

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

            expression = self._build_expression(operand1, operand2, operator, meas_type)

            if expression == "0":
                continue

            sign = "+" if k_value > 0 else "-"
            abs_k_value = abs(k_value)
            formatted_k = self._format_number(abs_k_value)
            equation_parts.append(f" {sign} {formatted_k}*({expression})")

        return "".join(equation_parts)

    def _build_expression(self, operand1: int, operand2: int, operator: int, meas_type: int) -> str:
        """Формирует математическое выражение на основе operand'ов и operator"""
        prefix = "I_" if meas_type == 0 else "C_"

        # Проверка на допустимость оператора
        if operator == 7 and meas_type != 0:
            return "0"  # Оператор 7 недоступен для концентраций

        if operator == 0:  # 0 - пустая операция
            return "0"

        elif operator == 1:  # 1 - берем только operand_i_01_01
            if operand1 > 0:
                name1 = self._get_range_name(operand1)
                return f"{prefix}{name1}"
            return "0"

        elif operator == 2:  # 2 - operand_i_01_01 * operand_i_02_01
            if operand1 > 0 and operand2 > 0:
                name1 = self._get_range_name(operand1)
                name2 = self._get_range_name(operand2)
                return f"{prefix}{name1}*{prefix}{name2}"
            return "0"

        elif operator == 3:  # 3 - operand_i_01_01 / operand_i_02_01
            if operand1 > 0 and operand2 > 0:
                name1 = self._get_range_name(operand1)
                name2 = self._get_range_name(operand2)
                return f"{prefix}{name1}/{prefix}{name2}"
            return "0"

        elif operator == 4:  # 4 - operand_i_01_01 * operand_i_01_01
            if operand1 > 0:
                name1 = self._get_range_name(operand1)
                return f"{prefix}{name1}*{prefix}{name1}"
            return "0"

        elif operator == 5:  # 5 - 1 / operand_i_01_01
            if operand1 > 0:
                name1 = self._get_range_name(operand1)
                return f"1/{prefix}{name1}"
            return "0"

        elif operator == 6:  # 6 - operand_i_01_01 / operand_i_02_01 * operand_i_02_01
            if operand1 > 0 and operand2 > 0:
                name1 = self._get_range_name(operand1)
                name2 = self._get_range_name(operand2)
                return f"{prefix}{name1}/{prefix}{name2}*{prefix}{name2}"
            return "0"

        elif operator == 7:  # 7 - 1 / operand_i_01_01 * operand_i_01_01
            if operand1 > 0:
                name1 = self._get_range_name(operand1)
                return f"1/{prefix}{name1}*{prefix}{name1}"
            return "0"

        return "0"

    def _get_element_name(self, el_nmb: int) -> str:
        """Получает имя элемента по его номеру"""
        for element in self.elements_config:
            if isinstance(element, dict) and element.get('number') == el_nmb:
                return element.get('name', f"Element_{el_nmb}")
        return f"Element_{el_nmb}"

    def _get_range_name(self, range_nmb: int) -> str:
        """Получает имя диапазона по его номеру"""
        if range_nmb <= 0:
            return ""

        for range_item in self.range_config:
            if isinstance(range_item, dict) and range_item.get('number') == range_nmb + 1:
                return range_item.get('name', f"Range_{range_nmb}")
        return f"Range_{range_nmb}"

    def showEvent(self, event):
        """Обработчик события показа виджета - скрывает редактор и обновляет конфигурации"""
        super().showEvent(event)

        # Скрываем окно редактирования
        self.edit_widget.setVisible(False)
        self.current_editing_row = None
        self.current_equation_data = None

        # Перезагружаем конфигурационные файлы
        self.elements_config = self._load_elements_config()
        self.range_config = self._load_range_config()

        # Загружаем данные
        self.load_equations()
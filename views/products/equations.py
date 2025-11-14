from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QFrame,
                               QHBoxLayout, QSplitter, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox, QLineEdit, QRadioButton,
                               QButtonGroup, QPushButton, QGroupBox, QFormLayout,
                               QScrollArea, QApplication, QDialog, QTextEdit,
                               QDialogButtonBox, QTabWidget)
from PySide6.QtGui import QDoubleValidator, QIntValidator, QValidator
from PySide6.QtCore import Qt, QRegularExpression
import json
import re
from database.db import Database
from pathlib import Path
from config import AC_COUNT, PR_COUNT, DB_CONFIG





class EquationsPage(QWidget):
    """Виджет для отображения уравнений расчета концентраций"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}
        self._config_dir = self._get_config_directory()
        self.elements_config = self._load_elements_config()
        self.range_config = self._load_range_config()
        self.lines_math_config = self._load_lines_math_config()
        self.math_config = self._load_math_config()
        self.current_editing_row = None
        self.current_equation_data = None
        self.current_intensity_data = None  # Данные границ интенсивности
        self.init_ui()
        self.setup_connections()

    def _get_config_directory(self) -> Path:
        """Получает путь к директории конфигурации"""
        base_dir = Path(__file__).parent
        config_dir = base_dir.parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        return config_dir

    def _load_config_file(self, filename: str) -> dict:
        """Загружает конфигурационный файл JSON"""
        config_path = self._config_dir / filename

        if not config_path.exists():
            print(f"Файл конфигурации не найден: {config_path}")
            return {}

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки файла {filename}: {e}")
            return {}

    def _load_elements_config(self) -> list:
        """Загружает конфигурацию элементов"""
        return self._load_config_file("elements.json")

    def _load_range_config(self) -> list:
        """Загружает конфигурацию диапазонов"""
        return self._load_config_file("range.json")

    def _load_lines_math_config(self) -> dict:
        """Загружает конфигурацию математических операций для линий"""
        return self._load_config_file("lines_math_interactions.json")

    def _load_math_config(self) -> dict:
        """Загружает конфигурацию математических операций для элементов"""
        return self._load_config_file("math_interactions.json")

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

    def _safe_float_convert(self, text, field_name=""):
        """Безопасно преобразует строку в float, поддерживая научную нотацию и запятые"""
        if not text or text.strip() == '':
            return 0.0

        # Очищаем и нормализуем текст
        cleaned = text.strip()

        # Проверяем, соответствует ли текст шаблону числа
        pattern = re.compile(r'^[-+]?(\d+([.,]\d*)?|[.,]\d+)([eEЕе][-+]?\d+)?$')
        if not pattern.match(cleaned):
            error_msg = f"Некорректный формат числа в поле '{field_name}': {text}\n\n"
            error_msg += "Допустимые форматы:\n"
            error_msg += "- Обычные числа: 1.5, -2.3, 0.001\n"
            error_msg += "- С запятой: 1,5, 0,001\n"
            error_msg += "- Научная нотация: 3.79e-01, 1.5E+02, 2,3е-5\n"
            error_msg += "- С русской Е: 3.79Е-01\n\n"
            error_msg += "Примеры: 0.5, -2.1, 3.79e-5, 1,5Е+03"
            raise ValueError(error_msg)

        # Нормализуем для преобразования
        cleaned = cleaned.replace(',', '.').lower()
        cleaned = cleaned.replace('е', 'e')  # русская е в английскую

        try:
            return float(cleaned)
        except ValueError as e:
            error_msg = f"Ошибка преобразования числа в поле '{field_name}': {text}\n"
            error_msg += f"Ошибка: {str(e)}"
            raise ValueError(error_msg)

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(800)

        # Используем переменные из config
        ac_count = AC_COUNT
        pr_count = PR_COUNT

        title = QLabel("Ввод уравнений связи")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Верхняя панель с комбобоксами
        top_frame = QFrame()
        top_frame.setFrameStyle(QFrame.StyledPanel)
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
        products = [f"Продукт {i}" for i in range(1, pr_count + 1)]
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

        # === Область редактирования с вкладками ===
        self.edit_widget = QGroupBox("Редактирование")
        edit_layout = QVBoxLayout()

        # Создаем вкладки
        self.tab_widget = QTabWidget()

        # Вкладка уравнения
        self.equation_tab = self.create_equation_tab()
        self.intensity_tab = self.create_intensity_tab()

        self.tab_widget.addTab(self.equation_tab, "Уравнение")
        self.tab_widget.addTab(self.intensity_tab, "Границы интенсивности")

        edit_layout.addWidget(self.tab_widget)

        # Кнопки управления (общие для всех вкладок)
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.apply_to_btn = QPushButton("Применить для...")
        self.cancel_btn = QPushButton("Отменить")
        self.clear_btn = QPushButton("Очистить уравнение")

        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.apply_to_btn)
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()

        edit_layout.addLayout(btn_layout)
        self.edit_widget.setLayout(edit_layout)

        main_layout.addWidget(self.edit_widget)
        self.edit_widget.setVisible(False)

    def create_equation_tab(self):
        """Создает вкладку для редактирования уравнения"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)

        # Первая строка: Продукт №  Модель № Элемент:
        header_layout1 = QHBoxLayout()
        self.product_model_label = QLabel("Продукт №:  Модель №:  Элемент: ")
        header_layout1.addWidget(self.product_model_label)
        header_layout1.addStretch()
        layout.addLayout(header_layout1)

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
        layout.addLayout(header_layout2)

        # Третья строка: Критерии и диапазоны концентраций
        criteria_layout = QHBoxLayout()

        # Критерий Вода и C мин
        water_label = QLabel("Критерий \"Вода\":")
        water_label.setFixedWidth(150)
        self.water_crit_edit = QLineEdit()
        self.water_crit_edit.setFixedWidth(100)
        self.water_crit_edit.setValidator(ScientificDoubleValidator())

        # Выбор линии для критерия
        self.w_element_combo = QComboBox()
        self.w_element_combo.setFixedWidth(100)
        self.populate_operand_combos(self.w_element_combo)

        # Выбор знака <= 0 ; > 1 bool
        self.w_operator_combo = QComboBox()
        self.w_operator_combo.setFixedWidth(50)
        self.populate_operator_combos(self.w_operator_combo)

        cmin_label = QLabel("C мин:")
        cmin_label.setFixedWidth(50)
        self.c_min_edit = QLineEdit()
        self.c_min_edit.setFixedWidth(100)
        self.c_min_edit.setValidator(ScientificDoubleValidator())

        criteria_layout.addWidget(water_label)
        criteria_layout.addWidget(self.w_element_combo)
        criteria_layout.addWidget(self.w_operator_combo)
        criteria_layout.addWidget(self.water_crit_edit)
        criteria_layout.addSpacing(10)
        criteria_layout.addWidget(cmin_label)
        criteria_layout.addWidget(self.c_min_edit)
        criteria_layout.addStretch()

        layout.addLayout(criteria_layout)

        # Четвертая строка: Критерий Пусто и C макс
        empty_layout = QHBoxLayout()

        # Критерий Пусто и C макс
        empty_label = QLabel("Критерий \"Пусто\"")
        empty_label.setFixedWidth(150)
        self.empty_crit_edit = QLineEdit()
        self.empty_crit_edit.setFixedWidth(100)
        self.empty_crit_edit.setValidator(ScientificDoubleValidator())

        # Выбор линии для критерия
        self.e_element_combo = QComboBox()
        self.e_element_combo.setFixedWidth(100)
        self.populate_operand_combos(self.e_element_combo)

        # Выбор знака <= 0 ; > 1 bool
        self.e_operator_combo = QComboBox()
        self.e_operator_combo.setFixedWidth(50)
        self.populate_operator_combos(self.e_operator_combo)

        cmax_label = QLabel("C макс:")
        cmax_label.setFixedWidth(50)
        self.c_max_edit = QLineEdit()
        self.c_max_edit.setFixedWidth(100)
        self.c_max_edit.setValidator(ScientificDoubleValidator())

        empty_layout.addWidget(empty_label)
        empty_layout.addWidget(self.e_element_combo)
        empty_layout.addWidget(self.e_operator_combo)
        empty_layout.addWidget(self.empty_crit_edit)
        empty_layout.addSpacing(10)
        empty_layout.addWidget(cmax_label)
        empty_layout.addWidget(self.c_max_edit)
        empty_layout.addStretch()

        layout.addLayout(empty_layout)

        # Коэффициенты корректировки
        corr_group = QGroupBox("Коэффициенты корректировки")
        corr_layout = QHBoxLayout()
        self.k0_edit = QLineEdit()
        self.k0_edit.setFixedWidth(120)
        self.k0_edit.setValidator(ScientificDoubleValidator())
        self.k1_edit = QLineEdit()
        self.k1_edit.setFixedWidth(120)
        self.k1_edit.setValidator(ScientificDoubleValidator())
        corr_layout.addWidget(QLabel("k0:"))
        corr_layout.addWidget(self.k0_edit)
        corr_layout.addWidget(QLabel("k1:"))
        corr_layout.addWidget(self.k1_edit)
        corr_layout.addStretch()
        corr_group.setLayout(corr_layout)
        layout.addWidget(corr_group)

        # Члены уравнения (A0-A5)
        members_group = QGroupBox("Члены уравнения")
        members_layout = QVBoxLayout()
        self.equation_members = []

        for i in range(6):  # A0-A5
            member_widget = self.create_member_widget(i)
            self.equation_members.append(member_widget)
            members_layout.addWidget(member_widget)

        members_group.setLayout(members_layout)
        layout.addWidget(members_group)

        tab.setLayout(layout)
        return tab

    def create_intensity_tab(self):
        """Создает вкладку для редактирования границ интенсивности"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Границы интенсивности для линий")
        title.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        # Информация о продукте
        info_label = QLabel("Настройка минимальных и максимальных значений интенсивности для каждой линии")
        info_label.setStyleSheet("color: #666;")
        layout.addWidget(info_label)

        # Прокручиваемая область для таблицы
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Контейнер для таблицы
        container = QWidget()
        container_layout = QVBoxLayout(container)

        # Таблица границ интенсивности (теперь 3 колонки вместо 4)
        self.intensity_table = QTableWidget()
        self.intensity_table.setColumnCount(3)  # Уменьшили с 4 до 3
        self.intensity_table.setHorizontalHeaderLabels([
            "Название линии", "I мин", "I макс"  # Убрали "№ линии"
        ])

        # НАСТРОЙКА РАЗМЕРОВ КОЛОНОК
        self.intensity_table.setColumnWidth(0, 180)  # Название линии - увеличили место
        self.intensity_table.setColumnWidth(1, 100)  # I мин
        self.intensity_table.setColumnWidth(2, 100)  # I макс

        self.intensity_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.intensity_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.intensity_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.intensity_table.setAlternatingRowColors(True)
        self.intensity_table.setRowCount(20)  # 20 линий

        container_layout.addWidget(self.intensity_table)
        scroll_area.setWidget(container)
        layout.addWidget(scroll_area)

        tab.setLayout(layout)
        return tab

    def create_member_widget(self, index):
        """Создает виджет для редактирования члена уравнения"""
        widget = QFrame()
        widget.setFrameStyle(QFrame.StyledPanel)
        layout = QHBoxLayout()

        # Коэффициент An
        layout.addWidget(QLabel(f"A{index}:"))
        coeff_edit = QLineEdit("0.000000")
        coeff_edit.setFixedWidth(100)
        coeff_edit.setValidator(ScientificDoubleValidator())
        layout.addWidget(coeff_edit)

        # Один комбобокс вместо трех (только для A1-A5)
        if index > 0:  # Для A0 операнды не нужны
            interaction_combo = QComboBox()
            interaction_combo.setFixedWidth(400)  # Увеличили ширину для длинных описаний

            layout.addWidget(QLabel("Взаимодействие:"))
            layout.addWidget(interaction_combo)

            # Сохраняем ссылки на виджеты
            widget.interaction_combo = interaction_combo
        else:
            # Для A0 создаем заглушки
            widget.interaction_combo = None
            # Добавляем пустое пространство
            layout.addStretch()

        layout.addStretch()
        widget.setLayout(layout)

        # Сохраняем ссылки на виджеты
        widget.coeff_edit = coeff_edit

        return widget

    def populate_operand_combos(self, combo):
        """Заполняет комбобоксы операндов"""
        combo.clear()
        combo.addItem("---", 0)

        for item in self.range_config:
            if isinstance(item, dict):
                number = item.get('number', 0)
                name = item.get('name', '').strip()
                if name and name != '-':
                    # Добавляем 1 к номеру для соответствия базе данных
                    combo.addItem(name, number)

    def populate_operator_combos(self, combo):
        """Заполняет комбобокс неравенством"""
        combo.clear()
        combo.addItem("≤", 1)  # True - меньше или равно
        combo.addItem(">", 0)  # False - строго больше

    def populate_interaction_combo(self, combo, meas_type, current_el_nmb=None):
        """Заполняет комбобокс взаимодействий в зависимости от типа измерения"""
        combo.clear()
        combo.addItem("---", {"x1": 0, "x2": 0, "op": 0})

        if meas_type == 0:  # Регрессия (интенсивности)
            interactions = self.lines_math_config.get('interactions', [])
            for interaction in interactions:
                description = interaction.get('description', '')
                if description:  # Пропускаем пустые описания
                    combo.addItem(description, {
                        'x1': interaction.get('x1', 0),
                        'x2': interaction.get('x2', 0),
                        'op': interaction.get('op', 0)
                    })
        else:  # Корреляция (концентрации)
            if current_el_nmb is not None:
                # Находим interactions для текущего элемента
                element_interactions = self._get_element_interactions(current_el_nmb)
                for interaction in element_interactions:
                    description = interaction.get('description', '')
                    if description:  # Пропускаем пустые описания
                        combo.addItem(description, {
                            'x1': interaction.get('x1', 0),
                            'x2': interaction.get('x2', 0),
                            'op': interaction.get('op', 0)
                        })

    def _get_element_interactions(self, el_nmb):
        """Получает interactions для конкретного элемента"""
        element_name = self._get_element_name(el_nmb)
        interactions_data = self.math_config.get('interactions', [])

        for element_data in interactions_data:
            if element_data.get('element_name') == element_name:
                return element_data.get('interactions', [])
        return []

    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        self.product_combo.currentIndexChanged.connect(self.on_product_or_model_changed)
        self.model_combo.currentIndexChanged.connect(self.on_product_or_model_changed)
        self.apply_to_btn.clicked.connect(self.show_apply_to_dialog)
        self.table_widget.cellClicked.connect(self.on_table_cell_clicked)
        self.save_btn.clicked.connect(self.save_equation_changes)
        self.cancel_btn.clicked.connect(self.cancel_editing)
        self.clear_btn.clicked.connect(self.clear_equation)
        # Добавляем обработчики переключения радиокнопок
        self.regression_radio.toggled.connect(self.on_measurement_type_changed)
        self.correlation_radio.toggled.connect(self.on_measurement_type_changed)

    def on_product_or_model_changed(self, index):
        """Обработчик изменения продукта или модели - скрывает окно редактирования и перезагружает конфигурации"""
        # Скрываем окно редактирования
        self.edit_widget.setVisible(False)
        self.current_editing_row = None
        self.current_equation_data = None
        self.current_intensity_data = None

        # Перезагружаем конфигурационные файлы
        self.elements_config = self._load_elements_config()
        self.range_config = self._load_range_config()
        self.lines_math_config = self._load_lines_math_config()
        self.math_config = self._load_math_config()

        # Перезагружаем данные
        self.load_equations()

    def on_measurement_type_changed(self):
        """Обработчик изменения типа измерения - переключает коэффициенты и комбобоксы"""
        if self.current_equation_data is None:
            return

        # Получаем выбранный тип измерения
        meas_type = 0 if self.regression_radio.isChecked() else 1
        current_el_nmb = self.current_equation_data.get('el_nmb', 0)

        # Обновляем комбобоксы взаимодействий
        for member_widget in self.equation_members:
            if hasattr(member_widget, 'interaction_combo') and member_widget.interaction_combo:
                self.populate_interaction_combo(member_widget.interaction_combo, meas_type, current_el_nmb)

        # Обновляем коэффициенты в соответствии с выбранным типом
        self.update_coefficients_display(meas_type)

    def update_coefficients_display(self, meas_type):
        """Обновляет отображение коэффициентов в соответствии с типом измерения"""
        current_el_nmb = self.current_equation_data.get('el_nmb', 0)

        if meas_type == 0:  # Регрессия
            self.k0_edit.setText(str(self.current_equation_data.get('k_i_klin00', 0)))
            self.k1_edit.setText(str(self.current_equation_data.get('k_i_klin01', 0)))

            for i in range(6):
                coeff_value = self.current_equation_data.get(f'k_i_alin{i:02d}', 0)
                self.equation_members[i].coeff_edit.setText(str(coeff_value))

                if i > 0:  # Для A1-A5 также обновляем взаимодействия
                    element1_value = self.current_equation_data.get(f'operand_i_01_{i:02d}', 0)
                    element2_value = self.current_equation_data.get(f'operand_i_02_{i:02d}', 0)
                    operation_value = self.current_equation_data.get(f'operator_i_{i:02d}', 0)

                    # Находим соответствующее взаимодействие
                    interaction_data = self._find_interaction_by_values(
                        element1_value, element2_value, operation_value, meas_type, current_el_nmb
                    )
                    self.set_combo_interaction_value(self.equation_members[i].interaction_combo, interaction_data)
        else:  # Корреляция
            self.k0_edit.setText(str(self.current_equation_data.get('k_c_klin00', 0)))
            self.k1_edit.setText(str(self.current_equation_data.get('k_c_klin01', 0)))

            for i in range(6):
                coeff_value = self.current_equation_data.get(f'k_c_alin{i:02d}', 0)
                self.equation_members[i].coeff_edit.setText(str(coeff_value))

                if i > 0:  # Для A1-A5 также обновляем взаимодействия
                    element1_value = self.current_equation_data.get(f'operand_c_01_{i:02d}', 0)
                    element2_value = self.current_equation_data.get(f'operand_c_02_{i:02d}', 0)
                    operation_value = self.current_equation_data.get(f'operator_c_{i:02d}', 0)

                    # Находим соответствующее взаимодействие
                    interaction_data = self._find_interaction_by_values(
                        element1_value, element2_value, operation_value, meas_type, current_el_nmb
                    )
                    self.set_combo_interaction_value(self.equation_members[i].interaction_combo, interaction_data)

    def _find_interaction_by_values(self, x1, x2, op, meas_type, current_el_nmb):
        """Находит взаимодействие по значениям x1, x2, op"""
        if meas_type == 0:  # Регрессия
            interactions = self.lines_math_config.get('interactions', [])
            for interaction in interactions:
                if (interaction.get('x1') == x1 and
                        interaction.get('x2') == x2 and
                        interaction.get('op') == op):
                    return interaction
        else:  # Корреляция
            element_interactions = self._get_element_interactions(current_el_nmb)
            for interaction in element_interactions:
                if (interaction.get('x1') == x1 and
                        interaction.get('x2') == x2 and
                        interaction.get('op') == op):
                    return interaction
        return {"x1": 0, "x2": 0, "op": 0}

    def set_combo_interaction_value(self, combo, interaction_data):
        """Устанавливает значение в комбобокс взаимодействий"""
        x1 = interaction_data.get('x1', 0)
        x2 = interaction_data.get('x2', 0)
        op = interaction_data.get('op', 0)

        for i in range(combo.count()):
            item_data = combo.itemData(i)
            if (item_data.get('x1') == x1 and
                    item_data.get('x2') == x2 and
                    item_data.get('op') == op):
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)  # Устанавливаем значение по умолчанию

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
            SELECT * FROM pr_set 
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
                coeff_item.setTextAlignment(Qt.AlignCenter)
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
            self.lines_math_config = self._load_lines_math_config()
            self.math_config = self._load_math_config()

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
            self.set_combo_value(self.w_element_combo, equation_data.get('w_sq_nmb', 0))

            # ИСПРАВЛЕНИЕ: преобразуем boolean в int для комбобокса
            w_operator = 1 if equation_data.get('w_operator', False) else 0
            self.set_combo_value(self.w_operator_combo, w_operator)

            self.empty_crit_edit.setText(str(equation_data.get('empty_crit', 0)))
            self.set_combo_value(self.e_element_combo, equation_data.get('e_sq_nmb', 0))

            # ИСПРАВЛЕНИЕ: преобразуем boolean в int для комбобокса
            e_operator = 1 if equation_data.get('e_operator', False) else 0
            self.set_combo_value(self.e_operator_combo, e_operator)

            self.c_min_edit.setText(str(equation_data.get('c_min', 0)))
            self.c_max_edit.setText(str(equation_data.get('c_max', 0)))

            # Инициализируем комбобоксы взаимодействий в соответствии с типом измерения
            current_el_nmb = equation_data.get('el_nmb', 0)
            for member_widget in self.equation_members:
                if hasattr(member_widget, 'interaction_combo') and member_widget.interaction_combo:
                    self.populate_interaction_combo(member_widget.interaction_combo, meas_type, current_el_nmb)

            # Заполняем коэффициенты в соответствии с текущим типом измерения
            self.update_coefficients_display(meas_type)

            # Загружаем данные границ интенсивности
            self.load_intensity_data(pr_nmb)

            # Подключаем обработчики
            try:
                self.regression_radio.toggled.disconnect(self.on_measurement_type_changed)
                self.correlation_radio.toggled.disconnect(self.on_measurement_type_changed)
            except:
                pass

            self.regression_radio.toggled.connect(self.on_measurement_type_changed)
            self.correlation_radio.toggled.connect(self.on_measurement_type_changed)

            self.edit_widget.setVisible(True)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки уравнения для редактирования: {str(e)}")

    def load_intensity_data(self, pr_nmb):
        """Загружает данные границ интенсивности для выбранного продукта"""
        try:
            # Загружаем данные из таблицы set07
            query = """
            SELECT sq_nmb, ln_nmb, i_min, i_max 
            FROM set07 
            WHERE pr_nmb = ? 
            ORDER BY sq_nmb
            """
            results = self.db.fetch_all(query, [pr_nmb])

            if not results:
                # Если данных нет, создаем пустые строки с значениями по умолчанию
                results = []
                for sq_nmb in range(1, 21):
                    results.append({
                        'sq_nmb': sq_nmb,
                        'ln_nmb': -1,
                        'i_min': 1,
                        'i_max': 1000000
                    })

            self.current_intensity_data = results
            self.update_intensity_table()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки границ интенсивности: {str(e)}")

    def update_intensity_table(self):
        """Обновляет таблицу границ интенсивности"""
        if not self.current_intensity_data:
            return

        self.intensity_table.setRowCount(len(self.current_intensity_data))

        # Устанавливаем размеры колонок при обновлении таблицы (теперь 3 колонки)
        self.intensity_table.setColumnWidth(0, 180)  # Название линии
        self.intensity_table.setColumnWidth(1, 100)  # I мин
        self.intensity_table.setColumnWidth(2, 100)  # I макс

        for row_idx, data in enumerate(self.current_intensity_data):
            sq_nmb = data.get('sq_nmb', 0)
            ln_nmb = data.get('ln_nmb', -1)

            # Получаем название линии
            line_name = self._get_line_name(ln_nmb)

            # 3 колонки:
            # 0: Название линии
            # 1: I мин
            # 2: I макс

            # Название линии
            name_item = QTableWidgetItem(line_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.intensity_table.setItem(row_idx, 0, name_item)

            # I мин
            i_min_item = QTableWidgetItem(str(data.get('i_min', 1)))
            i_min_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.intensity_table.setItem(row_idx, 1, i_min_item)

            # I макс
            i_max_item = QTableWidgetItem(str(data.get('i_max', 1000000)))
            i_max_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.intensity_table.setItem(row_idx, 2, i_max_item)

    def _get_line_name(self, ln_nmb):
        """Получает название линии по номеру"""
        if ln_nmb == -1:
            return "Не используется"

        # Сопоставление номеров линий с названиями из range.json
        for range_item in self.range_config:
            if isinstance(range_item, dict) and range_item.get('number') == ln_nmb:
                return range_item.get('name', f"Линия {ln_nmb}")

        # Если не найдено в конфиге, используем стандартные названия
        line_names = {
            1: "INT", 2: "NC", 21: "Fe_Ka", 23: "Co_Ka",
            25: "Ni_Ka", 27: "Cu_Ka"
        }
        return line_names.get(ln_nmb, f"Линия {ln_nmb}")

    def update_all_combos(self):
        """Обновляет все комбобоксы с новыми данными из конфигурационных файлов"""
        # Обновляем комбобоксы операндов для каждого члена уравнения
        for member_widget in self.equation_members:
            if hasattr(member_widget, 'interaction_combo') and member_widget.interaction_combo:
                # Комбобоксы взаимодействий будут обновляться при смене типа измерения
                pass
        self.populate_operand_combos(self.e_element_combo)
        self.populate_operand_combos(self.w_element_combo)

    def set_combo_value(self, combo, value):
        """Устанавливает значение в комбобокс по данным"""
        for i in range(combo.count()):
            if combo.itemData(i) == value:
                combo.setCurrentIndex(i)
                return
        combo.setCurrentIndex(0)  # Устанавливаем значение по умолчанию

    def save_equation_changes(self, product_numbers: list[int] | None = None, model_numbers: list[int] | None = None):
        """
        Сохраняет изменения уравнения в базу.
        Если product_numbers и model_numbers переданы, применяет изменения массово.
        """
        try:
            if self.current_editing_row is None or not self.current_equation_data:
                if product_numbers is False or model_numbers is None:
                    QMessageBox.warning(self, "Ошибка", "Нет активного уравнения для сохранения.")
                    return

            # Собираем данные из полей редактора
            meas_type = 0 if self.regression_radio.isChecked() else 1
            el_nmb = self.current_equation_data.get('el_nmb', 0)

            # Подготавливаем данные для обновления
            update_data = {
                'meas_type': meas_type,
                'el_nmb': el_nmb,
            }

            # Определяем, обновлять ли критерии и диапазоны
            update_criteria = product_numbers is False and model_numbers is None

            if update_criteria:
                # Обычное сохранение - обновляем ВСЕ поля
                # ИСПРАВЛЕНИЕ: преобразуем операторы в boolean
                w_operator_value = bool(self.w_operator_combo.itemData(self.w_operator_combo.currentIndex()))
                e_operator_value = bool(self.e_operator_combo.itemData(self.e_operator_combo.currentIndex()))

                update_data.update({
                    'water_crit': self._safe_float_convert(self.water_crit_edit.text(), "Критерий Вода"),
                    'w_sq_nmb': self.w_element_combo.itemData(self.w_element_combo.currentIndex()),
                    'w_operator': w_operator_value,
                    'empty_crit': self._safe_float_convert(self.empty_crit_edit.text(), "Критерий Пусто"),
                    'e_sq_nmb': self.e_element_combo.itemData(self.e_element_combo.currentIndex()),
                    'e_operator': e_operator_value,
                    'c_min': self._safe_float_convert(self.c_min_edit.text(), "C мин"),
                    'c_max': self._safe_float_convert(self.c_max_edit.text(), "C макс")
                })

            # Коэффициенты корректировки
            if meas_type == 0:
                update_data['k_i_klin00'] = self._safe_float_convert(self.k0_edit.text(), "k0")
                update_data['k_i_klin01'] = self._safe_float_convert(self.k1_edit.text(), "k1")
            else:
                update_data['k_c_klin00'] = self._safe_float_convert(self.k0_edit.text(), "k0")
                update_data['k_c_klin01'] = self._safe_float_convert(self.k1_edit.text(), "k1")

            # Члены уравнения
            for i in range(6):
                member_widget = self.equation_members[i]
                coeff_value = self._safe_float_convert(member_widget.coeff_edit.text(), f"A{i}")

                if meas_type == 0:
                    update_data[f'k_i_alin{i:02d}'] = coeff_value
                    if i > 0 and member_widget.interaction_combo:
                        interaction_data = member_widget.interaction_combo.itemData(
                            member_widget.interaction_combo.currentIndex())
                        if interaction_data:
                            update_data[f'operand_i_01_{i:02d}'] = interaction_data.get('x1', 0)
                            update_data[f'operand_i_02_{i:02d}'] = interaction_data.get('x2', 0)
                            update_data[f'operator_i_{i:02d}'] = interaction_data.get('op', 0)
                else:
                    update_data[f'k_c_alin{i:02d}'] = coeff_value
                    if i > 0 and member_widget.interaction_combo:
                        interaction_data = member_widget.interaction_combo.itemData(
                            member_widget.interaction_combo.currentIndex())
                        if interaction_data:
                            update_data[f'operand_c_01_{i:02d}'] = interaction_data.get('x1', 0)
                            update_data[f'operand_c_02_{i:02d}'] = interaction_data.get('x2', 0)
                            update_data[f'operator_c_{i:02d}'] = interaction_data.get('op', 0)

            # Формируем SQL запрос
            if meas_type == 0:
                if update_criteria:
                    base_fields = """
                    meas_type = ?, water_crit = ?, w_sq_nmb = ?, w_operator = ?, empty_crit = ?, e_sq_nmb =?,
                    e_operator = ?, c_min = ?, c_max = ?,
                    k_i_klin00 = ?, k_i_klin01 = ?,
                    k_i_alin00 = ?,
                    k_i_alin01 = ?, operand_i_01_01 = ?, operand_i_02_01 = ?, operator_i_01 = ?,
                    k_i_alin02 = ?, operand_i_01_02 = ?, operand_i_02_02 = ?, operator_i_02 = ?,
                    k_i_alin03 = ?, operand_i_01_03 = ?, operand_i_02_03 = ?, operator_i_03 = ?,
                    k_i_alin04 = ?, operand_i_01_04 = ?, operand_i_02_04 = ?, operator_i_04 = ?,
                    k_i_alin05 = ?, operand_i_01_05 = ?, operand_i_02_05 = ?, operator_i_05 = ?
                    """
                    base_params = [
                        update_data['meas_type'],
                        update_data['water_crit'], update_data['w_sq_nmb'], update_data['w_operator'],
                        update_data['empty_crit'], update_data['e_sq_nmb'], update_data['e_operator'],
                        update_data['c_min'], update_data['c_max'],
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
                        update_data['operator_i_05']
                    ]
                else:
                    base_fields = """
                    k_i_klin00 = ?, k_i_klin01 = ?,
                    k_i_alin00 = ?,
                    k_i_alin01 = ?, operand_i_01_01 = ?, operand_i_02_01 = ?, operator_i_01 = ?,
                    k_i_alin02 = ?, operand_i_01_02 = ?, operand_i_02_02 = ?, operator_i_02 = ?,
                    k_i_alin03 = ?, operand_i_01_03 = ?, operand_i_02_03 = ?, operator_i_03 = ?,
                    k_i_alin04 = ?, operand_i_01_04 = ?, operand_i_02_04 = ?, operator_i_04 = ?,
                    k_i_alin05 = ?, operand_i_01_05 = ?, operand_i_02_05 = ?, operator_i_05 = ?
                    """
                    base_params = [
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
                        update_data['operator_i_05']
                    ]
            else:
                if update_criteria:
                    base_fields = """
                    meas_type = ?, water_crit = ?, w_sq_nmb = ?, w_operator = ?, empty_crit = ?, e_sq_nmb =?,
                    e_operator = ?, c_min = ?, c_max = ?,
                    k_c_klin00 = ?, k_c_klin01 = ?,
                    k_c_alin00 = ?,
                    k_c_alin01 = ?, operand_c_01_01 = ?, operand_c_02_01 = ?, operator_c_01 = ?,
                    k_c_alin02 = ?, operand_c_01_02 = ?, operand_c_02_02 = ?, operator_c_02 = ?,
                    k_c_alin03 = ?, operand_c_01_03 = ?, operand_c_02_03 = ?, operator_c_03 = ?,
                    k_c_alin04 = ?, operand_c_01_04 = ?, operand_c_02_04 = ?, operator_c_04 = ?,
                    k_c_alin05 = ?, operand_c_01_05 = ?, operand_c_02_05 = ?, operator_c_05 = ?
                    """
                    base_params = [
                        update_data['meas_type'],
                        update_data['water_crit'], update_data['w_sq_nmb'], update_data['w_operator'],
                        update_data['empty_crit'], update_data['e_sq_nmb'], update_data['e_operator'],
                        update_data['c_min'], update_data['c_max'],
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
                        update_data['operator_c_05']
                    ]
                else:
                    base_fields = """
                    k_c_klin00 = ?, k_c_klin01 = ?,
                    k_c_alin00 = ?,
                    k_c_alin01 = ?, operand_c_01_01 = ?, operand_c_02_01 = ?, operator_c_01 = ?,
                    k_c_alin02 = ?, operand_c_01_02 = ?, operand_c_02_02 = ?, operator_c_02 = ?,
                    k_c_alin03 = ?, operand_c_01_03 = ?, operand_c_02_03 = ?, operator_c_03 = ?,
                    k_c_alin04 = ?, operand_c_01_04 = ?, operand_c_02_04 = ?, operator_c_04 = ?,
                    k_c_alin05 = ?, operand_c_01_05 = ?, operand_c_02_05 = ?, operator_c_05 = ?
                    """
                    base_params = [
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
                        update_data['operator_c_05']
                    ]

            # Выполняем запрос
            if product_numbers is not False and model_numbers is not None:
                # Режим массового применения
                if not product_numbers or not model_numbers:
                    QMessageBox.warning(self, "Ошибка", "Списки продуктов и моделей не могут быть пустыми.")
                    return

                # Создаем плейсхолдеры для IN условий
                product_placeholders = ','.join(['?' for _ in product_numbers])
                model_placeholders = ','.join(['?' for _ in model_numbers])

                # Подготавливаем параметры
                params = base_params.copy()
                params.extend(product_numbers)
                params.extend(model_numbers)
                params.append(el_nmb)

                query = f"""
                UPDATE pr_set SET
                {base_fields}
                WHERE pr_nmb IN ({product_placeholders}) AND mdl_nmb IN ({model_placeholders}) AND el_nmb = ?
                """

                # Выполняем обновление
                self.db.execute(query, params)

                # Уведомление об успехе
                QMessageBox.information(self, "Успех", f"Коэффициенты и члены уравнения успешно применены "
                                                       f"для продуктов {', '.join(map(str, product_numbers))} "
                                                       f"и моделей {', '.join(map(str, model_numbers))}!")
            else:
                # Режим обычного сохранения
                pr_nmb = self.current_equation_data.get('pr_nmb', 0)
                mdl_nmb = self.current_equation_data.get('mdl_nmb', 0)

                # Добавляем параметры WHERE
                params = base_params + [pr_nmb, mdl_nmb, el_nmb]

                query = f"""
                UPDATE pr_set SET
                {base_fields}
                WHERE pr_nmb = ? AND mdl_nmb = ? AND el_nmb = ?
                """

                # Выполняем загрузку в базу
                self.db.execute(query, params)

                # Сохраняем границы интенсивности
                self.save_intensity_data()

                # ОБНОВЛЯЕМ ДАННЫЕ ПОСЛЕ СОХРАНЕНИЯ
                # Загружаем обновленные данные из базы
                self.refresh_current_equation_data(pr_nmb, mdl_nmb, el_nmb)

                # Обновляем таблицу
                self.load_equations()

                QMessageBox.information(self, "Успех", "Данные успешно сохранены!")


        except ValueError as e:
            QMessageBox.critical(self, "Ошибка ввода данных", str(e))
            return

        except Exception as e:
            QMessageBox.critical(self, "Ошибка сохранения", f"Ошибка сохранения/применения уравнения: {str(e)}")
            return

    def save_intensity_data(self):
        """Сохраняет данные границ интенсивности"""
        try:
            if not self.current_intensity_data:
                return

            pr_nmb = self.current_equation_data.get('pr_nmb', 0)

            for row in range(self.intensity_table.rowCount()):
                # Теперь номер линии берем из текущих данных, так как столбца с номером нет
                # Используем row индекс + 1 для получения номера линии
                sq_nmb = row + 1

                # Колонки теперь: 0 - название, 1 - I мин, 2 - I макс
                i_min_text = self.intensity_table.item(row, 1).text()  # I мин теперь в колонке 1
                i_max_text = self.intensity_table.item(row, 2).text()  # I макс теперь в колонке 2

                if not i_min_text or not i_max_text:
                    QMessageBox.warning(self, "Ошибка",
                                        f"Пожалуйста, заполните значения I мин и I макс для линии {sq_nmb}")
                    return

                i_min = self._safe_float_convert(i_min_text)
                i_max = self._safe_float_convert(i_max_text)

                if i_min < 0 or i_max < 0:
                    QMessageBox.warning(self, "Ошибка",
                                        f"Значения интенсивности должны быть положительными для линии {sq_nmb}")
                    return

                if i_min >= i_max:
                    QMessageBox.warning(self, "Ошибка", f"I мин должно быть меньше I макс для линии {sq_nmb}")
                    return

                # Получаем ln_nmb из исходных данных
                ln_nmb = -1
                for data in self.current_intensity_data:
                    if data.get('sq_nmb') == sq_nmb:
                        ln_nmb = data.get('ln_nmb', -1)
                        break

                # Проверяем существует ли запись
                check_query = "SELECT id FROM set07 WHERE pr_nmb = ? AND sq_nmb = ?"
                exists = self.db.fetch_one(check_query, [pr_nmb, sq_nmb])

                if exists:
                    # Обновляем существующую запись
                    update_query = """
                    UPDATE set07 SET i_min = ?, i_max = ? 
                    WHERE pr_nmb = ? AND sq_nmb = ?
                    """
                    self.db.execute(update_query, [i_min, i_max, pr_nmb, sq_nmb])
                else:
                    # Создаем новую запись
                    insert_query = """
                    INSERT INTO set07 (pr_nmb, sq_nmb, ln_nmb, i_min, i_max)
                    VALUES (?, ?, ?, ?, ?)
                    """
                    self.db.execute(insert_query, [pr_nmb, sq_nmb, ln_nmb, i_min, i_max])

        except ValueError as e:
            QMessageBox.critical(self, "Ошибка", f"Некорректные значения интенсивности: {str(e)}")
            raise
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения границ интенсивности: {str(e)}")
            raise

    def refresh_current_equation_data(self, pr_nmb, mdl_nmb, el_nmb):
        """Обновляет текущие данные уравнения из базы после сохранения"""
        try:
            query = """
            SELECT * FROM pr_set 
            WHERE pr_nmb = ? AND mdl_nmb = ? AND el_nmb = ?
            """
            params = [pr_nmb, mdl_nmb, el_nmb]
            result = self.db.fetch_one(query, params)

            if result:
                self.current_equation_data = result.copy()
        except Exception as e:
            print(f"Ошибка обновления данных уравнения: {str(e)}")

    def show_apply_to_dialog(self):
        """Показывает диалоговое окно 'Применить для...' и выполняет массовое обновление"""
        if self.current_editing_row is None or not self.current_equation_data:
            QMessageBox.warning(self, "Ошибка", "Нет активного уравнения для применения.")
            return

        dialog = ApplyToDialog(self)
        if dialog.exec() == QDialog.Accepted:
            try:
                product_numbers, model_numbers = dialog.get_data()
                self.save_equation_changes(product_numbers, model_numbers)
            except ValueError as e:
                QMessageBox.warning(self, "Ошибка ввода", f"Некорректный формат ввода:\n{str(e)}")

    def cancel_editing(self):
        """Отменяет редактирование"""
        try:
            self.regression_radio.toggled.disconnect(self.on_measurement_type_changed)
            self.correlation_radio.toggled.connect(self.on_measurement_type_changed)
        except:
            pass  # Игнорируем ошибки если обработчики не подключены

        self.edit_widget.setVisible(False)
        self.current_editing_row = None
        self.current_equation_data = None
        self.current_intensity_data = None

    def clear_equation(self):
        """Очищает введенное уравнение и сбрасывает коэффициенты корректировки"""
        try:
            # Сбрасываем коэффициенты корректировки
            self.k0_edit.setText("0")
            self.k1_edit.setText("1")

            # Очищаем члены уравнения
            for i in range(6):
                member_widget = self.equation_members[i]
                member_widget.coeff_edit.setText("0")

                # Очищаем взаимодействия (только для A1-A5)
                if i > 0 and member_widget.interaction_combo:
                    member_widget.interaction_combo.setCurrentIndex(0)

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

            # Для корреляции используем имена элементов вместо диапазонов
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
        # Для корреляции используем префикс C_ и имена элементов
        if meas_type == 0:
            prefix = "I_"
            get_name_func = self._get_range_name
        else:
            prefix = "C_"
            get_name_func = self._get_element_name

        # Проверка на допустимость оператора
        if operator == 7 and meas_type != 0:
            return "0"  # Оператор 7 недоступен для концентраций

        if operator == 0:  # 0 - пустая операция
            return "0"

        elif operator == 1:  # 1 - берем только operand_i_01_01
            # ИСПРАВЛЕНИЕ: разрешаем operand1 = 0 (для NC)
            if operand1 >= 0:  # было operand1 > 0
                name1 = get_name_func(operand1)
                # Проверяем, что имя не пустое
                if name1:
                    return f"{prefix}{name1}"
            return "0"

        elif operator == 2:  # 2 - operand_i_01_01 * operand_i_02_01
            # ИСПРАВЛЕНИЕ: разрешаем operand1 = 0 или operand2 = 0
            if operand1 >= 0 and operand2 >= 0:  # было operand1 > 0 and operand2 > 0
                name1 = get_name_func(operand1)
                name2 = get_name_func(operand2)
                # Проверяем, что оба имени не пустые
                if name1 and name2:
                    return f"{prefix}{name1}*{prefix}{name2}"
            return "0"

        elif operator == 3:  # 3 - operand_i_01_01 / operand_i_02_01
            # ИСПРАВЛЕНИЕ: разрешаем operand1 = 0 или operand2 = 0
            if operand1 >= 0 and operand2 >= 0:  # было operand1 > 0 and operand2 > 0
                name1 = get_name_func(operand1)
                name2 = get_name_func(operand2)
                # Проверяем, что оба имени не пустые
                if name1 and name2:
                    return f"{prefix}{name1}/{prefix}{name2}"
            return "0"

        elif operator == 4:  # 4 - operand_i_01_01 * operand_i_01_01
            # ИСПРАВЛЕНИЕ: разрешаем operand1 = 0
            if operand1 >= 0:  # было operand1 > 0
                name1 = get_name_func(operand1)
                if name1:
                    return f"{prefix}{name1}*{prefix}{name1}"
            return "0"

        elif operator == 5:  # 5 - 1 / operand_i_01_01
            # ИСПРАВЛЕНИЕ: разрешаем operand1 = 0
            if operand1 >= 0:  # было operand1 > 0
                name1 = get_name_func(operand1)
                if name1:
                    return f"1/{prefix}{name1}"
            return "0"

        elif operator == 6:  # 6 - operand_i_01_01 / operand_i_02_01 * operand_i_02_01
            # ИСПРАВЛЕНИЕ: разрешаем operand1 = 0 или operand2 = 0
            if operand1 >= 0 and operand2 >= 0:  # было operand1 > 0 and operand2 > 0
                name1 = get_name_func(operand1)
                name2 = get_name_func(operand2)
                if name1 and name2:
                    return f"{prefix}{name1}/{prefix}{name2}*{prefix}{name2}"
            return "0"

        elif operator == 7:  # 7 - 1 / operand_i_01_01 * operand_i_01_01
            # ИСПРАВЛЕНИЕ: разрешаем operand1 = 0
            if operand1 >= 0:  # было operand1 > 0
                name1 = get_name_func(operand1)
                if name1:
                    return f"1/{prefix}{name1}*{prefix}{name1}"
            return "0"

        return "0"

    def _get_element_name(self, el_nmb: int) -> str:
        """Получает имя элемента по его номеру"""
        # Используем adjusted_number из math_config
        if el_nmb < 0:
            return ""

        # Сначала ищем в math_config
        elements_config = self.math_config.get('elements', [])
        for element in elements_config:
            if isinstance(element, dict) and element.get('original_number') == el_nmb:
                return element.get('name', f"Element_{el_nmb}")

        # Если не нашли в math_config, ищем в elements_config
        for element in self.elements_config:
            if isinstance(element, dict) and element.get('number') == el_nmb:
                return element.get('name', f"Element_{el_nmb}")
        return f"Element_{el_nmb}"

    def _get_range_name(self, range_nmb: int) -> str:
        """Получает имя диапазона по его номеру"""
        # ИСПРАВЛЕНИЕ: разрешаем range_nmb = 0
        if range_nmb < 0:  # было range_nmb <= 0
            return ""

        # Сначала ищем в lines_math_config
        lines_config = self.lines_math_config.get('lines', [])
        for line in lines_config:
            if isinstance(line, dict) and line.get('adjusted_number') == range_nmb:
                return line.get('name', f"Range_{range_nmb}")

        # Если не нашли, ищем в range_config
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
        self.current_intensity_data = None

        # Перезагружаем конфигурационные файлы
        self.elements_config = self._load_elements_config()
        self.range_config = self._load_range_config()
        self.lines_math_config = self._load_lines_math_config()
        self.math_config = self._load_math_config()

        # Загружаем данные
        self.load_equations()


class ApplyToDialog(QDialog):
    """Диалоговое окно для ввода продуктов и моделей для массового применения"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Применить коэффициенты и члены уравнения для...")
        self.setModal(True)
        self.resize(300, 200)

        layout = QVBoxLayout(self)

        self.products_label = QLabel("Номера продуктов (через запятую, например: 1,2,3):")
        self.products_edit = QTextEdit()
        self.products_edit.setMaximumHeight(60)

        self.models_label = QLabel("Номера моделей (через запятую, например: 1,2):")
        self.models_edit = QTextEdit()
        self.models_edit.setMaximumHeight(60)

        # Кнопки OK/Cancel
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.products_label)
        layout.addWidget(self.products_edit)
        layout.addWidget(self.models_label)
        layout.addWidget(self.models_edit)
        layout.addWidget(self.button_box)

    def get_data(self):
        """Получает введенные данные и проверяет их"""
        try:
            products_text = self.products_edit.toPlainText().strip()
            models_text = self.models_edit.toPlainText().strip()

            if not products_text or not models_text:
                raise ValueError("Необходимо заполнить оба поля.")

            # Парсим номера продуктов
            product_numbers = []
            for part in products_text.split(','):
                num = int(part.strip())
                if num < 1:
                    raise ValueError("Номера продуктов должны быть положительными целыми числами.")
                product_numbers.append(num)

            # Парсим номера моделей
            model_numbers = []
            for part in models_text.split(','):
                num = int(part.strip())
                if num < 1:
                    raise ValueError("Номера моделей должны быть положительными целыми числами.")
                model_numbers.append(num)

            if not product_numbers or not model_numbers:
                raise ValueError("Необходимо ввести хотя бы один номер продукта и одну модель.")

            return product_numbers, model_numbers

        except ValueError as e:
            raise e

class ScientificDoubleValidator(QValidator):
    """Валидатор для чисел с плавающей точкой в научной нотации"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Регулярное выражение для чисел в научной нотации (разрешает E, e, Е, е)
        self.pattern = re.compile(r'^[-+]?(\d+([.,]\d*)?|[.,]\d+)([eEЕе][-+]?\d+)?$')

    def validate(self, text, pos):
        if not text:
            return QValidator.Intermediate, text, pos

        # Проверяем соответствие шаблону
        if self.pattern.match(text):
            return QValidator.Acceptable, text, pos
        else:
            return QValidator.Invalid, text, pos

    def fixup(self, text):
        # Заменяем запятые на точки и русские Е на английские E для корректного преобразования
        text = text.replace(',', '.')
        text = text.replace('Е', 'E').replace('е', 'e')
        return text
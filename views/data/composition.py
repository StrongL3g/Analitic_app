from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QCheckBox, QListWidget, QListWidgetItem, QComboBox, QSizePolicy, QDateTimeEdit,
    QTimeEdit, QMessageBox, QGridLayout, QFrame, QHeaderView, QStyle, QStyledItemDelegate, QStyleOptionHeader,
    QTableView, QScrollArea
)
from PySide6.QtCore import Qt, QEvent, QDateTime, QTime, QRect, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QGuiApplication, QFontMetrics
from database.db import Database



class TimeEdit15Min(QTimeEdit):
    #Кастомный QTimeEdit с шагом 15 минут

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("HH:mm")
        self.setTime(QTime(0, 0))

    def stepBy(self, steps):
        #Переопределяем изменение значения стрелочками
        current_time = self.time()
        minutes = current_time.minute()
        hours = current_time.hour()

        # Изменяем время с шагом 15 минут
        new_minutes = minutes + (steps * 15)
        if new_minutes >= 60:
            hours += 1
            new_minutes -= 60
        elif new_minutes < 0:
            hours -= 1
            new_minutes += 60

        # Корректируем часы если вышли за границы
        if hours >= 24:
            hours = 0
        elif hours < 0:
            hours = 23

        self.setTime(QTime(hours, new_minutes))


class CompositionPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}
        self.init_ui()

    def get_configured_elements(self):
        """Получаем список сконфигурированных элементов из БД"""
        try:
            query = """
            SELECT [el_nmb], [el_name] 
            FROM [AMMKASAKDB01].[dbo].[SET05] 
            WHERE el_name NOT IN ('-', 'None', '') 
            ORDER BY ak_nmb, el_nmb
            """

            # Используем fetch_all, который точно работает (как в load_data())
            rows = self.db.fetch_all(query)

            if not rows:
                print("Предупреждение: Нет данных в результате запроса")
                return []

            # Дополнительная диагностика
            print(f"Получено строк: {len(rows)}")
            print(f"Первая строка: {rows[0]} (тип: {type(rows[0])})")

            elements = []
            for row in rows:
                try:
                    # Обрабатываем как словарь
                    el_name = row['el_name'].strip() if 'el_name' in row else None
                    if el_name and el_name not in ('-', 'None', ''):
                        elements.append(el_name)
                except Exception as e:
                    print(f"Ошибка обработки строки {row}: {str(e)}")
                    continue

            print(f"Найдено элементов: {elements}")
            return elements

        except Exception as e:
            print(f"Ошибка в get_configured_elements: {str(e)}", exc_info=True)
            return []

    def round_to_15_min(self, time):
        """Округляет время до ближайших 15 минут"""
        minute = time.minute()
        rounded_minute = (minute // 15) * 15
        return QTime(time.hour(), rounded_minute)

    def validate_dates(self):
        """Проверяет корректность периода"""
        dt_from = QDateTime(
            self.date_from.date(),
            self.time_from.time()
        )
        dt_to = QDateTime(
            self.date_to.date(),
            self.time_to.time()
        )

        if dt_to < dt_from:
            self.date_to.setStyleSheet("background-color: #ffdddd;")
            QMessageBox.warning(self, "Ошибка", "Дата 'До' не может быть раньше 'От'!")
            return False

        self.date_to.setStyleSheet("")
        return True

    def on_checkbox_change(self, state):
        """Обработчик изменения состояния чекбокса"""
        sender = self.sender()
        if sender == self.check_man:
            status = "включен" if state == 2 else "выключен"
            print(f"Ручное измерение {status}")

    def init_upper_table(self):
        """Инициализация верхней таблицы с заголовками"""
        self.upper_table = QTableWidget()
        self.configured_elements = self.get_configured_elements()

        # Столбцы: ID, Пусто (Модель), Пусто (Время), + по одному на каждый элемент
        column_count = 3 + len(self.configured_elements)
        self.upper_table.setColumnCount(column_count)
        self.upper_table.setRowCount(0)

        # Устанавливаем заголовки
        headers = ["", "", ""] + self.configured_elements
        self.upper_table.setHorizontalHeaderLabels(headers)

        # Настраиваем внешний вид (остальное как было)
        self.upper_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.upper_table.verticalHeader().setVisible(False)
        self.upper_table.setShowGrid(False)
        self.upper_table.setFocusPolicy(Qt.NoFocus)
        self.upper_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.upper_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.upper_table.setSelectionMode(QTableWidget.NoSelection)
        self.upper_table.setFixedHeight(self.upper_table.horizontalHeader().height())

        return self.upper_table

    def init_lower_table(self):
        """Инициализация нижней таблицы с данными"""
        self.lower_table = QTableWidget()

        # Столбцы: ID, Модель, Время, + по 3 на каждый элемент
        column_count = 3 + len(self.configured_elements) * 3
        self.lower_table.setColumnCount(column_count)

        # Формируем заголовки
        headers = ["ID", "Модель", "Время цикла"]
        for element in self.configured_elements:
            headers.extend([f"С расч ({element})", f"С кор ({element})", f"С хим ({element})"])

        self.lower_table.setHorizontalHeaderLabels(headers)

        # Настраиваем внешний вид (как было)
        self.lower_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.lower_table.verticalHeader().setVisible(False)
        self.lower_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        header = self.lower_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Fixed)

        return self.lower_table

    def calculate_column_widths(self):
        """Рассчитывает ширину столбцов с учетом содержимого"""
        id_width = 50
        model_width = QFontMetrics(self.font()).horizontalAdvance("Модель") + 20
        time_width = QFontMetrics(self.font()).horizontalAdvance("Время цикла") + 20

        # Ширина столбцов для элементов
        element_width = max(
            QFontMetrics(self.font()).horizontalAdvance("С расч (XXX)"),
            QFontMetrics(self.font()).horizontalAdvance("С кор (XXX)"),
            QFontMetrics(self.font()).horizontalAdvance("С хим (XXX)")
        ) + 20

        return id_width, model_width, time_width, element_width

    def sync_column_widths(self):
        """Синхронизирует ширину столбцов между таблицами"""
        id_width, model_width, time_width, element_width = self.calculate_column_widths()

        # Устанавливаем ширину для нижней таблицы
        self.lower_table.setColumnWidth(0, id_width)  # ID
        self.lower_table.setColumnWidth(1, model_width)  # Модель
        self.lower_table.setColumnWidth(2, time_width)  # Время цикла

        # Ширина столбцов для элементов (по 3 столбца на каждый элемент)
        for i in range(3, 3 + len(self.configured_elements) * 3, 3):
            self.lower_table.setColumnWidth(i, element_width)  # С расч
            self.lower_table.setColumnWidth(i + 1, element_width)  # С кор
            self.lower_table.setColumnWidth(i + 2, element_width)  # С хим

        # Устанавливаем ширину верхней таблицы
        self.upper_table.setColumnWidth(0, id_width)  # ID
        self.upper_table.setColumnWidth(1, model_width)  # Пусто (Модель)
        self.upper_table.setColumnWidth(2, time_width)  # Пусто (Время)

        # Ширина заголовков элементов (сумма 3 столбцов)
        for i in range(3, 3 + len(self.configured_elements)):
            self.upper_table.setColumnWidth(i, element_width * 3)

        # Обновляем минимальную ширину виджета
        total_width = id_width + model_width + time_width + (len(self.configured_elements) * 3 * element_width)
        self.setMinimumWidth(total_width + 50)

    def create_tables_container(self):
        """Создает контейнер для таблиц с синхронизацией прокрутки"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Добавляем таблицы
        layout.addWidget(self.upper_table)
        layout.addWidget(self.lower_table)

        # Настраиваем прокрутку
        scroll_area = QScrollArea()
        scroll_area.setWidget(container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Синхронизируем горизонтальную прокрутку
        self.lower_table.horizontalScrollBar().valueChanged.connect(
            lambda value: self.upper_table.horizontalScrollBar().setValue(value)
        )

        return scroll_area

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Ввод химических содержаний")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Контейнер для чекбоксов и полей дат
        container = QHBoxLayout()
        container.setAlignment(Qt.AlignLeft)  # Выравнивание по левому краю
        container.setSpacing(10)  # Уменьшаем расстояние между элементами

        # Вертикальные чекбоксы
        checkboxes = QVBoxLayout()
        checkboxes.setSpacing(10)

        self.check_man = QCheckBox("Ручное измерение")
        self.check_man.stateChanged.connect(self.on_checkbox_change)
        self.check_chem = QCheckBox("Наличие химии")
        self.check_inten = QCheckBox("Интенсивности")

        checkboxes.addWidget(self.check_man)
        checkboxes.addWidget(self.check_chem)
        checkboxes.addWidget(self.check_inten)

        container.addLayout(checkboxes)

        # Поля дат и времени
        dates_layout = QVBoxLayout()
        dates_layout.setSpacing(10)

        # Строка "От"
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("От:"))
        self.date_from = QDateTimeEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDateTime(QDateTime.currentDateTime())
        self.date_from.setFixedWidth(100)
        from_layout.addWidget(self.date_from)

        self.time_from = TimeEdit15Min()
        self.time_from.setTime(self.round_to_15_min(QTime.currentTime()))
        from_layout.addWidget(self.time_from)
        dates_layout.addLayout(from_layout)

        # Строка "До"
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("До:"))
        self.date_to = QDateTimeEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.date_to.setFixedWidth(100)
        to_layout.addWidget(self.date_to)

        self.time_to = TimeEdit15Min()
        self.time_to.setTime(self.round_to_15_min(QTime.currentTime()))
        to_layout.addWidget(self.time_to)
        dates_layout.addLayout(to_layout)

        container.addLayout(dates_layout)
        main_layout.addLayout(container)

        # Комбобокс с продуктами
        self.product_combo = QComboBox()
        products = [f"Продукт {i}" for i in range(1, 9)]
        self.product_combo.addItems(products)
        self.product_combo.setFixedWidth(150)

        main_layout.addWidget(QLabel("Выберите продукт:"))
        main_layout.addWidget(self.product_combo)

        # Инициализация таблиц
        self.init_upper_table()
        self.init_lower_table()
        self.sync_column_widths()

        # Добавляем таблицы в контейнер с прокруткой
        tables_container = self.create_tables_container()
        main_layout.addWidget(tables_container, stretch=1)



        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)

        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_data)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

        # Подключение валидации
        self.date_from.dateTimeChanged.connect(self.validate_dates)
        self.time_from.timeChanged.connect(self.validate_dates)
        self.date_to.dateTimeChanged.connect(self.validate_dates)
        self.time_to.timeChanged.connect(self.validate_dates)

        self.setLayout(main_layout)

        self.load_data()



    def load_data(self):
        print("Заглушка")

    def save_data(self):
        print("Заглушка")
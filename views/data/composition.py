from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QPushButton, QLabel, QHBoxLayout, QCheckBox, QComboBox, QDateTimeEdit,
    QTimeEdit, QMessageBox, QHeaderView, QScrollArea, QTableWidgetItem, QProgressDialog)
from PySide6.QtCore import Qt, QDateTime, QTime
from PySide6.QtGui import QFontMetrics
from database.db import Database
import math


class TimeEdit15Min(QTimeEdit):
    # Кастомный QTimeEdit с шагом 15 минут
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("HH:mm")
        self.setTime(QTime(0, 0))

    def stepBy(self, steps):
        # Переопределяем изменение значения стрелочками
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
        self.intensity_columns = []  # Список столбцов интенсивностей
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

            rows = self.db.fetch_all(query)

            if not rows:
                print("Предупреждение: Нет данных в результате запроса")
                return []

            elements = []
            for row in rows:
                try:
                    el_name = row['el_name'].strip() if 'el_name' in row else None
                    if el_name and el_name not in ('-', 'None', ''):
                        elements.append(el_name)
                except Exception as e:
                    print(f"Ошибка обработки строки {row}: {str(e)}")
                    continue

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
        self.configured_elements = self.get_configured_elements()
        column_count = 3 + len(self.configured_elements)
        self.upper_table = QTableWidget()
        self.upper_table.setColumnCount(column_count)
        self.upper_table.setRowCount(0)

        headers = ["", "", ""] + self.configured_elements
        self.upper_table.setHorizontalHeaderLabels(headers)

        # Настройки таблицы
        self.upper_table.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.upper_table.verticalHeader().setVisible(False)
        self.upper_table.setShowGrid(False)
        self.upper_table.setFocusPolicy(Qt.NoFocus)
        self.upper_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.upper_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.upper_table.setSelectionMode(QTableWidget.NoSelection)
        self.upper_table.setFixedHeight(self.upper_table.horizontalHeader().height())

        # Устанавливаем минимальные ширины (будут пересчитаны позже)
        for i in range(column_count):
            self.upper_table.setColumnWidth(i, 100)

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

        # Настраиваем внешний вид
        self.lower_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.lower_table.verticalHeader().setVisible(False)
        self.lower_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Разрешаем редактирование только для столбцов "С хим"
        self.lower_table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)

        # Подключаем валидацию ввода
        self.lower_table.itemChanged.connect(self.validate_table_input)

        return self.lower_table

    def validate_table_input(self, item):
        """Проверяет ввод в ячейки таблицы"""
        header = self.lower_table.horizontalHeaderItem(item.column()).text()
        if "С хим" in header:
            try:
                float(item.text())
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Введите числовое значение")
                item.setText("0.0")  # Устанавливаем значение по умолчанию

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
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Функция для синхронизации прокрутки
        def sync_upper_scroll(value):
            # Рассчитываем позицию для верхней таблицы
            upper_pos = value // 3
            self.upper_table.horizontalScrollBar().setValue(upper_pos)

        # Подключаем синхронизацию
        self.lower_table.horizontalScrollBar().valueChanged.connect(sync_upper_scroll)

        # Обновляем ширину столбцов верхней таблицы при изменении размеров нижней
        def update_upper_columns():
            self.upper_table.setColumnWidth(0, self.lower_table.columnWidth(0))
            self.upper_table.setColumnWidth(1, self.lower_table.columnWidth(1))
            self.upper_table.setColumnWidth(2, self.lower_table.columnWidth(2))
            for i in range(3, self.upper_table.columnCount()):
                lower_col1 = 3 + (i - 3) * 3
                total_width = sum(self.lower_table.columnWidth(lower_col1 + k) for k in range(3))
                self.upper_table.setColumnWidth(i, total_width)

        self.lower_table.horizontalHeader().sectionResized.connect(update_upper_columns)
        update_upper_columns()

        return scroll_area

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setMinimumWidth(800)

        title = QLabel("Ввод химических содержаний")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        container = QHBoxLayout()
        container.setAlignment(Qt.AlignLeft)
        container.setSpacing(10)

        checkboxes = QVBoxLayout()
        checkboxes.setSpacing(10)

        self.check_man = QCheckBox("Ручное измерение")
        self.check_man.stateChanged.connect(self.on_checkbox_change)
        self.check_chem = QCheckBox("Наличие химии")
        self.check_inten = QCheckBox("Интенсивности")
        self.check_inten.setChecked(False)
        self.check_inten.stateChanged.connect(self.toggle_intensity_mode)

        checkboxes.addWidget(self.check_man)
        checkboxes.addWidget(self.check_chem)
        checkboxes.addWidget(self.check_inten)

        container.addLayout(checkboxes)

        dates_layout = QVBoxLayout()
        dates_layout.setSpacing(10)

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

        self.product_combo = QComboBox()
        products = [f"Продукт {i}" for i in range(1, 9)]
        self.product_combo.addItems(products)
        self.product_combo.setFixedWidth(150)

        main_layout.addWidget(QLabel("Выберите продукт:"))
        main_layout.addWidget(self.product_combo)

        self.init_upper_table()
        self.init_lower_table()
        self.sync_column_widths()

        self.tables_container = self.create_tables_container()
        self.layout().insertWidget(self.layout().count() - 1, self.tables_container, stretch=1)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_data)

        self.save_btn = QPushButton("Сохранить изменения")
        self.save_btn.clicked.connect(self.save_data)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)

        self.date_from.dateTimeChanged.connect(self.validate_dates)
        self.time_from.timeChanged.connect(self.validate_dates)
        self.date_to.dateTimeChanged.connect(self.validate_dates)
        self.time_to.timeChanged.connect(self.validate_dates)

        self.load_data()

    def clear_tables(self):
        # Удаляем контейнер таблиц
        if hasattr(self, 'tables_container') and self.tables_container is not None:
            self.layout().removeWidget(self.tables_container)
            self.tables_container.deleteLater()
            self.tables_container = None

        # Удаляем верхнюю таблицу
        if hasattr(self, 'upper_table') and self.upper_table is not None:
            self.upper_table.deleteLater()
            self.upper_table = None

        # Удаляем нижнюю таблицу
        if hasattr(self, 'lower_table') and self.lower_table is not None:
            self.lower_table.deleteLater()
            self.lower_table = None

        # Обновляем макет
        self.layout().invalidate()
        self.layout().activate()
        self.update()

    def init_intensity_table(self):
        self.lower_table = QTableWidget()
        self.lower_table.setColumnCount(3 + len(self.intensity_columns))
        headers = ["ID", "Модель", "Время цикла"] + self.intensity_columns
        self.lower_table.setHorizontalHeaderLabels(headers)
        self.lower_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.lower_table.verticalHeader().setVisible(False)
        self.lower_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.lower_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.lower_table.setSelectionMode(QTableWidget.NoSelection)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.lower_table)

        scroll_area = QScrollArea()
        scroll_area.setWidget(container)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.tables_container = scroll_area

        main_layout = self.layout()
        main_layout.insertWidget(main_layout.count() - 1, self.tables_container, stretch=1)

        self.lower_table.setColumnWidth(0, 80)
        self.lower_table.setColumnWidth(1, 120)
        self.lower_table.setColumnWidth(2, 150)
        for i in range(3, 3 + len(self.intensity_columns)):
            self.lower_table.setColumnWidth(i, 100)

    def toggle_intensity_mode(self):
        try:
            self.lower_table.setRowCount(0)  # очищаем строки

            if self.check_inten.isChecked():
                self.save_btn.hide()

                if not self.load_intensity_columns():
                    self.check_inten.setChecked(False)
                    return

                self.configure_lower_table_intensity()
                self.load_intensity_data()

            else:
                self.save_btn.show()

                self.configure_lower_table_normal()
                self.load_normal_data()

            # Обновляем верхнюю таблицу в зависимости от состояния чекбокса
            self.configure_upper_table()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось переключить режим: {str(e)}")
            self.check_inten.setChecked(False)

    def configure_lower_table_intensity(self):
        column_count = 3 + len(self.intensity_columns)
        self.lower_table.clear()
        self.lower_table.setColumnCount(column_count)

        headers = ["ID", "Модель", "Время цикла"] + self.intensity_columns
        self.lower_table.setHorizontalHeaderLabels(headers)

        self.lower_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.lower_table.setSelectionMode(QTableWidget.NoSelection)
        self.lower_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.lower_table.verticalHeader().setVisible(False)

        # Установите ширины столбцов, например:
        self.lower_table.setColumnWidth(0, 80)
        self.lower_table.setColumnWidth(1, 120)
        self.lower_table.setColumnWidth(2, 150)
        for i in range(3, column_count):
            self.lower_table.setColumnWidth(i, 100)

    def configure_upper_table(self):
        if self.check_inten.isChecked():
            # Устанавливаем заголовки с пустым текстом в режиме интенсивностей
            headers = ["", "", ""]  # Пустые заголовки для трех фиксированных столбцов
            elements = self.get_configured_elements()
            for element in elements:
                headers.extend(["", "", ""])  # Пустые заголовки для каждого элемента
            self.upper_table.setColumnCount(len(headers))
            self.upper_table.setHorizontalHeaderLabels(headers)

            # Очищаем таблицу
            self.upper_table.clearContents()
            self.upper_table.setRowCount(0)

        else:
            self.init_upper_table()

            # Синхронизируем ширину столбцов
            self.sync_column_widths()

    def configure_lower_table_normal(self):
        elements = self.get_configured_elements()

        column_count = 3 + len(elements) * 3
        self.lower_table.clear()
        self.lower_table.setColumnCount(column_count)

        headers = ["ID", "Модель", "Время цикла"]
        for element in elements:
            headers.extend([f"С расч ({element})", f"С кор ({element})", f"С хим ({element})"])
        self.lower_table.setHorizontalHeaderLabels(headers)

        self.lower_table.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)
        self.lower_table.setSelectionMode(QTableWidget.SingleSelection)
        self.lower_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.lower_table.verticalHeader().setVisible(False)

        self.sync_column_widths()

    def load_intensity_columns(self):
        try:
            query = "SELECT [ln_name] FROM [AMMKASAKDB01].[dbo].[LN_SET01] WHERE ln_nmb > 0 ORDER BY id"
            rows = self.db.fetch_all(query)

            if not rows:
                QMessageBox.warning(self, "Ошибка",
                                    "Не найдены столбцы интенсивностей в базе данных.\n"
                                    "Проверьте таблицу LN_SET01.")
                self.intensity_columns = []
                return False

            self.intensity_columns = [row['ln_name'] for row in rows if 'ln_name' in row]
            return True

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки столбцов интенсивностей: {str(e)}")
            self.intensity_columns = []
            return False

    def load_intensity_data(self):
        try:
            self.lower_table.setRowCount(0)
            self.original_data = {}

            manual_only = self.check_man.isChecked()
            has_chemistry = self.check_chem.isChecked()

            dt_from = QDateTime(self.date_from.date(), self.time_from.time()).toString("yyyy-MM-dd HH:mm:ss")
            dt_to = QDateTime(self.date_to.date(), self.time_to.time()).toString("yyyy-MM-dd HH:mm:ss")

            selected_product = self.product_combo.currentText()
            try:
                pr_nmb = int(selected_product.split()[-1])
            except:
                QMessageBox.warning(self, "Ошибка", "Неверный формат номера продукта")
                return

            num_columns = len(self.intensity_columns)
            if num_columns == 0:
                QMessageBox.warning(self, "Ошибка", "Не загружены названия столбцов интенсивностей")
                return

            intensity_columns = [f"[i_00_{i:02d}]" for i in range(num_columns)]
            select_columns = ", ".join(intensity_columns)

            query = f"""
            SELECT TOP (1000)
                [id], [mdl_nmb], [meas_dt], {select_columns}
            FROM [AMMKASAKDB01].[dbo].[PR_MEAS]
            WHERE [meas_dt] BETWEEN ? AND ?
            AND [pr_nmb] = ?
            """

            params = [dt_from, dt_to, pr_nmb]

            conditions = []
            if manual_only:
                conditions.append("[meas_type] = 0")
            if has_chemistry:
                conditions.append("1=1")

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += " ORDER BY [meas_dt]"

            rows = self.db.fetch_all(query, params)

            if not rows:
                QMessageBox.information(self, "Информация",
                                        "Данные интенсивностей не найдены. Проверьте параметры фильтрации.")
                return

            for row in rows:
                row_pos = self.lower_table.rowCount()
                self.lower_table.insertRow(row_pos)
                self.lower_table.setItem(row_pos, 0, QTableWidgetItem(str(row.get('id', ''))))
                self.lower_table.setItem(row_pos, 1, QTableWidgetItem(str(row.get('mdl_nmb', ''))))

                meas_dt = row.get('meas_dt')
                if isinstance(meas_dt, str):
                    dt_str = meas_dt
                elif hasattr(meas_dt, 'strftime'):
                    dt_str = meas_dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    dt_str = str(meas_dt) if meas_dt else ""

                self.lower_table.setItem(row_pos, 2, QTableWidgetItem(dt_str))

                for i in range(num_columns):
                    col_name = f"i_00_{i:02d}"
                    val = row.get(col_name)
                    item_text = f"{float(val):.4f}" if val is not None else ""
                    self.lower_table.setItem(row_pos, 3 + i, QTableWidgetItem(item_text))

            self.lower_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных интенсивностей: {str(e)}")
            self.lower_table.setRowCount(0)
            self.original_data = {}

    def load_data(self):
        if self.check_inten.isChecked():
            self.load_intensity_data()
        else:
            self.load_normal_data()

    def load_normal_data(self):
        try:
            self.lower_table.setRowCount(0)
            self.original_data = {}

            manual_only = self.check_man.isChecked()
            has_chemistry = self.check_chem.isChecked()

            dt_from = QDateTime(self.date_from.date(), self.time_from.time()).toString("yyyy-MM-dd HH:mm:ss")
            dt_to = QDateTime(self.date_to.date(), self.time_to.time()).toString("yyyy-MM-dd HH:mm:ss")

            selected_product = self.product_combo.currentText()
            try:
                pr_nmb = int(selected_product.split()[-1])
            except:
                QMessageBox.warning(self, "Ошибка", "Неверный формат номера продукта")
                return

            query = """
            SELECT TOP (1000)
                [id], [mdl_nmb], [meas_dt], [cuv_nmb], [meas_type], [pr_nmb],
                [c_01],[c_02],[c_03],[c_04],[c_05],[c_06],[c_07],[c_08],
                [c_cor_01],[c_cor_02],[c_cor_03],[c_cor_04],[c_cor_05],[c_cor_06],[c_cor_07],[c_cor_08],
                [c_chem_01],[c_chem_02],[c_chem_03],[c_chem_04],[c_chem_05],[c_chem_06],[c_chem_07],[c_chem_08]
            FROM [AMMKASAKDB01].[dbo].[PR_MEAS]
            WHERE [meas_dt] BETWEEN ? AND ?
            AND [pr_nmb] = ?
            """

            params = [dt_from, dt_to, pr_nmb]

            conditions = []
            if manual_only:
                conditions.append("[meas_type] = 0")
            if has_chemistry:
                chem_conditions = [f"[c_chem_{i:02d}] <> 0" for i in range(1, 9)]
                conditions.append(f"({' OR '.join(chem_conditions)})")

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += " ORDER BY [meas_dt]"

            rows = self.db.fetch_all(query, params)

            if not rows:
                QMessageBox.information(self, "Информация",
                                        "Данные не найдены. Проверьте параметры фильтрации.")
                return

            elements = self.get_configured_elements()

            for row in rows:
                row_pos = self.lower_table.rowCount()
                self.lower_table.insertRow(row_pos)

                self.lower_table.setItem(row_pos, 0, QTableWidgetItem(str(row.get('id', ''))))
                self.lower_table.setItem(row_pos, 1, QTableWidgetItem(str(row.get('mdl_nmb', ''))))

                meas_dt = row.get('meas_dt')
                if isinstance(meas_dt, str):
                    dt_str = meas_dt
                elif hasattr(meas_dt, 'strftime'):
                    dt_str = meas_dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    dt_str = str(meas_dt) if meas_dt else ""

                self.lower_table.setItem(row_pos, 2, QTableWidgetItem(dt_str))

                for i, element in enumerate(elements, 1):
                    if i > 8:
                        break

                    col_base = 3 + (i - 1) * 3
                    for prefix in ['c_', 'c_cor_', 'c_chem_']:
                        val = row.get(f"{prefix}{i:02d}")
                        item_text = f"{float(val):.4f}" if val is not None else ""
                        self.lower_table.setItem(row_pos, col_base, QTableWidgetItem(item_text))
                        col_base += 1

            for row in range(self.lower_table.rowCount()):
                for col in range(self.lower_table.columnCount()):
                    header = self.lower_table.horizontalHeaderItem(col)
                    if header and "С хим" in header.text():
                        item = self.lower_table.item(row, col)
                        if item:
                            try:
                                self.original_data[(row, col)] = float(item.text())
                            except ValueError:
                                self.original_data[(row, col)] = 0.0

            self.lower_table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных (обычный режим): {str(e)}")
            self.lower_table.setRowCount(0)
            self.original_data = {}

    def save_data(self):
        try:
            if not hasattr(self.db, 'execute'):
                QMessageBox.critical(self, "Ошибка", "Нет подключения к базе данных")
                return

            updates = []
            for row in range(self.lower_table.rowCount()):
                row_id_item = self.lower_table.item(row, 0)
                if not row_id_item:
                    continue

                row_id = row_id_item.text()
                if not row_id.isdigit():
                    continue

                for col in range(self.lower_table.columnCount()):
                    header = self.lower_table.horizontalHeaderItem(col)
                    if not header or "С хим" not in header.text():
                        continue

                    item = self.lower_table.item(row, col)
                    if not item:
                        continue

                    try:
                        element_name = header.text().split("(")[1].split(")")[0]
                        element_idx = self.configured_elements.index(element_name) + 1
                    except (IndexError, ValueError):
                        continue

                    try:
                        current_value = float(item.text())
                    except ValueError:
                        QMessageBox.warning(self, "Ошибка",
                                            f"Некорректное значение в строке {row + 1}, столбец {col + 1}")
                        return

                    original_value = self.original_data.get((row, col))
                    if original_value is None or not math.isclose(current_value, original_value, rel_tol=1e-5):
                        updates.append({
                            'id': int(row_id),
                            'element_num': element_idx,
                            'value': current_value,
                            'row': row,
                            'col': col
                        })

            if not updates:
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения")
                return

            progress = QProgressDialog("Сохранение изменений...", "Отмена", 0, len(updates), self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(0)

            failed_updates = []
            success_count = 0

            for i, update in enumerate(updates):
                progress.setValue(i)
                if progress.wasCanceled():
                    break

                query = f"""
                UPDATE [AMMKASAKDB01].[dbo].[PR_MEAS]
                SET [c_chem_{update['element_num']:02d}] = ?
                WHERE [id] = ?
                """
                params = [update['value'], update['id']]

                try:
                    self.db.execute(query, params)

                    if self.verify_update_in_db(update['id'], update):
                        self.original_data[(update['row'], update['col'])] = update['value']
                        success_count += 1
                    else:
                        failed_updates.append(update['id'])

                except Exception as e:
                    failed_updates.append(update['id'])
                    print(f"Ошибка при обновлении ID {update['id']}: {str(e)}")

            progress.setValue(len(updates))

            message = []
            if success_count > 0:
                message.append(f"Успешно обновлено: {success_count}")
            if failed_updates:
                message.append(
                    f"Проблемы с ID: {', '.join(map(str, failed_updates))} (но проверьте БД - возможно обновление прошло)")

            QMessageBox.information(self, "Результат сохранения", "\n".join(message))

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")

    def verify_update_in_db(self, record_id, update_data):
        try:
            query = f"""
            SELECT [c_chem_{update_data['element_num']:02d}]
            FROM [AMMKASAKDB01].[dbo].[PR_MEAS]
            WHERE [id] = ?
            """
            result = self.db.fetch_one(query, [record_id])

            if not result:
                return False

            if isinstance(result, dict):
                db_value = result[f'c_chem_{update_data["element_num"]:02d}']
            else:
                db_value = result[0] if isinstance(result, (list, tuple)) else result

            return math.isclose(float(db_value), update_data['value'], rel_tol=1e-5)

        except Exception as e:
            print(f"Ошибка при проверке обновления ID {record_id}: {str(e)}")
            return False

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QPushButton, QLabel, QHBoxLayout, QCheckBox, QComboBox, QDateTimeEdit,
    QTimeEdit, QMessageBox, QHeaderView, QScrollArea, QTableWidgetItem)
from PySide6.QtCore import Qt, QEvent, QDateTime, QTime
from PySide6.QtGui import QFontMetrics
from database.db import Database


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
        self.upper_table = QTableWidget()
        self.configured_elements = self.get_configured_elements()

        column_count = 3 + len(self.configured_elements)
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
        self.lower_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)  # Изменяем на Interactive
        self.lower_table.verticalHeader().setVisible(False)
        self.lower_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.lower_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Включаем полосу прокрутки

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
            # Каждый заголовок элемента в верхней таблице соответствует 3 столбцам в нижней
            upper_pos = value // 3
            self.upper_table.horizontalScrollBar().setValue(upper_pos)
            print("Синхронизируем")

        # Подключаем синхронизацию
        self.lower_table.horizontalScrollBar().valueChanged.connect(sync_upper_scroll)

        # Также обновляем ширину столбцов верхней таблицы при изменении размеров
        def update_upper_columns():
            # Первые три столбца (ID, Модель, Время)
            self.upper_table.setColumnWidth(0, self.lower_table.columnWidth(0))
            self.upper_table.setColumnWidth(1, self.lower_table.columnWidth(1))
            self.upper_table.setColumnWidth(2, self.lower_table.columnWidth(2))

            # Столбцы элементов (каждый соответствует 3 столбцам в нижней таблице)
            for i in range(3, self.upper_table.columnCount()):
                lower_col1 = 3 + (i - 3) * 3
                total_width = sum(self.lower_table.columnWidth(lower_col1 + k) for k in range(3))
                self.upper_table.setColumnWidth(i, total_width)

        # Обновляем при изменении размеров
        self.lower_table.horizontalHeader().sectionResized.connect(update_upper_columns)

        # Первоначальная настройка ширины
        update_upper_columns()

        return scroll_area

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Убираем фиксированную ширину
        self.setMinimumWidth(800)  # Минимальная ширина, но можно менять

        # Заголовок
        title = QLabel("Ввод химических содержаний")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Контейнер для чекбоксов и полей дат
        container = QHBoxLayout()
        container.setAlignment(Qt.AlignLeft)
        container.setSpacing(10)

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
        main_layout.addWidget(tables_container, stretch=1)  # Растягиваем на все доступное пространство

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

        self.load_data()

    def load_data(self):
        """Загрузка данных из базы данных с учетом фильтров"""
        try:
            print("Начало загрузки данных...")

            manual_only = self.check_man.isChecked()
            has_chemistry = self.check_chem.isChecked()
            print(f"Фильтры: Ручное={manual_only}, Химия={has_chemistry}")

            dt_from = QDateTime(
                self.date_from.date(),
                self.time_from.time()
            ).toString("yyyy-MM-dd HH:mm:ss")

            dt_to = QDateTime(
                self.date_to.date(),
                self.time_to.time()
            ).toString("yyyy-MM-dd HH:mm:ss")

            print(f"Диапазон дат: {dt_from} - {dt_to}")

            selected_product = self.product_combo.currentText()
            try:
                pr_nmb = int(selected_product.split()[-1])
                print(f"Выбран продукт: {pr_nmb}")
            except:
                QMessageBox.warning(self, "Ошибка", "Неверный формат номера продукта")
                return

            query = """
            SELECT 
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

            print("Выполняемый запрос:")
            print(query)
            print("Параметры:", params)

            if not self.db or not hasattr(self.db, 'fetch_all'):
                QMessageBox.critical(self, "Ошибка", "Нет подключения к базе данных")
                return

            rows = self.db.fetch_all(query, params)
            print(f"Найдено строк: {len(rows)}")

            if not rows:
                QMessageBox.information(self, "Информация",
                                        "Данные не найдены. Проверьте параметры фильтрации:\n"
                                        f"Дата: {dt_from} - {dt_to}\n"
                                        f"Продукт: {pr_nmb}\n"
                                        f"Фильтры: Ручное измерение={manual_only}, Наличие химии={has_chemistry}")
                return

            elements = self.get_configured_elements()
            print(f"Загружено элементов: {len(elements)}")

            self.lower_table.setRowCount(0)

            for row in rows:
                row_pos = self.lower_table.rowCount()
                self.lower_table.insertRow(row_pos)

                # Основные колонки
                self.lower_table.setItem(row_pos, 0, QTableWidgetItem(str(row.get('id', ''))))
                self.lower_table.setItem(row_pos, 1, QTableWidgetItem(str(row.get('mdl_nmb', ''))))

                # Исправленное форматирование даты
                meas_dt = row.get('meas_dt')
                if isinstance(meas_dt, str):
                    dt_str = meas_dt  # Если дата уже в строковом формате
                elif hasattr(meas_dt, 'strftime'):
                    dt_str = meas_dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    dt_str = str(meas_dt) if meas_dt else ""

                self.lower_table.setItem(row_pos, 2, QTableWidgetItem(dt_str))

                # Данные по элементам
                for i, element in enumerate(elements, 1):
                    if i > 8:
                        break

                    col_base = 3 + (i - 1) * 3
                    for prefix in ['c_', 'c_cor_', 'c_chem_']:
                        val = row.get(f"{prefix}{i:02d}")
                        item_text = f"{float(val):.4f}" if val is not None else ""
                        self.lower_table.setItem(row_pos, col_base, QTableWidgetItem(item_text))
                        col_base += 1

            self.lower_table.resizeColumnsToContents()
            print("Данные успешно загружены")

        except Exception as e:
            error_msg = f"Ошибка загрузки данных: {str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def save_data(self):
        """Сохранение измененных химических содержаний в БД"""
        try:
            # Проверяем соединение с БД
            if not self.db or not hasattr(self.db, 'execute'):
                QMessageBox.critical(self, "Ошибка", "Нет подключения к базе данных")
                return

            # Собираем все изменения
            updates = []
            for row in range(self.lower_table.rowCount()):
                id_item = self.lower_table.item(row, 0)
                if not id_item:
                    continue

                row_id = id_item.text()
                if not row_id.isdigit():
                    QMessageBox.warning(self, "Ошибка", f"Некорректный ID в строке {row + 1}")
                    return

                # Проходим по всем столбцам "С хим"
                for col in range(self.lower_table.columnCount()):
                    header_item = self.lower_table.horizontalHeaderItem(col)
                    if not header_item:
                        continue

                    header = header_item.text()
                    if "С хим" in header:
                        try:
                            # Получаем номер элемента из заголовка
                            element_name = header.split("(")[1].split(")")[0]
                            element_idx = self.configured_elements.index(element_name) + 1
                        except (IndexError, ValueError):
                            continue

                        item = self.lower_table.item(row, col)
                        if item is None:
                            continue

                        # Проверяем, что значение - число
                        try:
                            new_value = float(item.text())
                        except ValueError:
                            QMessageBox.warning(self, "Ошибка",
                                                f"Некорректное значение для элемента {element_name} в строке {row + 1}")
                            return

                        updates.append({
                            'id': int(row_id),  # Конвертируем в целое число
                            'element_num': element_idx,
                            'value': new_value
                        })

            if not updates:
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения")
                return

            # Выполняем все запросы UPDATE
            success = True
            for update in updates:
                query = f"""
                UPDATE [AMMKASAKDB01].[dbo].[PR_MEAS]
                SET [c_chem_{update['element_num']:02d}] = ?
                WHERE [id] = ?
                """
                params = [update['value'], update['id']]

                if not self.db.execute(query, params):
                    success = False
                    QMessageBox.critical(self, "Ошибка",
                                         f"Не удалось обновить запись ID {update['id']}")
                    break

            if success:
                # Обновляем данные в таблице
                self.load_data()
                QMessageBox.information(self, "Успех", "Изменения успешно сохранены")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении данных: {str(e)}")
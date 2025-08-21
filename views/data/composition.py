from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget,
    QPushButton, QLabel, QHBoxLayout, QCheckBox, QComboBox, QDateTimeEdit,
    QTimeEdit, QMessageBox, QHeaderView, QScrollArea, QTableWidgetItem, QProgressDialog)
from PySide6.QtCore import Qt, QDateTime, QTime
from PySide6.QtGui import QFontMetrics
from database.db import Database
import math
import json
from pathlib import Path


class TimeEdit15Min(QTimeEdit):
    """Кастомный QTimeEdit с шагом 15 минут"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("HH:mm")
        self.setTime(QTime(0, 0))

    def stepBy(self, steps):
        """Переопределяем изменение значения стрелочками с шагом 15 минут"""
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
    """Виджет для работы с химическим составом"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}
        self.intensity_columns = []
        self._config_dir = self._get_config_directory()
        self.init_ui()

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
                data = json.load(f)

            if not isinstance(data, list):
                print(f"Ошибка: {filename} должен содержать список")
                return []

            return data

        except json.JSONDecodeError as e:
            print(f"Ошибка формата JSON в файле {filename}: {str(e)}")
            return []
        except Exception as e:
            print(f"Ошибка загрузки файла {filename}: {str(e)}")
            return []

    def get_configured_elements(self) -> list:
        """Получает список сконфигурированных элементов из JSON-файла"""
        try:
            data = self._load_config_file("elements.json")
            if not data:
                return []

            # Извлекаем имена элементов, исключая невалидные значения
            elements = []
            for item in data:
                try:
                    if not isinstance(item, dict):
                        continue

                    element_name = item.get('name', '').strip()
                    if element_name and element_name not in ('-', 'None', ''):
                        elements.append(element_name)
                except Exception as e:
                    print(f"Ошибка обработки элемента {item}: {str(e)}")
                    continue

            # Сортировка по полю 'number'
            if all('number' in item for item in data):
                elements = sorted(elements,
                                  key=lambda x: next(item['number'] for item in data if item.get('name') == x))

            print(f"Успешно загружено {len(elements)} элементов")
            return elements

        except Exception as e:
            print(f"Ошибка в get_configured_elements: {str(e)}")
            return []

    def round_to_15_min(self, time: QTime) -> QTime:
        """Округляет время до ближайших 15 минут"""
        minute = time.minute()
        rounded_minute = (minute // 15) * 15
        return QTime(time.hour(), rounded_minute)

    def validate_dates(self) -> bool:
        """Проверяет корректность периода"""
        dt_from = QDateTime(self.date_from.date(), self.time_from.time())
        dt_to = QDateTime(self.date_to.date(), self.time_to.time())

        if dt_to < dt_from:
            self.date_to.setStyleSheet("background-color: #ffdddd;")
            QMessageBox.warning(self, "Ошибка", "Дата 'До' не может быть раньше 'От'!")
            return False

        self.date_to.setStyleSheet("")
        return True

    def init_table(self) -> QTableWidget:
        """Инициализация таблицы с данными"""
        table = QTableWidget()
        table.setEditTriggers(QTableWidget.AllEditTriggers)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.verticalHeader().setVisible(False)
        return table

    def configure_table_normal(self):
        """Настройка таблицы в обычном режиме"""
        elements = self.get_configured_elements()
        column_count = 3 + len(elements) * 3
        self.table.clear()
        self.table.setColumnCount(column_count)

        headers = ["ID", "Модель", "Время цикла"]
        for element in elements:
            headers.extend([f"С расч ({element})", f"С кор ({element})", f"С хим ({element})"])
        self.table.setHorizontalHeaderLabels(headers)

        # Разрешаем редактирование всех ячеек
        self.table.setEditTriggers(QTableWidget.AllEditTriggers)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        # Устанавливаем ширину столбцов
        id_width = 50
        model_width = QFontMetrics(self.font()).horizontalAdvance("Модель") + 20
        time_width = QFontMetrics(self.font()).horizontalAdvance("Время цикла") + 20
        element_width = max(
            QFontMetrics(self.font()).horizontalAdvance("С расч (XXX)"),
            QFontMetrics(self.font()).horizontalAdvance("С кор (XXX)"),
            QFontMetrics(self.font()).horizontalAdvance("С хим (XXX)")
        ) + 20

        self.table.setColumnWidth(0, id_width)
        self.table.setColumnWidth(1, model_width)
        self.table.setColumnWidth(2, time_width)

        for i in range(3, column_count):
            self.table.setColumnWidth(i, element_width)

    def configure_table_intensity(self):
        """Настройка таблицы в режиме интенсивностей"""
        column_count = 3 + len(self.intensity_columns)
        self.table.clear()
        self.table.setColumnCount(column_count)

        headers = ["ID", "Модель", "Время цикла"] + self.intensity_columns
        self.table.setHorizontalHeaderLabels(headers)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)

        # Устанавливаем ширину столбцов
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 150)
        for i in range(3, column_count):
            self.table.setColumnWidth(i, 100)

    def toggle_intensity_mode(self):
        """Переключает режим отображения таблицы"""
        try:
            self.table.setRowCount(0)

            if self.check_inten.isChecked():
                self.save_btn.hide()

                if not self.load_intensity_columns():
                    self.check_inten.setChecked(False)
                    return

                self.configure_table_intensity()
                self.load_intensity_data()

            else:
                self.save_btn.show()
                self.configure_table_normal()
                self.load_normal_data()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось переключить режим: {str(e)}")
            self.check_inten.setChecked(False)

    def load_intensity_columns(self) -> bool:
        """Загружает названия столбцов интенсивностей"""
        try:
            data = self._load_config_file("range.json")
            if not data:
                self.intensity_columns = []
                return False

            # Извлекаем имена, исключая пустые значения ("-")
            self.intensity_columns = []
            for item in data:
                if not isinstance(item, dict):
                    continue

                name = item.get('name', '').strip()
                if name and name != '-':
                    self.intensity_columns.append(name)

            if not self.intensity_columns:
                QMessageBox.warning(self, "Ошибка",
                                    "Не найдено ни одного валидного имени столбца в range.json")
                return False

            return True

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки столбцов интенсивностей: {str(e)}")
            self.intensity_columns = []
            return False

    def load_intensity_data(self):
        """Загружает данные интенсивностей"""
        try:
            self.table.setRowCount(0)
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
            FROM [dbo].[PR_MEAS]
            WHERE [meas_dt] BETWEEN ? AND ?
            AND [pr_nmb] = ? AND [active_model] = 1
            """

            params = [dt_from, dt_to, pr_nmb]

            conditions = []
            if manual_only:
                conditions.append("[meas_type] = 0")
            if has_chemistry:
                conditions.append("1=1")

            if conditions:
                query += " AND " + " AND ".join(conditions)

            query += " ORDER BY [timestamp]"

            rows = self.db.fetch_all(query, params)

            if not rows:
                QMessageBox.information(self, "Информация",
                                        "Данные интенсивностей не найдены. Проверьте параметры фильтрации.")
                return

            for row in rows:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)
                self.table.setItem(row_pos, 0, QTableWidgetItem(str(row.get('id', ''))))
                self.table.setItem(row_pos, 1, QTableWidgetItem(str(row.get('mdl_nmb', ''))))

                meas_dt = row.get('meas_dt')
                if isinstance(meas_dt, str):
                    dt_str = meas_dt
                elif hasattr(meas_dt, 'strftime'):
                    dt_str = meas_dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    dt_str = str(meas_dt) if meas_dt else ""

                self.table.setItem(row_pos, 2, QTableWidgetItem(dt_str))

                # Заполнение столбцов интенсивностей
                for i in range(num_columns):
                    col_name = f"i_00_{i:02d}"
                    val = row.get(col_name)
                    item_text = f"{float(val):.4f}" if val is not None else ""
                    self.table.setItem(row_pos, 3 + i, QTableWidgetItem(item_text))

            self.table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных интенсивностей: {str(e)}")
            self.table.setRowCount(0)
            self.original_data = {}

    def load_data(self):
        """Загрузка данных с автоматической проверкой конфигурации элементов"""
        if self.check_inten.isChecked():
            self.load_intensity_data()
        else:
            self.load_normal_data()

    def load_normal_data(self):
        """Загружает данные в обычном режиме"""
        try:
            self.table.setRowCount(0)
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
            FROM [dbo].[PR_MEAS]
            WHERE [meas_dt] BETWEEN ? AND ?
            AND [pr_nmb] = ? AND [active_model] = 1 
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

            query += " ORDER BY [timestamp]"

            rows = self.db.fetch_all(query, params)

            if not rows:
                QMessageBox.information(self, "Информация",
                                        "Данные не найдены. Проверьте параметры фильтрации.")
                return

            elements = self.get_configured_elements()

            for row in rows:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)

                # Добавляем данные в таблицу
                self.table.setItem(row_pos, 0, QTableWidgetItem(str(row.get('id', ''))))
                self.table.setItem(row_pos, 1, QTableWidgetItem(str(row.get('mdl_nmb', ''))))

                meas_dt = row.get('meas_dt')
                if isinstance(meas_dt, str):
                    dt_str = meas_dt
                elif hasattr(meas_dt, 'strftime'):
                    dt_str = meas_dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    dt_str = str(meas_dt) if meas_dt else ""

                self.table.setItem(row_pos, 2, QTableWidgetItem(dt_str))

                for i, element in enumerate(elements, 1):
                    if i > 8:
                        break

                    col_base = 3 + (i - 1) * 3
                    for prefix in ['c_', 'c_cor_', 'c_chem_']:
                        val = row.get(f"{prefix}{i:02d}")
                        item_text = f"{float(val):.4f}" if val is not None else ""
                        item = QTableWidgetItem(item_text)

                        # Устанавливаем флаги редактирования только для столбцов "С хим"
                        if prefix == 'c_chem_':
                            item.setFlags(item.flags() | Qt.ItemIsEditable)
                        else:
                            item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                        self.table.setItem(row_pos, col_base, item)
                        col_base += 1

            # Сохраняем исходные значения для сравнения при сохранении
            for row in range(self.table.rowCount()):
                for col in range(self.table.columnCount()):
                    header = self.table.horizontalHeaderItem(col)
                    if header and "С хим" in header.text():
                        item = self.table.item(row, col)
                        if item:
                            try:
                                self.original_data[(row, col)] = float(item.text())
                            except ValueError:
                                self.original_data[(row, col)] = 0.0

            self.table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных (обычный режим): {str(e)}")
            self.table.setRowCount(0)
            self.original_data = {}

    def save_data(self):
        """Сохраняет изменения в базу данных"""
        try:
            if not hasattr(self.db, 'execute'):
                QMessageBox.critical(self, "Ошибка", "Нет подключения к базе данных")
                return

            updates = []
            for row in range(self.table.rowCount()):
                row_id_item = self.table.item(row, 0)
                if not row_id_item:
                    continue

                row_id = row_id_item.text()
                if not row_id.isdigit():
                    continue

                for col in range(self.table.columnCount()):
                    header = self.table.horizontalHeaderItem(col)
                    if not header or "С хим" not in header.text():
                        continue

                    item = self.table.item(row, col)
                    if not item:
                        continue

                    try:
                        element_name = header.text().split("(")[1].split(")")[0]
                        element_idx = self.get_configured_elements().index(element_name) + 1
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
                UPDATE [dbo].[PR_MEAS]
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

    def verify_update_in_db(self, record_id: int, update_data: dict) -> bool:
        """Проверяет, что данные были успешно обновлены в БД"""
        try:
            query = f"""
            SELECT [c_chem_{update_data['element_num']:02d}]
            FROM [dbo].[PR_MEAS]
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

    def force_reload_data(self):
        """Принудительная перезагрузка данных"""
        try:
            if not self.check_inten.isChecked():
                self.configure_table_normal()
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при обновлении данных: {str(e)}")

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setMinimumWidth(800)

        title = QLabel("Ввод химических содержаний")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Верхняя панель с настройками
        container = QHBoxLayout()
        container.setAlignment(Qt.AlignLeft)
        container.setSpacing(10)

        # Чекбоксы
        checkboxes = QVBoxLayout()
        checkboxes.setSpacing(10)

        self.check_man = QCheckBox("Ручное измерение")
        self.check_man.stateChanged.connect(self.load_data)
        self.check_chem = QCheckBox("Наличие химии")
        self.check_chem.stateChanged.connect(self.load_data)
        self.check_inten = QCheckBox("Интенсивности")
        self.check_inten.setChecked(False)
        self.check_inten.stateChanged.connect(self.toggle_intensity_mode)

        checkboxes.addWidget(self.check_man)
        checkboxes.addWidget(self.check_chem)
        checkboxes.addWidget(self.check_inten)

        container.addLayout(checkboxes)

        # Даты и время
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

        # Выбор продукта
        self.product_combo = QComboBox()
        products = [f"Продукт {i}" for i in range(1, 9)]
        self.product_combo.addItems(products)
        self.product_combo.setFixedWidth(150)
        self.product_combo.currentIndexChanged.connect(self.force_reload_data)

        main_layout.addWidget(QLabel("Выберите продукт:"))
        main_layout.addWidget(self.product_combo)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignLeft)
        btn_layout.setSpacing(10)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.force_reload_data)

        self.save_btn = QPushButton("Сохранить изменения")
        self.save_btn.clicked.connect(self.save_data)

        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)

        # Таблица
        self.table = self.init_table()
        self.configure_table_normal()

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        main_layout.addWidget(scroll_area)

        # Связывание валидации дат
        self.date_from.dateTimeChanged.connect(self.validate_dates)
        self.time_from.timeChanged.connect(self.validate_dates)
        self.date_to.dateTimeChanged.connect(self.validate_dates)
        self.time_to.timeChanged.connect(self.validate_dates)
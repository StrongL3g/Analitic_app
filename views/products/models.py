from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTableWidget, QTableWidgetItem, QHeaderView,
                               QSizePolicy, QPushButton, QComboBox, QMessageBox)
from PySide6.QtCore import Qt
from pathlib import Path


class ModelsPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.original_data = {}
        self.intensity_columns = []
        self._config_dir = self._get_config_directory()
        self.show_success_message = False  # Флаг для показа сообщения об успехе
        self.init_ui()
        self.load_data_from_db(show_message=False)  # Первая загрузка без сообщения

    def _get_config_directory(self) -> Path:
        """Получает путь к директории конфигурации"""
        base_dir = Path(__file__).parent
        config_dir = base_dir.parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        return config_dir

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        self.setLayout(main_layout)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(400)

        # Кнопки управления
        buttons_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Обновить")
        self.save_btn = QPushButton("Сохранить")

        buttons_layout.addWidget(self.refresh_btn)
        buttons_layout.addWidget(self.save_btn)
        buttons_layout.addStretch()

        main_layout.addLayout(buttons_layout)

        # Создаем контейнер для двух таблиц
        tables_container = QWidget()
        tables_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        tables_layout = QHBoxLayout(tables_container)
        tables_layout.setContentsMargins(0, 0, 0, 0)
        tables_layout.setSpacing(20)
        main_layout.addWidget(tables_container)

        # Таблица для кюветы 1
        cuv1_widget = QWidget()
        cuv1_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cuv1_layout = QVBoxLayout(cuv1_widget)
        cuv1_layout.setContentsMargins(0, 0, 0, 0)
        cuv1_layout.setSpacing(5)
        cuv1_layout.setAlignment(Qt.AlignTop)

        cuv1_title = QLabel("Выбор активной модели кювета 1")
        cuv1_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        cuv1_title.setAlignment(Qt.AlignCenter)
        cuv1_layout.addWidget(cuv1_title)

        self.table_cuv1 = QTableWidget()
        self.table_cuv1.setColumnCount(4)
        self.table_cuv1.setHorizontalHeaderLabels(["Прибор №", "Продукт №", "Модель №", "Описание"])
        self.table_cuv1.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_cuv1.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_cuv1.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_cuv1.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_cuv1.verticalHeader().setVisible(False)
        self.table_cuv1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cuv1_layout.addWidget(self.table_cuv1)
        tables_layout.addWidget(cuv1_widget)

        # Таблица для кюветы 2
        cuv2_widget = QWidget()
        cuv2_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cuv2_layout = QVBoxLayout(cuv2_widget)
        cuv2_layout.setContentsMargins(0, 0, 0, 0)
        cuv2_layout.setSpacing(5)
        cuv2_layout.setAlignment(Qt.AlignTop)

        cuv2_title = QLabel("Выбор активной модели кювета 2")
        cuv2_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        cuv2_title.setAlignment(Qt.AlignCenter)
        cuv2_layout.addWidget(cuv2_title)

        self.table_cuv2 = QTableWidget()
        self.table_cuv2.setColumnCount(4)
        self.table_cuv2.setHorizontalHeaderLabels(["Прибор №", "Продукт №", "Модель №", "Описание"])
        self.table_cuv2.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table_cuv2.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_cuv2.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_cuv2.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_cuv2.verticalHeader().setVisible(False)
        self.table_cuv2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cuv2_layout.addWidget(self.table_cuv2)
        tables_layout.addWidget(cuv2_widget)

        # Устанавливаем равное соотношение для двух таблиц
        tables_layout.setStretchFactor(cuv1_widget, 1)
        tables_layout.setStretchFactor(cuv2_widget, 1)

        # Добавляем растягивающийся элемент внизу, чтобы все осталось вверху
        main_layout.addStretch()

        # Подключаем кнопки
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.save_btn.clicked.connect(self.save_data)

    def showEvent(self, event):
        """Обработчик события показа страницы - загружаем данные"""
        super().showEvent(event)
        self.load_data_from_db(show_message=False)  # При открытии страницы - без сообщения

    def refresh_data(self):
        """Обновление данных по кнопке"""
        self.load_data_from_db(show_message=True)  # По кнопке - с сообщением

    def load_data_from_db(self, show_message=False):
        """Загрузка данных из базы данных"""
        try:
            # Загрузка данных для кюветы 1
            self.load_cuv_data(1, self.table_cuv1)

            # Загрузка данных для кюветы 2
            self.load_cuv_data(2, self.table_cuv2)

            if show_message or self.show_success_message:
                QMessageBox.information(self, "Успех", "Данные успешно обновлены!")
                self.show_success_message = False  # Сбрасываем флаг после показа

        except Exception as e:
            print(f"Ошибка при загрузке данных из БД: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке данных: {e}")

    def load_cuv_data(self, cuv_number, table_widget):
        """Загрузка данных для конкретной кюветы"""
        try:
            query = """
                SELECT 
                    c.ac_nmb, 
                    c.pr_nmb, 
                    p.mdl_nmb, 
                    p.mdl_desc, 
                    c.cuv_nmb
                FROM cfg01 c
                JOIN pr_set p ON c.pr_nmb = p.pr_nmb 
                WHERE c.cuv_nmb = ? 
                    AND p.active_model = 1
                    AND p.el_nmb = 1
                ORDER BY c.pr_nmb
                LIMIT 4
            """

            params = (cuv_number,)
            rows = self.db.fetch_all(query, params)
            print(f"Запрос для кюветы {cuv_number}: найдено {len(rows)} строк")

            # Сохраняем оригинальные данные для сравнения при сохранении
            self.original_data[cuv_number] = []

            # Всегда устанавливаем 4 строки
            table_widget.setRowCount(4)

            for i in range(4):
                if i < len(rows):
                    row = rows[i]

                    # Сохраняем оригинальные данные
                    original_row = {
                        'ac_nmb': row['ac_nmb'],
                        'pr_nmb': row['pr_nmb'],
                        'mdl_nmb': row['mdl_nmb'],
                        'mdl_desc': row['mdl_desc'],
                        'cuv_nmb': row['cuv_nmb']
                    }
                    self.original_data[cuv_number].append(original_row)

                    # Прибор № и Продукт № - только для чтения
                    item_ac = QTableWidgetItem(str(row['ac_nmb']))
                    item_ac.setFlags(item_ac.flags() & ~Qt.ItemIsEditable)
                    table_widget.setItem(i, 0, item_ac)

                    item_pr = QTableWidgetItem(str(row['pr_nmb']))
                    item_pr.setFlags(item_pr.flags() & ~Qt.ItemIsEditable)
                    table_widget.setItem(i, 1, item_pr)

                    # Модель № - комбобокс с выбором
                    combo_mdl = QComboBox()
                    combo_mdl.addItems(["1", "2", "3"])  # Доступные модели
                    combo_mdl.setCurrentText(str(row['mdl_nmb']))
                    table_widget.setCellWidget(i, 2, combo_mdl)

                    # Описание - редактируемое поле
                    description = str(row['mdl_desc']) if row['mdl_desc'] else ""
                    item_desc = QTableWidgetItem(description)
                    table_widget.setItem(i, 3, item_desc)

                else:
                    # Заполняем пустые строки прочерками
                    item_ac = QTableWidgetItem("-")
                    item_ac.setFlags(item_ac.flags() & ~Qt.ItemIsEditable)
                    table_widget.setItem(i, 0, item_ac)

                    item_pr = QTableWidgetItem("-")
                    item_pr.setFlags(item_pr.flags() & ~Qt.ItemIsEditable)
                    table_widget.setItem(i, 1, item_pr)

                    combo_mdl = QComboBox()
                    combo_mdl.addItems(["1", "2", "3"])
                    combo_mdl.setCurrentText("-")
                    combo_mdl.setEnabled(False)
                    table_widget.setCellWidget(i, 2, combo_mdl)

                    item_desc = QTableWidgetItem("")
                    item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsEditable)
                    table_widget.setItem(i, 3, item_desc)

                    self.original_data[cuv_number].append(None)

            # Устанавливаем высоту строк
            row_height = 40
            for i in range(4):
                table_widget.setRowHeight(i, row_height)

            # Устанавливаем фиксированную высоту таблицы
            header_height = table_widget.horizontalHeader().height()
            total_height = header_height + (4 * row_height) + 2
            table_widget.setFixedHeight(total_height)

        except Exception as e:
            print(f"Ошибка при загрузке данных для кюветы {cuv_number}: {e}")
            # Все равно создаем 4 пустые строки
            table_widget.setRowCount(4)
            for i in range(4):
                item_ac = QTableWidgetItem("-")
                item_ac.setFlags(item_ac.flags() & ~Qt.ItemIsEditable)
                table_widget.setItem(i, 0, item_ac)

                item_pr = QTableWidgetItem("-")
                item_pr.setFlags(item_pr.flags() & ~Qt.ItemIsEditable)
                table_widget.setItem(i, 1, item_pr)

                combo_mdl = QComboBox()
                combo_mdl.addItems(["1", "2", "3"])
                combo_mdl.setCurrentText("-")
                combo_mdl.setEnabled(False)
                table_widget.setCellWidget(i, 2, combo_mdl)

                item_desc = QTableWidgetItem("")
                item_desc.setFlags(item_desc.flags() & ~Qt.ItemIsEditable)
                table_widget.setItem(i, 3, item_desc)

            # Устанавливаем фиксированную высоту даже при ошибке
            row_height = 40
            header_height = table_widget.horizontalHeader().height()
            total_height = header_height + (4 * row_height) + 2
            table_widget.setFixedHeight(total_height)

    def save_data(self):
        """Сохранение изменений в базе данных"""
        try:
            changes_made = False

            # Обрабатываем изменения для каждой кюветы
            for cuv_number, table_widget in [(1, self.table_cuv1), (2, self.table_cuv2)]:
                if cuv_number not in self.original_data:
                    continue

                for i in range(4):
                    original_row = self.original_data[cuv_number][i]
                    if not original_row:
                        continue

                    # Получаем текущие значения из таблицы
                    combo_mdl = table_widget.cellWidget(i, 2)
                    current_mdl_nmb = int(combo_mdl.currentText()) if combo_mdl and combo_mdl.isEnabled() else \
                    original_row['mdl_nmb']

                    item_desc = table_widget.item(i, 3)
                    current_mdl_desc = item_desc.text() if item_desc else original_row['mdl_desc']

                    pr_nmb = original_row['pr_nmb']
                    original_mdl_nmb = original_row['mdl_nmb']
                    original_mdl_desc = original_row['mdl_desc']

                    # Проверяем, изменилась ли модель
                    if current_mdl_nmb != original_mdl_nmb:
                        changes_made = True

                        # 1. Устанавливаем active_model = 0 для всех моделей этого продукта
                        query_deactivate = """
                            UPDATE pr_set 
                            SET active_model = 0 
                            WHERE pr_nmb = ?
                        """
                        self.db.execute(query_deactivate, (pr_nmb,))

                        # 2. Устанавливаем active_model = 1 для выбранной модели
                        query_activate = """
                            UPDATE pr_set 
                            SET active_model = 1 
                            WHERE pr_nmb = ? AND mdl_nmb = ?
                        """
                        self.db.execute(query_activate, (pr_nmb, current_mdl_nmb))

                        print(
                            f"Изменена активная модель для продукта {pr_nmb}: {original_mdl_nmb} -> {current_mdl_nmb}")

                    # Проверяем, изменилось ли описание
                    if current_mdl_desc != original_mdl_desc:
                        changes_made = True

                        # Обновляем описание для всех строк этой модели
                        query_desc = """
                            UPDATE pr_set 
                            SET mdl_desc = ? 
                            WHERE pr_nmb = ? AND mdl_nmb = ?
                        """
                        self.db.execute(query_desc, (current_mdl_desc, pr_nmb, current_mdl_nmb))

                        print(
                            f"Изменено описание для продукта {pr_nmb}, модель {current_mdl_nmb}: '{original_mdl_desc}' -> '{current_mdl_desc}'")

            if changes_made:
                #QMessageBox.information(self, "Успех", "Изменения успешно сохранены в базе данных!")
                # Устанавливаем флаг для показа сообщения при следующей загрузке
                self.show_success_message = True
                # Обновляем данные после сохранения
                self.load_data_from_db(show_message=False)
            else:
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения.")

        except Exception as e:
            print(f"Ошибка при сохранении данных: {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении данных: {e}")

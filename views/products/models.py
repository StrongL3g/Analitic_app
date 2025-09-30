from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy)
from PySide6.QtCore import Qt
from pathlib import Path


class ModelsPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.original_data = {}
        self.intensity_columns = []
        self._config_dir = self._get_config_directory()
        self.init_ui()
        self.load_data_from_db()

    def _get_config_directory(self) -> Path:
        """Получает путь к директории конфигурации"""
        base_dir = Path(__file__).parent
        config_dir = base_dir.parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        return config_dir

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setMinimumWidth(800)

        # Создаем контейнер для двух таблиц
        tables_layout = QHBoxLayout()
        main_layout.addLayout(tables_layout)

        # Таблица для кюветы 1
        cuv1_layout = QVBoxLayout()
        cuv1_title = QLabel("Выбор активной модели кювета 1")
        cuv1_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        cuv1_layout.addWidget(cuv1_title)


        self.table_cuv1 = QTableWidget()
        self.table_cuv1.setColumnCount(4)
        self.table_cuv1.setHorizontalHeaderLabels(["Прибор №", "Продукт №", "Модель №", "Описание"])
        self.table_cuv1.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_cuv1.verticalHeader().setVisible(False)
        cuv1_layout.addWidget(self.table_cuv1)
        tables_layout.addLayout(cuv1_layout)

        # Таблица для кюветы 2
        cuv2_layout = QVBoxLayout()
        cuv2_title = QLabel("Выбор активной модели кювета 2")
        cuv2_title.setStyleSheet("font-size: 14px; font-weight: bold;")
        cuv2_layout.addWidget(cuv2_title)

        self.table_cuv2 = QTableWidget()
        self.table_cuv2.setColumnCount(4)
        self.table_cuv2.setHorizontalHeaderLabels(["Прибор №", "Продукт №", "Модель №", "Описание"])
        self.table_cuv2.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table_cuv2.verticalHeader().setVisible(False)
        cuv2_layout.addWidget(self.table_cuv2)

        tables_layout.addLayout(cuv2_layout)

        # Для заголовков таблиц
        cuv1_title.setAlignment(Qt.AlignTop)
        cuv2_title.setAlignment(Qt.AlignTop)

        # Для таблиц
        self.table_cuv1.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.table_cuv2.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        # Для layout таблиц
        cuv1_layout.setAlignment(Qt.AlignTop)
        cuv2_layout.setAlignment(Qt.AlignTop)

    def load_data_from_db(self):
        """Загрузка данных из базы данных"""
        try:
            # Загрузка данных для кюветы 1
            self.load_cuv_data(1, self.table_cuv1)

            # Загрузка данных для кюветы 2
            self.load_cuv_data(2, self.table_cuv2)

        except Exception as e:
            print(f"Ошибка при загрузке данных из БД: {e}")

    def load_cuv_data(self, cuv_number, table_widget):
        """Загрузка данных для конкретной кюветы"""
        try:
            query = """
                SELECT m.ac_nmb, m.pr_nmb, p.mdl_nmb, p.mdl_desc, m.cuv_nmb
                FROM cfg01 m
                JOIN pr_set p ON m.pr_nmb = p.pr_nmb
                WHERE m.ac_nmb = 1 AND p.active_model = 1 AND m.cuv_nmb = ? LIMIT 1
            """

            params = (cuv_number,)
            rows = self.db.fetch_all(query, params)
            print(f"Запрос для кюветы {cuv_number}: найдено {len(rows)} строк")

            if rows and len(rows) > 0:
                table_widget.setRowCount(len(rows))

                # Высота одной строки
                row_height = 30
                # Высота заголовка таблицы
                header_height = table_widget.horizontalHeader().height()
                # Общая высота таблицы
                total_height = header_height + (len(rows) * row_height)

                # Устанавливаем фиксированную высоту таблицы
                table_widget.setFixedHeight(total_height)

                for i, row in enumerate(rows):
                    table_widget.setItem(i, 0, QTableWidgetItem(str(row['ac_nmb'])))  # Прибор №
                    table_widget.setItem(i, 1, QTableWidgetItem(str(row['pr_nmb'])))  # Продукт №
                    table_widget.setItem(i, 2, QTableWidgetItem(str(row['mdl_nmb'])))  # Модель №

                    description = str(row['mdl_desc']) if row['mdl_desc'] else ""
                    table_widget.setItem(i, 3, QTableWidgetItem(description))

            else:
                # Если данных нет, показываем пустую таблицу
                print(f"Данные для кюветы {cuv_number} не найдены")
                table_widget.setRowCount(0)

        except Exception as e:
            print(f"Ошибка при загрузке данных для кюветы {cuv_number}: {e}")
            table_widget.setRowCount(0)

    def save_data(self):
        """Сохранение данных (если потребуется редактирование в будущем)"""
        pass
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QComboBox, QFrame,
                               QHBoxLayout, QSplitter, QTableWidget, QTableWidgetItem,
                               QHeaderView, QMessageBox, QPushButton)
from PySide6.QtGui import QDoubleValidator
from PySide6.QtCore import Qt
import json
from database.db import Database
from pathlib import Path
from config import PR_COUNT, DB_CONFIG


class StandardsPage(QWidget):
    """Виджет для отображения и редактирования нормативов"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}
        self._config_dir = self._get_config_directory()
        self.elements_config = self._load_elements_config()
        self.products_config = self._load_products_config()
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

    def _load_products_config(self) -> list:
        """Загружает конфигурацию продуктов из базы данных"""
        try:
            query = "SELECT pr_nmb, pr_name, pr_desc FROM cfg02 ORDER BY pr_nmb"
            results = self.db.fetch_all(query)
            return results if results else []
        except Exception as e:
            print(f"Ошибка загрузки конфигурации продуктов: {e}")
            return []

    def _get_element_name(self, el_nmb: int) -> str:
        """Получает имя элемента по его номеру"""
        for element in self.elements_config:
            if isinstance(element, dict) and element.get('number') == el_nmb:
                return element.get('name', f"Element_{el_nmb}")
        return f"Element_{el_nmb}"

    def _get_product_desc(self, pr_nmb: int) -> str:
        """Получает описание продукта по его номеру"""
        for product in self.products_config:
            if product.get('pr_nmb') == pr_nmb:
                return product.get('pr_desc', f"Продукт {pr_nmb}")
        return f"Продукт {pr_nmb}"

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setMinimumWidth(900)
        self.setMinimumHeight(700)

        title = QLabel("Нормативы")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Верхняя панель с комбобоксом выбора продукта и кнопками
        top_frame = QFrame()
        top_frame.setFrameStyle(QFrame.StyledPanel)
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)
        top_layout.setContentsMargins(10, 5, 10, 5)
        top_frame.setLayout(top_layout)

        # Левая часть: выбор продукта и кнопки
        left_layout = QVBoxLayout()
        left_layout.setSpacing(10)

        # Выбор продукта
        product_layout = QVBoxLayout()
        product_layout.setSpacing(2)
        product_label = QLabel("Продукт:")
        product_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        product_label.setFixedHeight(20)

        self.product_combo = QComboBox()
        products = [f"Продукт {i}" for i in range(1, PR_COUNT + 1)]
        self.product_combo.addItems(products)
        self.product_combo.setFixedSize(150, 30)

        product_layout.addWidget(product_label)
        product_layout.addWidget(self.product_combo)
        left_layout.addLayout(product_layout)

        # Кнопки управления (без подписи "Действия")
        buttons_row_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setFixedSize(100, 30)
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.setFixedSize(100, 30)

        buttons_row_layout.addWidget(self.save_btn)
        buttons_row_layout.addWidget(self.refresh_btn)
        buttons_row_layout.addStretch()

        left_layout.addLayout(buttons_row_layout)
        top_layout.addLayout(left_layout)

        top_layout.addStretch()
        top_frame.setFixedHeight(100)  # Увеличили высоту для кнопок

        # Область с описанием продукта (с рамкой как у верхней панели)
        self.product_info_frame = QFrame()
        # Добавляем рамку как у верхней панели
        self.product_info_frame.setFrameStyle(QFrame.StyledPanel)
        self.product_info_frame.setStyleSheet("background-color: #f0f0f0; padding: 10px;")
        product_info_layout = QVBoxLayout()
        product_info_layout.setContentsMargins(5, 5, 5, 5)  # Уменьшили отступы

        self.product_desc_label = QLabel()
        self.product_desc_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")

        product_info_layout.addWidget(self.product_desc_label)
        self.product_info_frame.setLayout(product_info_layout)
        self.product_info_frame.setVisible(False)

        main_layout.addWidget(self.product_info_frame)

        # Таблица с нормативами
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(3)
        self.table_widget.setHorizontalHeaderLabels([
            "Имя элемента", "ΔC", "Отн. ΔC, %"
        ])

        # Настройка размеров колонок
        self.table_widget.setColumnWidth(0, 120)  # Фиксированная ширина для имен элементов
        self.table_widget.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table_widget.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_widget.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Увеличиваем ширину номеров строк
        self.table_widget.verticalHeader().setDefaultSectionSize(30)
        self.table_widget.verticalHeader().setMinimumWidth(50)

        self.table_widget.setAlternatingRowColors(True)
        self.table_widget.setSelectionBehavior(QTableWidget.SelectRows)

        # Разрешаем редактирование только для колонок deltaC
        self.table_widget.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.EditKeyPressed)

        # Добавляем разделитель
        splitter = QSplitter(Qt.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(top_frame)
        splitter.addWidget(self.table_widget)
        splitter.setSizes([100, 400])

        main_layout.addWidget(splitter)

    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        self.product_combo.currentIndexChanged.connect(self.on_product_changed)
        self.save_btn.clicked.connect(self.save_all_changes)
        self.refresh_btn.clicked.connect(self.refresh_data)
        self.table_widget.itemChanged.connect(self.on_item_changed)

    def on_product_changed(self, index):
        """Обработчик изменения продукта"""
        # Загружаем данные
        self.load_standards()

    def refresh_data(self):
        """Обновляет данные"""
        # Перезагружаем конфигурационные файлы
        self.elements_config = self._load_elements_config()
        self.products_config = self._load_products_config()

        # Загружаем данные
        self.load_standards()

    def load_standards(self):
        """Загружает нормативы из базы данных"""
        try:
            # Отключаем сигнал itemChanged чтобы избежать рекурсии при заполнении
            self.table_widget.itemChanged.disconnect(self.on_item_changed)

            product_nmb = self.product_combo.currentIndex() + 1

            # Обновляем описание продукта
            product_desc = self._get_product_desc(product_nmb)
            self.product_desc_label.setText(product_desc)
            self.product_info_frame.setVisible(True)

            # Загружаем данные из таблицы set08 с двойной сортировкой
            query = """
            SELECT s.id, s.pr_nmb, s.el_nmb, s.delta_c_01, s.delta_c_02 
            FROM set08 s
            WHERE s.pr_nmb = ? 
            ORDER BY s.pr_nmb, s.el_nmb
            """
            results = self.db.fetch_all(query, [product_nmb])

            if not results:
                self.table_widget.setRowCount(0)
                QMessageBox.information(self, "Информация", "Данные для выбранного продукта не найдены.")
                return

            self.table_widget.setRowCount(len(results))

            for row_idx, row in enumerate(results):
                el_nmb = row.get('el_nmb', 0)

                # Имя элемента
                element_name = self._get_element_name(el_nmb)
                element_item = QTableWidgetItem(element_name)
                element_item.setFlags(element_item.flags() & ~Qt.ItemIsEditable)
                self.table_widget.setItem(row_idx, 0, element_item)

                # ΔC (редактируемая)
                delta_c_item = QTableWidgetItem(str(row.get('delta_c_01', 0)))
                delta_c_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                delta_c_item.setData(Qt.UserRole, row)
                self.table_widget.setItem(row_idx, 1, delta_c_item)

                # Отн. ΔC, % (редактируемая)
                delta_c_percent_item = QTableWidgetItem(str(row.get('delta_c_02', 0)))
                delta_c_percent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                delta_c_percent_item.setData(Qt.UserRole, row)
                self.table_widget.setItem(row_idx, 2, delta_c_percent_item)

            # Включаем сигнал обратно
            self.table_widget.itemChanged.connect(self.on_item_changed)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки нормативов: {str(e)}")
            self.table_widget.setRowCount(0)
            self.table_widget.itemChanged.connect(self.on_item_changed)

    def on_item_changed(self, item):
        """Обработчик изменения ячейки таблицы"""
        if item.column() not in [1, 2]:
            return

        try:
            value = item.text()
            if value:
                float(value)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректное числовое значение")
            self.table_widget.itemChanged.disconnect(self.on_item_changed)
            item.setText("0")
            self.table_widget.itemChanged.connect(self.on_item_changed)
            return

    def save_all_changes(self):
        """Сохраняет все изменения в базе данных"""
        try:
            changes_made = False

            for row in range(self.table_widget.rowCount()):
                delta_c_item = self.table_widget.item(row, 1)
                delta_c_percent_item = self.table_widget.item(row, 2)

                if not delta_c_item or not delta_c_percent_item:
                    continue

                original_data = delta_c_item.data(Qt.UserRole)
                if not original_data:
                    continue

                new_delta_c_01 = float(delta_c_item.text()) if delta_c_item.text() else 0
                new_delta_c_02 = float(delta_c_percent_item.text()) if delta_c_percent_item.text() else 0
                old_delta_c_01 = original_data.get('delta_c_01', 0)
                old_delta_c_02 = original_data.get('delta_c_02', 0)

                if new_delta_c_01 != old_delta_c_01 or new_delta_c_02 != old_delta_c_02:
                    changes_made = True

                    id_value = original_data.get('id')
                    query = """
                    UPDATE set08 SET delta_c_01 = ?, delta_c_02 = ?
                    WHERE id = ?
                    """
                    self.db.execute(query, [new_delta_c_01, new_delta_c_02, id_value])

            if changes_made:
                QMessageBox.information(self, "Успех", "Изменения успешно сохранены!")
                self.refresh_data()
            else:
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения.")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения нормативов: {str(e)}")

    def showEvent(self, event):
        """Обработчик события показа виджета"""
        super().showEvent(event)
        self.elements_config = self._load_elements_config()
        self.products_config = self._load_products_config()
        self.load_standards()
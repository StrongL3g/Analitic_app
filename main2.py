import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QWidget, QSplitter
)
from PySide6.QtCore import Qt, QCoreApplication

# Настройки масштабирования для HighDPI
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

app = QApplication(sys.argv)

# Импорты страниц
from database.db import Database
from views.dashboard import DashboardPage
from views.measurement.lines import LinesPage
from views.measurement.ranges import RangesPage
from views.measurement.background import BackgroundPage
from views.measurement.params import ParamsPage
from views.measurement.elements import ElementsPage
from views.measurement.criteria import CriteriaPage
from views.products.equations import EquationsPage
from views.products.models import ModelsPage
from views.data.composition import CompositionPage
from views.data.regression import RegressionPage
from views.data.correction import CorrectionPage
from views.data.recalc import RecalcPage
from views.data.standards import StandardsPage
from views.data.report import ReportPage
from views.settings import SettingsPage
from views.users import UsersPage
from views.logs import LogsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система анализа спектров")
        self.resize(1200, 800)

        # Текущая роль пользователя
        self.current_role = "Инженер-программист"

        # Подключение к БД
        self.db = Database()

        # Основной разделитель
        splitter = QSplitter(Qt.Horizontal)

        # === Левое меню ===
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFixedWidth(250)
        self.tree.setStyleSheet("QTreeWidget { font-size: 13px; }")

        # Заполнение дерева меню
        self.tree.addTopLevelItem(self.create_menu_item("Главный", "dashboard"))

        measurement_item = self.create_menu_item("Управление измерениями", "measurement")
        measurement_item.addChild(self.create_menu_item("Спектральные линии", "lines"))
        measurement_item.addChild(self.create_menu_item("Спектральные диапазоны", "ranges"))
        measurement_item.addChild(self.create_menu_item("Фон и наложения", "background"))
        measurement_item.addChild(self.create_menu_item("Параметры измерения", "params"))
        measurement_item.addChild(self.create_menu_item("Элементы", "elements"))
        measurement_item.addChild(self.create_menu_item("Критерии проверок", "criteria"))

        products_item = self.create_menu_item("Управление продуктами", "products")
        products_item.addChild(self.create_menu_item("Ввод уравнений связи", "equations"))
        products_item.addChild(self.create_menu_item("Активные модели", "models"))

        data_item = self.create_menu_item("Управление данными", "data")
        data_item.addChild(self.create_menu_item("Ввод химических содержаний", "composition"))
        data_item.addChild(self.create_menu_item("Регрессия", "regression"))
        data_item.addChild(self.create_menu_item("Корректировка", "correction"))
        data_item.addChild(self.create_menu_item("Свободный пересчет", "recalc"))
        data_item.addChild(self.create_menu_item("Нормативы", "standards"))
        data_item.addChild(self.create_menu_item("Отчет", "report"))

        self.tree.addTopLevelItem(measurement_item)
        self.tree.addTopLevelItem(products_item)
        self.tree.addTopLevelItem(data_item)

        # Разделы только для инженера-программиста
        if self.current_role == "Инженер-программист":
            settings_item = self.create_menu_item("Настройки", "settings")
            users_item = self.create_menu_item("Пользователи", "users")
            logs_item = self.create_menu_item("Журнал", "logs")
            self.tree.addTopLevelItem(settings_item)
            self.tree.addTopLevelItem(users_item)
            self.tree.addTopLevelItem(logs_item)

        # === Область контента ===
        self.stacked_widget = QStackedWidget()

        # Словарь классов страниц
        self.page_classes = {
            "dashboard": DashboardPage,

            "lines": LinesPage,
            "ranges": RangesPage,
            "background": BackgroundPage,
            "params": ParamsPage,
            "elements": ElementsPage,
            "criteria": CriteriaPage,

            "equations": EquationsPage,
            "models": ModelsPage,

            "composition": CompositionPage,
            "regression": RegressionPage,
            "correction": CorrectionPage,
            "recalc": RecalcPage,
            "standards": StandardsPage,
            "report": ReportPage,

            "settings": SettingsPage,
            "users": UsersPage,
            "logs": LogsPage
        }

        # Страницы, требующие подключения к БД
        self.db_pages = {
            "lines", "ranges", "background", "params",
            "elements", "criteria", "composition", "regression"
        }

        # Текущая страница
        self.current_page = None

        # Подключение сигналов
        self.tree.itemClicked.connect(self.on_item_clicked)

        # Добавление виджетов в разделитель
        splitter.addWidget(self.tree)
        splitter.addWidget(self.stacked_widget)

        # Установка разделителя как центрального виджета
        self.setCentralWidget(splitter)

        # Сразу открываем главную страницу
        self.create_and_show_page("dashboard")

    def create_menu_item(self, text, key):
        """Создает элемент меню с заданным текстом и ключом"""
        item = QTreeWidgetItem()
        item.setText(0, text)
        item.setData(0, Qt.UserRole, key)
        return item

    def create_and_show_page(self, key):
        """Создает новую страницу и удаляет предыдущую"""
        if key not in self.page_classes:
            return

        # Удаляем текущую страницу, если она есть
        if self.current_page:
            self.stacked_widget.removeWidget(self.current_page)
            self.current_page.deleteLater()

        # Создаем новую страницу
        if key in self.db_pages:
            page = self.page_classes[key](self.db)  # Страницы, требующие db
        else:
            page = self.page_classes[key]()  # Остальные страницы

        self.current_page = page
        self.stacked_widget.addWidget(page)
        self.stacked_widget.setCurrentWidget(page)


    def on_item_clicked(self, item, column):
        """Обработчик клика по пункту меню"""
        key = item.data(0, Qt.UserRole)
        if key:
            self.create_and_show_page(key)


# Запуск приложения
if __name__ == "__main__":
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

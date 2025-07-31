# main.py
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QWidget, QVBoxLayout, QLabel, QSplitter
)
from PySide6.QtCore import Qt

# === ВАЖНО: импорты до создания QApplication ===
from PySide6.QtCore import QCoreApplication
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

# === Теперь создаём QApplication ===
app = QApplication(sys.argv)

# === Подключаем БД и страницы ===
from database.db import Database
from views.dashboard import DashboardPage

# Импорт всех страниц
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

        # === Создаём подключение к БД ===
        self.db = Database()

        # Разделитель: слева — меню, справа — контент
        splitter = QSplitter(Qt.Horizontal)

        # === ЛЕВОЕ МЕНЮ: дерево ===
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setFixedWidth(250)
        self.tree.setStyleSheet("QTreeWidget { font-size: 13px; }")

        # Заполняем дерево
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

        settings_item = self.create_menu_item("Настройки", "settings")
        users_item = self.create_menu_item("Пользователи", "users")
        logs_item = self.create_menu_item("Журнал", "logs")

        self.tree.addTopLevelItem(measurement_item)
        self.tree.addTopLevelItem(products_item)
        self.tree.addTopLevelItem(data_item)

        # Ограничиваем доступ к разделам
        if self.current_role == "Инженер-программист":
            self.tree.addTopLevelItem(settings_item)
            self.tree.addTopLevelItem(users_item)
            self.tree.addTopLevelItem(logs_item)

        # === ЦЕНТР: контент ===
        self.stacked_widget = QStackedWidget()

        # Добавим страницы
        self.pages = {}

        self.pages["dashboard"] = DashboardPage()

        self.pages["lines"] = LinesPage(self.db)
        self.pages["ranges"] = RangesPage(self.db)
        self.pages["background"] = BackgroundPage()
        self.pages["params"] = ParamsPage()
        self.pages["elements"] = ElementsPage(self.db)  # ← передаём db
        self.pages["criteria"] = CriteriaPage()

        self.pages["equations"] = EquationsPage()
        self.pages["models"] = ModelsPage()

        self.pages["composition"] = CompositionPage()
        self.pages["regression"] = RegressionPage()
        self.pages["correction"] = CorrectionPage()
        self.pages["recalc"] = RecalcPage()
        self.pages["standards"] = StandardsPage()
        self.pages["report"] = ReportPage()

        self.pages["settings"] = SettingsPage()
        self.pages["users"] = UsersPage()
        self.pages["logs"] = LogsPage()

        for name, page in self.pages.items():
            self.stacked_widget.addWidget(page)

        # === Сигнал: при клике в дереве — меняем страницу ===
        self.tree.itemClicked.connect(self.on_item_clicked)

        # Добавляем в сплиттер
        splitter.addWidget(self.tree)
        splitter.addWidget(self.stacked_widget)

        self.setCentralWidget(splitter)

    def create_menu_item(self, text, key):
        item = QTreeWidgetItem()
        item.setText(0, text)
        item.setData(0, Qt.UserRole, key)
        return item

    def on_item_clicked(self, item, column):
        key = item.data(0, Qt.UserRole)
        if key and key in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[key])


# === Запуск приложения ===
window = MainWindow()
window.show()
app.exec()

# main3.py
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QWidget, QSplitter
)
from PySide6.QtCore import Qt#, QCoreApplication

# Импортируем конфиг БД
from config import DB_CONFIG

# Импортируем Alarm manager и перечень аварий
from services.alarm_manager import AlarmManager
from plc.alarms_list import alarms

#Импортируем класс подключения к OPC UA
from plc.connection import OPCUAWorker


# Настройки масштабирования для HighDPI
# Эти атрибуты устарели в Qt6, но оставим на всякий случай
#QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
#QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

app = QApplication(sys.argv)

# Импорты страниц (только классы, без создания экземпляров)
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
#from views.ac.ac import ACPage
from views.cfg.cfg_01 import Cfg01Page
from views.cfg.cfg_02 import Cfg02Page
from views.cfg.cfg_03 import Cfg03Page



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Система анализа спектров")
        self.setMinimumSize(1200, 800)
        #self.resize(1920, 1080)
        self.resize(1200, 800)

        # Текущая роль пользователя
        self.current_role = "Инженер-программист"

        # Подключение к БД
        self.db = Database(DB_CONFIG)

        # Запускаем в работу AlarmManager
        #self.alarm_manager = AlarmManager(self.db, alarms)

        # Запускаем OPC UA воркер
        #self.plc_worker = OPCUAWorker("opc.tcp://192.168.102.7:4840")

        # Связываем OPC и Alarm
        #self.plc_worker.data_updated.connect(self.alarm_manager.check_data)

        #self.plc_worker.start()

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

        cfg_item = self.create_menu_item("Конфигуратор", "cfg")
        cfg_item.addChild(self.create_menu_item("Измерения", "cfg_measure"))
        cfg_item.addChild(self.create_menu_item("Продукты", "cfg_products"))
        cfg_item.addChild(self.create_menu_item("Отбор", "cfg_samplers"))

        #ac_item = self.create_menu_item("АК21", "ac")
        #ac_item.addChild(self.create_menu_item("Управление", "ac"))

        self.tree.addTopLevelItem(measurement_item)
        self.tree.addTopLevelItem(products_item)
        self.tree.addTopLevelItem(data_item)
        self.tree.addTopLevelItem(cfg_item)
        #self.tree.addTopLevelItem(ac_item)

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
            "logs": LogsPage,
            "cfg_measure": Cfg01Page,
            "cfg_products": Cfg02Page,
            "cfg_samplers": Cfg03Page,
            #"ac": ACPage
        }

        # Страницы, требующие подключения к БД
        self.db_pages = {
            "lines", "ranges", "background", "params",
            "elements", "criteria", "composition", "regression", "settings",
            "equations", "models", "standards", "report", "cfg_measure",
            "cfg_products", "cfg_samplers", #"ac"
        }

        # Страницы, требующие проброса Alarm Manager
        #self.alarm_pages = {"ac"}

        # Страницы, требующие подключения к OPC UA
        #self.plc_pages = {"ac"}

        # Кэш созданных страниц
        self.page_cache = {}

        # Подключение сигналов
        self.tree.itemClicked.connect(self.on_item_clicked)

        # Добавление виджетов в разделитель
        splitter.addWidget(self.tree)
        splitter.addWidget(self.stacked_widget)

        # Установка разделителя как центрального виджета
        self.setCentralWidget(splitter)

        # Сразу открываем главную страницу
        self.show_page("dashboard")

    def create_menu_item(self, text, key):
        """Создает элемент меню с заданным текстом и ключом"""
        item = QTreeWidgetItem()
        item.setText(0, text)
        item.setData(0, Qt.UserRole, key)
        return item

    def show_page(self, key):
        """Показывает страницу (создает при первом обращении, далее использует кэш)"""
        if key not in self.page_classes:
            return

        # Проверяем, есть ли страница в кэше
        if key in self.page_cache:
            # Если есть - просто показываем
            page = self.page_cache[key]
        else:
            # Если нет - создаем и сохраняем в кэш
            # Определяем аргументы для создания страницы
            args = []
            # Если странице нужна БД — добавляем её в аргументы
            if key in self.db_pages:
                args.append(self.db)
            # Если странице нужен ПЛК — добавляем воркер в аргументы
            #if key in self.plc_pages:
            #    args.append(self.plc_worker)
            # 3. Добавляем AlarmManager, если он нужен странице
            #if hasattr(self, 'alarm_pages') and key in self.alarm_pages:
            #    args.append(self.alarm_manager)

            # Создаем экземпляр класса с собранными аргументами (*args распакует список)
            page = self.page_classes[key](*args)

            # Сохраняем в кэш и добавляем в виджет
            self.page_cache[key] = page
            self.stacked_widget.addWidget(page)

        # Показываем страницу
        self.stacked_widget.setCurrentWidget(page)

    def on_item_clicked(self, item, column):
        """Обработчик клика по пункту меню"""
        key = item.data(0, Qt.UserRole)
        if key:
            self.show_page(key)

    def closeEvent(self, event):
        #self.plc_worker.stop()
        event.accept()

# Запуск приложения
if __name__ == "__main__":
    window = MainWindow()
    window.show()
    sys.exit(app.exec())



# main.py
import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTreeWidget, QTreeWidgetItem,
    QStackedWidget, QWidget, QSplitter, QDialog
)
from PySide6.QtCore import Qt

# Импортируем конфиг БД
from config import DB_CONFIG, refresh_app_settings

app = QApplication(sys.argv)
app.setStyle("Fusion")

# --- ИНТЕГРАЦИЯ СТИЛЕЙ ТЕМЫ ---
from utils.theme_manager import apply_application_theme

apply_application_theme(app)
# ------------------------------

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
from views.cfg.cfg_main import CfgMainPage
from views.cfg.cfg_ac import CfgacPage
from views.cfg.cfg_pr import CfgprPage
from views.cfg.cfg_sp import CfgspPage
from views.data.rf_meas import RfMeasPage

# ИМПОРТ ОКНА АВТОРИЗАЦИИ
from views.login import LoginDialog


class MainWindow(QMainWindow):
    def __init__(self, user_role="Аналитик"):
        super().__init__()

        # 1. ОБНОВЛЯЕМ НАСТРОЙКИ ИЗ БД ПЕРЕД СОЗДАНИЕМ ИНТЕРФЕЙСА
        refresh_app_settings()

        # Текущая роль пользователя (получаем из окна логина)
        self.current_role = user_role

        self.setWindowTitle(f"Система анализа спектров - [{self.current_role}]")
        self.setMinimumSize(1200, 800)
        self.resize(1200, 800)

        # Подключение к БД
        self.db = Database(DB_CONFIG)

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
        data_item.addChild(self.create_menu_item("Интенсивности репера", "rf_meas"))  # <--- Добавили меню
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
            cfg_item = self.create_menu_item("Конфигуратор", "cfg_main")
            cfg_item.addChild(self.create_menu_item("Приборы", "cfg_ac"))
            cfg_item.addChild(self.create_menu_item("Продукты", "cfg_pr"))
            cfg_item.addChild(self.create_menu_item("Пробоотборники", "cfg_sp"))
            self.tree.addTopLevelItem(cfg_item)

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
            "rf_meas": RfMeasPage,
            "standards": StandardsPage,
            "report": ReportPage,
            "settings": SettingsPage,
            "users": UsersPage,
            "logs": LogsPage,
            "cfg_main": CfgMainPage,
            "cfg_ac": CfgacPage,
            "cfg_pr": CfgprPage,
            "cfg_sp": CfgspPage,
        }

        # Страницы, требующие подключения к БД
        self.db_pages = {
            "lines", "ranges", "background", "params",
            "elements", "criteria", "composition", "regression", "correction", "recalc", "settings",
            "equations", "models", "standards", "report", "cfg_main", "cfg_ac",
            "cfg_pr", "cfg_sp", "rf_meas"
        }

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
        item = QTreeWidgetItem()
        item.setText(0, text)
        item.setData(0, Qt.UserRole, key)
        return item

    def show_page(self, key):
        if key not in self.page_classes:
            return

        if key in self.page_cache:
            page = self.page_cache[key]
        else:
            args = []
            if key in self.db_pages:
                args.append(self.db)

            page = self.page_classes[key](*args)
            self.page_cache[key] = page
            self.stacked_widget.addWidget(page)

        if hasattr(page, 'refresh'):
            page.refresh()

        self.stacked_widget.setCurrentWidget(page)

    def on_item_clicked(self, item, column):
        key = item.data(0, Qt.UserRole)
        if key:
            self.show_page(key)

    def do_logout(self):
        """Устанавливает флаг выхода и закрывает окно"""
        self.wants_logout = True
        self.close()


# ЗАПУСК ПРИЛОЖЕНИЯ
if __name__ == "__main__":
    while True:
        # 1. Показываем окно логина
        login_dialog = LoginDialog()

        # 2. Если логин успешен
        if login_dialog.exec() == QDialog.Accepted:
            # 3. Запускаем главное окно
            window = MainWindow(user_role=login_dialog.user_role)
            window.show()

            # Ждем, пока окно не будет закрыто
            app.exec()

            # 4. Проверяем причину закрытия
            if getattr(window, 'wants_logout', False):
                # Если нажали "Сменить пользователя" -> идем на новый круг цикла (снова логин)
                continue
            else:
                # Если просто закрыли крестиком -> выходим из приложения
                break
        else:
            # Отменили авторизацию (закрыли окно логина) -> выходим
            break

    sys.exit(0)
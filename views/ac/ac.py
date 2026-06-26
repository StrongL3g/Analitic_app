from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QFrame, QStackedWidget, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, QTimer, QDateTime, Slot, QPropertyAnimation, QRect, QEasingCurve

# Импортируем твои страницы
from views.ac.ac_main import ACMainPage
from views.ac.man_meas import ManualMeasPage
from views.ac.em import EMPage
from views.ac.detector import DetectorPage
from views.ac.check import CheckPage
from views.ac.cooling import CoolingPage
from views.ac.alarms import AlarmsPage
from views.ac.system import SystemPage


class ACPage(QWidget):
    def __init__(self, db, plc_worker, alarm_manager):
        super().__init__()
        self.db = db
        self.plc_worker = plc_worker
        self.alarm_manager = alarm_manager

        self.menu_data = [
            ("Главная", "🏠"), ("Ручное измерение", "🖐"), ("Исп. механизмы", "⚙"),
            ("Детектор", "☢"), ("Тестирование", "🧪"), ("Охлаждение", "❄"),
            ("Аварии", "🔔"), ("Система", "🛠")
        ]
        self.indicators = {}
        self.init_ui()

        # Таймер времени
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_and_status)
        self.timer.start(1000)

        if self.plc_worker:
            self.plc_worker.status_changed.connect(self.update_plc_status)

    def init_ui(self):
        self.setStyleSheet("background-color: #E0E0E0;")
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # --- HEADER (Блок управления + Черная голова) ---
        self.top_bar_layout = QHBoxLayout()
        self.top_bar_layout.setContentsMargins(10, 10, 10, 0)

        # Левый белый квадрат
        self.ctrl_panel = QFrame()
        self.ctrl_panel.setFixedSize(180, 85)
        self.ctrl_panel.setStyleSheet("background-color: white; border-radius: 5px; border: 1px solid #CCC;")
        ctrl_layout = QVBoxLayout(self.ctrl_panel)

        ctrl_top = QHBoxLayout()
        self.menu_btn = QPushButton("☰")
        self.menu_btn.setFixedSize(35, 35)
        self.menu_btn.setStyleSheet("font-size: 20px; border: none; background: transparent;")
        self.menu_btn.clicked.connect(self.toggle_menu_anim)

        self.stop_btn = QPushButton("СТОП")
        self.stop_btn.setStyleSheet(
            "font-weight: bold; background: white; border: 1px solid #999; border-radius: 10px; padding: 5px;")

        ctrl_top.addWidget(self.menu_btn)
        ctrl_top.addWidget(self.stop_btn)
        ctrl_layout.addLayout(ctrl_top)

        self.side_info = QLabel("Загрузка...")
        self.side_info.setStyleSheet("color: #444; font-size: 10px; border: none;")
        ctrl_layout.addWidget(self.side_info)
        self.top_bar_layout.addWidget(self.ctrl_panel)

        # Черный хедер
        self.header = QFrame()
        self.header.setFixedHeight(85)
        self.header.setStyleSheet("background-color: black; border-radius: 10px;")
        h_layout = QHBoxLayout(self.header)

        self.plc_led = QLabel("ПЛК ■")
        self.plc_led.setStyleSheet("color: #777; font-size: 14px; margin-left: 15px;")
        self.indicators["ПЛК"] = self.plc_led
        h_layout.addWidget(self.plc_led)
        h_layout.addStretch()

        self.time_label = QLabel()
        self.time_label.setStyleSheet("color: white; font-family: monospace; font-size: 18px; margin-right: 15px;")
        h_layout.addWidget(self.time_label)

        self.top_bar_layout.addWidget(self.header)
        self.main_layout.addLayout(self.top_bar_layout)

        # --- СТЕК СТРАНИЦ ---
        self.stack = QStackedWidget()

        # Инстанцируем страницы
        self.ac_main = ACMainPage()
        self.man_meas = ManualMeasPage()
        self.em_page = EMPage(self.db, self.plc_worker)
        self.detector = DetectorPage()
        self.check = CheckPage()
        self.cooling = CoolingPage()
        self.alarms = AlarmsPage(self.db, self.alarm_manager)
        self.system = SystemPage()

        # Добавляем в стек (индексы: ac_main=0, man_meas = 1, em_page=2, ....)
        self.stack.addWidget(self.ac_main)
        self.stack.addWidget(self.man_meas)
        self.stack.addWidget(self.em_page)
        self.stack.addWidget(self.detector)
        self.stack.addWidget(self.check)
        self.stack.addWidget(self.cooling)
        self.stack.addWidget(self.alarms)
        self.stack.addWidget(self.system)

        self.main_layout.addWidget(self.stack)

        # --- ВЫПАДАЮЩЕЕ МЕНЮ (OVERLAY) ---
        self.dropdown_menu = QFrame(self)
        self.dropdown_menu.setGeometry(10, 100, 180, 0)
        self.dropdown_menu.setStyleSheet("""
            QFrame { background-color: white; border: 1px solid #CCC; border-top: none; border-bottom-left-radius: 5px; border-bottom-right-radius: 5px; }
            QPushButton { text-align: left; padding: 12px; border: none; background: white; font-size: 12px; }
            QPushButton:hover { background: #EEE; }
        """)

        self.menu_layout = QVBoxLayout(self.dropdown_menu)
        self.menu_layout.setContentsMargins(0, 0, 0, 0)
        self.menu_layout.setSpacing(0)

        for text, icon in self.menu_data:
            btn = QPushButton(f"{icon}  {text}")
            self.menu_layout.addWidget(btn)

            # Настраиваем переходы
            if text == "Главная":
                btn.clicked.connect(lambda: self.switch_page(0))
            elif text == "Ручное измерение":
                btn.clicked.connect(lambda: self.switch_page(1))
            elif text == "Исп. механизмы":
                btn.clicked.connect(lambda: self.switch_page(2))
            elif text == "Детектор":
                btn.clicked.connect(lambda: self.switch_page(3))
            elif text == "Тестирование":
                btn.clicked.connect(lambda: self.switch_page(4))
            elif text == "Охлаждение":
                btn.clicked.connect(lambda: self.switch_page(5))
            elif text == "Аварии":
                btn.clicked.connect(lambda: self.switch_page(6))
            elif text == "Система":
                btn.clicked.connect(lambda: self.switch_page(7))
        self.dropdown_menu.hide()

    def switch_page(self, index):
        """Переключает страницу и закрывает меню"""
        self.stack.setCurrentIndex(index)
        self.toggle_menu_anim()

    def toggle_menu_anim(self):
        if self.dropdown_menu.height() == 0:
            self.dropdown_menu.show()
            self.anim = QPropertyAnimation(self.dropdown_menu, b"geometry")
            self.anim.setDuration(250)
            self.anim.setStartValue(QRect(10, 100, 180, 0))
            self.anim.setEndValue(QRect(10, 100, 180, 380))
            self.anim.setEasingCurve(QEasingCurve.OutQuad)
            self.anim.start()
        else:
            self.anim = QPropertyAnimation(self.dropdown_menu, b"geometry")
            self.anim.setDuration(200)
            self.anim.setStartValue(QRect(10, 100, 180, 380))
            self.anim.setEndValue(QRect(10, 100, 180, 0))
            self.anim.setEasingCurve(QEasingCurve.InQuad)
            self.anim.finished.connect(self.dropdown_menu.hide)
            self.anim.start()

    def update_time_and_status(self):
        curr = QDateTime.currentDateTime()
        self.time_label.setText(curr.toString("hh:mm:ss\ndd.MM.yyyy"))
        self.side_info.setText(curr.toString("dd.MM.yyyy hh:mm") + "\n802 сек.")

    @Slot(bool)
    def update_plc_status(self, connected):
        color = "#00FF00" if connected else "#FF0000"
        self.plc_led.setStyleSheet(f"color: {color}; font-size: 14px; margin-left: 15px;")
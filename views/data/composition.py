from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QCheckBox, QListWidget, QListWidgetItem, QComboBox, QSizePolicy, QDateTimeEdit,
    QTimeEdit, QMessageBox, QGridLayout
)
from PySide6.QtCore import Qt, QEvent, QDateTime, QTime
from PySide6.QtGui import QGuiApplication
from database.db import Database


class TimeEdit15Min(QTimeEdit):
    #Кастомный QTimeEdit с шагом 15 минут

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("HH:mm")
        self.setTime(QTime(0, 0))

    def stepBy(self, steps):
        #Переопределяем изменение значения стрелочками
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

    def init_ui(self):
        main_layout = QVBoxLayout()

        # Заголовок
        title = QLabel("Ввод химических содержаний")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Основной контейнер
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Левая колонка - чекбоксы
        checkboxes_layout = QVBoxLayout()
        checkboxes_layout.setContentsMargins(0, 0, 20, 0)

        self.check_man = QCheckBox("Ручное измерение")
        self.check_man.stateChanged.connect(self.on_checkbox_change)
        checkboxes_layout.addWidget(self.check_man)

        self.check_chem = QCheckBox("Наличие химии")
        checkboxes_layout.addWidget(self.check_chem)

        self.check_inten = QCheckBox("Интенсивности")
        checkboxes_layout.addWidget(self.check_inten)

        content_layout.addLayout(checkboxes_layout)

        # Правая колонка - поля дат
        dates_layout = QGridLayout()
        dates_layout.setHorizontalSpacing(10)

        # Заголовки
        dates_layout.addWidget(QLabel("От:"), 0, 0)
        dates_layout.addWidget(QLabel("До:"), 0, 2)

        # Поля "От"
        self.date_from = QDateTimeEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDateTime(QDateTime.currentDateTime())
        self.date_from.setFixedWidth(100)

        self.time_from = TimeEdit15Min()
        self.time_from.setTime(self.round_to_15_min(QTime.currentTime()))

        dates_layout.addWidget(self.date_from, 1, 0)
        dates_layout.addWidget(self.time_from, 1, 1)

        # Поля "До"
        self.date_to = QDateTimeEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDateTime(QDateTime.currentDateTime().addDays(1))
        self.date_to.setFixedWidth(100)

        self.time_to = TimeEdit15Min()
        self.time_to.setTime(self.round_to_15_min(QTime.currentTime()))

        dates_layout.addWidget(self.date_to, 1, 2)
        dates_layout.addWidget(self.time_to, 1, 3)

        content_layout.addLayout(dates_layout)
        main_layout.addLayout(content_layout)

        # Комбобокс с продуктами
        self.product_combo = QComboBox()
        products = [f"Продукт {i}" for i in range(1, 9)]
        self.product_combo.addItems(products)
        self.product_combo.setFixedWidth(150)

        main_layout.addWidget(QLabel("Выберите продукт:"))
        main_layout.addWidget(self.product_combo)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(["ID", "Номер", "Название"])
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        main_layout.addWidget(self.table)

        # Подключение валидации
        self.date_from.dateTimeChanged.connect(self.validate_dates)
        self.time_from.timeChanged.connect(self.validate_dates)
        self.date_to.dateTimeChanged.connect(self.validate_dates)
        self.time_to.timeChanged.connect(self.validate_dates)

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

        self.setLayout(main_layout)

    def load_data(self):
        print("Заглушка")

    def save_data(self):
        print("Заглушка")
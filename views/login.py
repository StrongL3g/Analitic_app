# views/login.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QComboBox
from PySide6.QtCore import Qt


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setFixedSize(300, 300)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        # Переменная для хранения роли авторизованного пользователя
        self.user_role = None

        # Временная база пользователей (позже заменишь на запрос к БД)
        self.users_db = {
            "Аналитик": {"password": "123", "role": "Аналитик"},
            "Инженер": {"password": "admin", "role": "Инженер-программист"}
        }

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel("Вход в систему")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addWidget(QLabel("Пользователь:"))
        self.combo_user = QComboBox()
        self.combo_user.addItems(self.users_db.keys())
        layout.addWidget(self.combo_user)

        layout.addWidget(QLabel("Пароль:"))
        self.line_password = QLineEdit()
        self.line_password.setEchoMode(QLineEdit.Password)  # Скрываем вводимые символы звездочками
        # По нажатию Enter пытаемся войти
        self.line_password.returnPressed.connect(self.check_login)
        layout.addWidget(self.line_password)

        self.btn_login = QPushButton("Войти")
        self.btn_login.setFixedHeight(35)
        self.btn_login.clicked.connect(self.check_login)
        layout.addWidget(self.btn_login)

    def check_login(self):
        username = self.combo_user.currentText()
        password = self.line_password.text()

        if username in self.users_db and self.users_db[username]["password"] == password:
            self.user_role = self.users_db[username]["role"]
            self.accept()  # Сигнал успешного закрытия окна
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный пароль!")
            self.line_password.clear()
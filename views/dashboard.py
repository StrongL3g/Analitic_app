from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)

        # Заголовок
        #self.lbl_title = QLabel("<h2>Главный экран</h2><p>Система управления и анализа спектров.</p>")
        #self.lbl_title.setAlignment(Qt.AlignCenter)
        #layout.addWidget(self.lbl_title)

        # Метка для отображения текущей роли
        self.lbl_user = QLabel()
        self.lbl_user.setAlignment(Qt.AlignCenter)
        self.lbl_user.setStyleSheet("font-size: 15px; color: #555;")
        layout.addWidget(self.lbl_user)

        # Кнопка смены пользователя
        btn_layout = QHBoxLayout()
        self.btn_logout = QPushButton("Сменить пользователя")
        self.btn_logout.setFixedSize(200, 40)
        self.btn_logout.setStyleSheet("font-weight: bold; background-color: #e2e8f0; color: #333;")
        self.btn_logout.clicked.connect(self.logout)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_logout)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        layout.addStretch()  # Прижимаем контент к верху

        self.setLayout(layout)

    def refresh(self):
        """Метод вызывается каждый раз при открытии вкладки (настроено в main.py)"""
        # Получаем доступ к главному окну, чтобы узнать текущую роль
        main_win = self.window()
        if hasattr(main_win, 'current_role'):
            self.lbl_user.setText(f"Текущий пользователь: <b>{main_win.current_role}</b>")

    def logout(self):
        """Вызывает процедуру выхода в главном окне"""
        main_win = self.window()
        if hasattr(main_win, 'do_logout'):
            main_win.do_logout()
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class UsersPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("<h2>Пользователи</h2><p>Добавление/удаление пользователей.</p>")
        label.setAlignment(Qt.AlignCenter)  # Теперь Qt доступен
        layout.addWidget(label)
        self.setLayout(layout)

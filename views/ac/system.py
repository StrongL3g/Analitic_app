from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class SystemPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.label = QLabel("СИСТЕМА")
        self.label.setStyleSheet("font-size: 40px; font-weight: bold; color: #555;")
        self.label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.label)
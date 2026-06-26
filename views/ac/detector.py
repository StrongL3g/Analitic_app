from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class DetectorPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.label = QLabel("ДЕТЕКТОР")
        self.label.setStyleSheet("font-size: 40px; font-weight: bold; color: #555;")
        self.label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.label)
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class RecalcPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("<h2>Свободный пересчет</h2><p>Пересчёт состава по новым условиям.</p>")
        label.setAlignment(Qt.AlignCenter)  # Теперь Qt доступен
        layout.addWidget(label)
        self.setLayout(layout)

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class RangesPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("<h2>Спектральные диапазоны</h2><p>Управление диапазонами анализа.</p>")
        label.setAlignment(Qt.AlignCenter)  # Теперь Qt доступен
        layout.addWidget(label)
        self.setLayout(layout)

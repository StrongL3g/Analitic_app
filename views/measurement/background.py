from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

class BackgroundPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout()
        label = QLabel("<h2>Фон и наложения</h2><p>Коррекция фона, учёт мешающих факторов.</p>")
        label.setAlignment(Qt.AlignCenter)  # Теперь Qt доступен
        layout.addWidget(label)
        self.setLayout(layout)

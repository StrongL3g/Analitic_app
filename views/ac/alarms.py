# views/ac/alarms.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
                               QHeaderView, QPushButton, QHBoxLayout, QLabel)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


class AlarmsPage(QWidget):
    def __init__(self, db, alarm_manager):
        super().__init__()
        self.db = db
        self.alarm_manager = alarm_manager
        self.init_ui()

        # Подключаемся к сигналу менеджера
        self.alarm_manager.alarms_updated.connect(self.update_table)

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Верхняя панель
        top_panel = QHBoxLayout()
        self.label_count = QLabel("Активных аварий: 0")
        btn_ack = QPushButton("Квитировать всё")
        btn_ack.setFixedWidth(150)
        btn_ack.clicked.connect(self.alarm_manager.acknowledge_all)

        top_panel.addWidget(self.label_count)
        top_panel.addStretch()
        top_panel.addWidget(btn_ack)
        layout.addLayout(top_panel)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Время", "Сообщение", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self.table)

    def update_table(self, active_alarms):
        """Метод обновляет таблицу на основе списка из памяти"""
        self.table.setRowCount(len(active_alarms))
        self.label_count.setText(f"Активных аварий: {len(active_alarms)}")

        for i, alarm in enumerate(active_alarms):
            # Время
            time_item = QTableWidgetItem(alarm['start_time'])
            self.table.setItem(i, 0, time_item)

            # Сообщение
            msg_item = QTableWidgetItem(alarm['message'])
            self.table.setItem(i, 1, msg_item)

            # Статус квитирования
            status = "ОЖИДАЕТ" if alarm['is_acked'] == 0 else "ПОДТВЕРЖДЕНО"
            status_item = QTableWidgetItem(status)
            self.table.setItem(i, 2, status_item)

            # Цветовая индикация (только для неквитированных)
            if alarm['is_acked'] == 0:
                self._set_row_color(i, QColor(60, 0, 0), Qt.white)  # Темно-красный фон
            else:
                self._set_row_color(i, Qt.transparent, Qt.black)

    def _set_row_color(self, row, bg, fg):
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(bg)
                item.setForeground(fg)
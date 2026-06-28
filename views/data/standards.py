# views/data/standards.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QTableWidget,
                               QTableWidgetItem, QHeaderView, QMessageBox, QPushButton, QHBoxLayout)
from PySide6.QtCore import Qt
from database.db import Database


class StandardsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Нормативы по всем продуктам")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(5)
        self.table_widget.setHorizontalHeaderLabels(["№", "Название продукта", "Элемент", "ΔC", "Отн. ΔC, %"])

        # Настройка ширины столбцов
        self.table_widget.setColumnWidth(0, 40)  # №
        self.table_widget.setColumnWidth(1, 200)  # Название
        self.table_widget.setColumnWidth(2, 100)  # Элемент
        self.table_widget.setColumnWidth(3, 80)  # ΔC
        self.table_widget.setColumnWidth(4, 80)  # Отн. ΔC

        layout.addWidget(self.table_widget)

        # Создаём горизонтальный layout для кнопок
        button_layout = QHBoxLayout()

        refresh_btn = QPushButton("🔄 Обновить")
        refresh_btn.clicked.connect(self.refresh_data)
        button_layout.addWidget(refresh_btn)

        save_btn = QPushButton("💾 Сохранить нормативы")
        save_btn.clicked.connect(self.save_all_changes)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

    def refresh_data(self):
        # ИСПРАВЛЕНИЕ: Добавлен фильтр WHERE s.pr_nmb > 0 для исключения продукта -1
        query = """
            SELECT s.id, s.pr_nmb, p.pr_name, s.el_nmb, e.el_name, s.delta_c_01, s.delta_c_02
            FROM set08 s
            JOIN cfg02 p ON s.pr_nmb = p.pr_nmb
            LEFT JOIN set05 e ON s.el_nmb = e.el_nmb
            WHERE s.pr_nmb > 0
            ORDER BY s.pr_nmb, s.el_nmb
        """
        data = self.db.fetch_all(query)

        # Блокируем обновление таблицы для производительности
        self.table_widget.setUpdatesEnabled(False)
        self.table_widget.setRowCount(0)

        # Сначала заполняем все строки данными
        product_rows = {}  # {pr_nmb: [start_row, count]}

        for row_data in data:
            row = self.table_widget.rowCount()
            self.table_widget.insertRow(row)

            # Сохраняем номер продукта в ячейку (временно, потом объединим)
            pr_nmb_item = QTableWidgetItem(str(row_data['pr_nmb']))
            pr_nmb_item.setTextAlignment(Qt.AlignCenter)
            self.table_widget.setItem(row, 0, pr_nmb_item)

            # Сохраняем название продукта в ячейку
            pr_name_item = QTableWidgetItem(row_data['pr_name'])
            self.table_widget.setItem(row, 1, pr_name_item)

            # Элемент
            el_name = row_data['el_name'] or f"Эл. {row_data['el_nmb']}"
            self.table_widget.setItem(row, 2, QTableWidgetItem(el_name))

            # Значения
            item_d1 = QTableWidgetItem(str(row_data['delta_c_01']))
            item_d2 = QTableWidgetItem(str(row_data['delta_c_02']))
            item_d1.setData(Qt.UserRole, row_data['id'])  # ID для апдейта

            self.table_widget.setItem(row, 3, item_d1)
            self.table_widget.setItem(row, 4, item_d2)

            # Собираем информацию о количестве строк для каждого продукта
            pr_nmb = row_data['pr_nmb']
            if pr_nmb not in product_rows:
                product_rows[pr_nmb] = {'start': row, 'count': 1}
            else:
                product_rows[pr_nmb]['count'] += 1

        # Теперь объединяем ячейки для номеров и названий продуктов
        for pr_nmb, info in product_rows.items():
            start_row = info['start']
            span_count = info['count']

            if span_count > 1:
                # Объединяем ячейки в столбце "№" (индекс 0)
                self.table_widget.setSpan(start_row, 0, span_count, 1)

                # Объединяем ячейки в столбце "Название продукта" (индекс 1)
                self.table_widget.setSpan(start_row, 1, span_count, 1)

                # Для объединённых ячеек можно настроить выравнивание
                # Номер продукта выравниваем по центру
                center_item = self.table_widget.item(start_row, 0)
                if center_item:
                    center_item.setTextAlignment(Qt.AlignCenter)

                # Название продукта можно оставить с выравниванием по левому краю
                name_item = self.table_widget.item(start_row, 1)
                if name_item:
                    name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Включаем обновление таблицы обратно
        self.table_widget.setUpdatesEnabled(True)

        # (Опционально) Если всплывающее окно при каждом открытии вкладки сильно мешает,
        # эту строчку можно закомментировать.
        QMessageBox.information(self, "Обновлено", "Данные успешно обновлены", QMessageBox.Ok)

    def save_all_changes(self):
        try:
            for row in range(self.table_widget.rowCount()):
                # Пропускаем объединённые ячейки (у них item может быть None)
                item_d1 = self.table_widget.item(row, 3)
                if item_d1 is None:
                    continue  # Это объединённая ячейка, пропускаем

                item_id = item_d1.data(Qt.UserRole)
                d1_text = self.table_widget.item(row, 3).text().replace(',', '.')
                d2_text = self.table_widget.item(row, 4).text().replace(',', '.')

                # ИСПРАВЛЕНИЕ: Защита от ввода букв или пустых строк
                try:
                    d1 = float(d1_text) if d1_text else 0.0
                    d2 = float(d2_text) if d2_text else 0.0
                except ValueError:
                    QMessageBox.warning(self, "Ошибка ввода",
                                        f"Некорректное значение в строке {row + 1}.\nПожалуйста, введите число (например, 0.5).")
                    return

                self.db.execute("UPDATE set08 SET delta_c_01 = ?, delta_c_02 = ? WHERE id = ?", [d1, d2, item_id])
            QMessageBox.information(self, "Успех", "Данные сохранены")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка сохранения: {e}")
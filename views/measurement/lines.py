# views/measurement/lines.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout
)
from PySide6.QtCore import Qt
from database.db import Database


class LinesPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}  # id → dict всех полей
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Спектральные линии (SET01)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "№", "Название", "Энергия", "Описание",
            "NC", "Фон", "Вода", "Пусто"
        ])
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)

        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_data)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        """Загружает спектральные линии из SET01"""
        query = """
        SELECT [id], [ln_nmb], [ln_name], [ln_en], [ln_desc],
               [ln_nc], [ln_back], [ln_water], [ln_empty]
        FROM [AMMKASAKDB01].[dbo].[SET01]
        ORDER BY [ln_nmb]
        """
        try:
            data = self.db.fetch_all(query)
            self.table.setRowCount(0)
            self.original_data.clear()

            for row_data in data:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)

                # ID (только для чтения)
                item_id = QTableWidgetItem(str(row_data["id"]))
                item_id.setFlags(item_id.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(row_pos, 0, item_id)

                # Остальные поля
                fields = ["ln_nmb", "ln_name", "ln_en", "ln_desc", "ln_nc", "ln_back", "ln_water", "ln_empty"]
                for col_idx, field in enumerate(fields, start=1):
                    value = row_data[field]
                    item = QTableWidgetItem("" if value is None else str(value))
                    self.table.setItem(row_pos, col_idx, item)

                # Сохраняем оригинальные данные
                self.original_data[row_data["id"]] = {k: "" if v is None else str(v) for k, v in row_data.items()}

        except Exception as e:
            print(f"Ошибка при загрузке спектральных линий: {e}")

    def save_data(self):
        """Сохраняет изменения в БД"""
        updated_count = 0
        string_fields = {"ln_name", "ln_desc"}  # Поля, которые нужно брать в кавычки

        for row in range(self.table.rowCount()):
            item_id = self.table.item(row, 0)
            if not item_id:
                continue

            row_id = int(item_id.text())
            original = self.original_data.get(row_id, {})
            if not original:
                continue

            changes = []
            params = []

            # Проверяем все редактируемые поля
            fields = [
                ("ln_nmb", 1), ("ln_name", 2), ("ln_en", 3), ("ln_desc", 4),
                ("ln_nc", 5), ("ln_back", 6), ("ln_water", 7), ("ln_empty", 8)
            ]

            for db_field, col in fields:
                current_item = self.table.item(row, col)
                if not current_item:
                    continue

                new_value = current_item.text().strip()
                old_value = original.get(db_field, "")

                if new_value != old_value:
                    if db_field in string_fields:
                        changes.append(f"[{db_field}] = ?")
                        params.append(new_value)
                    else:
                        # Для чисел и NULL
                        if new_value == "":
                            changes.append(f"[{db_field}] = NULL")
                        else:
                            changes.append(f"[{db_field}] = ?")
                            try:
                                num_val = float(new_value) if '.' in new_value else int(new_value)
                                params.append(num_val)
                            except ValueError:
                                params.append(new_value)  # fallback

            if changes:
                try:
                    query = f"UPDATE [AMMKASAKDB01].[dbo].[SET01] SET {', '.join(changes)} WHERE [id] = ?"
                    params.append(row_id)
                    self.db.execute(query, params)
                    # Обновляем оригинал
                    for db_field, col in fields:
                        item = self.table.item(row, col)
                        if item:
                            original[db_field] = "" if item.text().strip() == "" else item.text().strip()
                    updated_count += 1
                except Exception as e:
                    print(f"Ошибка при обновлении строки ID={row_id}: {e}")

        if updated_count > 0:
            print(f"Сохранено: {updated_count} строк")
        else:
            print("Изменений не было")

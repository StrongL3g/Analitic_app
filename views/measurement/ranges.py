# views/measurement/ranges.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout
)
from PySide6.QtCore import Qt
from database.db import Database


class RangesPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}  # id → {ln_nmb, ln_ch_min, ln_ch_max}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Спектральные диапазоны (SET02, ak_nmb = 1)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "№", "Min", "Max"])
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
        """Загружает диапазоны из SET02 где ak_nmb = 1"""
        query = """
        SELECT [id], [ln_nmb], [ln_ch_min], [ln_ch_max]
        FROM [AMMKASAKDB01].[dbo].[SET02]
        WHERE [ak_nmb] = 1
        ORDER BY [ID]
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

                # Номер
                item_nmb = QTableWidgetItem(str(row_data["ln_nmb"]))
                item_nmb.setFlags(item_nmb.flags() & ~Qt.ItemIsEditable)  # Только для чтения
                self.table.setItem(row_pos, 1, item_nmb)

                # Min
                self.table.setItem(row_pos, 2, QTableWidgetItem("" if row_data["ln_ch_min"] is None else str(row_data["ln_ch_min"])))

                # Max
                self.table.setItem(row_pos, 3, QTableWidgetItem("" if row_data["ln_ch_max"] is None else str(row_data["ln_ch_max"])))

                # Сохраняем оригинальные данные
                self.original_data[row_data["id"]] = {
                    "ln_ch_min": "" if row_data["ln_ch_min"] is None else str(row_data["ln_ch_min"]),
                    "ln_ch_max": "" if row_data["ln_ch_max"] is None else str(row_data["ln_ch_max"])
                }

        except Exception as e:
            print(f"Ошибка при загрузке спектральных диапазонов: {e}")

    def save_data(self):
        """Сохраняет изменения в БД"""
        updated_count = 0

        for row in range(self.table.rowCount()):
            item_id = self.table.item(row, 0)
            if not item_id:
                continue

            row_id = int(item_id.text())
            original = self.original_data.get(row_id)
            if not original:
                continue

            changes = []
            params = []

            # Проверяем Min
            item_min = self.table.item(row, 2)
            if item_min:
                new_min = item_min.text().strip()
                old_min = original["ln_ch_min"]
                if new_min != old_min:
                    if new_min == "":
                        changes.append("[ln_ch_min] = NULL")
                    else:
                        changes.append("[ln_ch_min] = ?")
                        try:
                            params.append(float(new_min))
                        except ValueError:
                            params.append(new_min)

            # Проверяем Max
            item_max = self.table.item(row, 3)
            if item_max:
                new_max = item_max.text().strip()
                old_max = original["ln_ch_max"]
                if new_max != old_max:
                    if new_max == "":
                        changes.append("[ln_ch_max] = NULL")
                    else:
                        changes.append("[ln_ch_max] = ?")
                        try:
                            params.append(float(new_max))
                        except ValueError:
                            params.append(new_max)

            if changes:
                try:
                    query = f"""
                    UPDATE [AMMKASAKDB01].[dbo].[SET02]
                    SET {', '.join(changes)}
                    WHERE [id] = ? AND [ak_nmb] = 1
                    """
                    params.append(row_id)
                    self.db.execute(query, params)
                    # Обновляем оригинал
                    if item_min:
                        original["ln_ch_min"] = item_min.text().strip()
                    if item_max:
                        original["ln_ch_max"] = item_max.text().strip()
                    updated_count += 1
                except Exception as e:
                    print(f"Ошибка при обновлении диапазона ID={row_id}: {e}")

        if updated_count > 0:
            print(f"Сохранено: {updated_count} строк")
        else:
            print("Изменений не было")

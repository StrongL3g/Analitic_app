# views/measurement/lines.py
import os
import json
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.db import Database


class LinesPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}  # id → dict всех полей
        self.first_load = True    # Флаг для отслеживания первого открытия
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Спектральные линии")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Кнопки - теперь сверху, слева
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        refresh_btn.setFixedWidth(120)

        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_data)
        save_btn.setFixedWidth(180)

        # Новые кнопки для управления строками
        add_btn = QPushButton("Добавить строку")
        add_btn.clicked.connect(self.add_row)
        add_btn.setFixedWidth(150)

        delete_btn = QPushButton("Удалить строку")
        delete_btn.clicked.connect(self.delete_row)
        delete_btn.setFixedWidth(150)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()  # Отступ справа
        layout.addLayout(btn_layout)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(6)  # №, Название, Энергия, Описание, NC, Фон
        self.table.setHorizontalHeaderLabels([
            "№", "Название", "Энергия", "Описание",
            "NC", "Фон"
        ])
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        # Убираем нумерацию строк
        self.table.verticalHeader().setVisible(False)
        # Высота строк
        self.table.verticalHeader().setDefaultSectionSize(30)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_data()

    def load_data(self):
        """Загружает спектральные линии из SET01"""
        # Используем имя базы из объекта db и сортируем по ln_nmb
        query = f"""
        SELECT id, ln_nmb, ln_name, ln_en, ln_desc, ln_nc, ln_back
        FROM SET01
        ORDER BY ln_nmb
        """
        try:
            data = self.db.fetch_all(query)
            self.table.setRowCount(0)
            self.original_data.clear()

            for row_data in data:
                row_pos = self.table.rowCount()
                self.table.insertRow(row_pos)

                # № (не редактируется)
                item_nmb = QTableWidgetItem(str(row_data["ln_nmb"]))
                item_nmb.setFlags(item_nmb.flags() & ~Qt.ItemIsEditable)
                item_nmb.setTextAlignment(Qt.AlignCenter)
                # Цвет фона для номера
                item_nmb.setBackground(QColor(240, 240, 240))
                self.table.setItem(row_pos, 0, item_nmb)

                # Остальные поля
                fields = ["ln_name", "ln_en", "ln_desc", "ln_nc", "ln_back"]
                for col_idx, field in enumerate(fields, start=1):
                    value = row_data[field]
                    item = QTableWidgetItem("" if value is None else str(value))
                    if col_idx in [1, 3]:  # Название и описание - выравнивание по левому краю
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:  # Остальные - по центру
                        item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row_pos, col_idx, item)

                # Сохраняем оригинальные данные (по ID)
                self.original_data[row_data["id"]] = {k: "" if v is None else str(v) for k, v in row_data.items()}

            # Экспортируем в JSON
            self.export_to_json()

            # Показываем сообщение об успешной загрузке только если это не первое открытие
            if not self.first_load:
                QMessageBox.information(self, "Успех", f"Загружено {len(data)} спектральных линий")
            else:
                self.first_load = False  # Сбрасываем флаг после первого открытия

        except Exception as e:
            error_msg = f"Ошибка при загрузке спектральных линий: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def save_data(self):
        """Сохраняет изменения в БД"""
        try:
            updated_count = 0

            # Обрабатываем существующие строки
            for row in range(self.table.rowCount()):
                # Находим ID в оригинальных данных по ln_nmb
                item_nmb = self.table.item(row, 0)
                if not item_nmb:
                    continue

                current_nmb = item_nmb.text().strip()

                # Ищем ID в оригинальных данных
                row_id = None
                original = None
                for orig_id, orig_data in self.original_data.items():
                    if orig_data["ln_nmb"] == current_nmb:
                        row_id = orig_id
                        original = orig_data
                        break

                if not row_id or not original:
                    # Это новая строка, которую нужно вставить
                    # Пропускаем, так как вставка будет обработана отдельно
                    continue

                changes = []
                params = []

                # Проверяем все редактируемые поля
                fields = [
                    ("ln_name", 1), ("ln_en", 2), ("ln_desc", 3),
                    ("ln_nc", 4), ("ln_back", 5)
                ]

                for db_field, col in fields:
                    current_item = self.table.item(row, col)
                    if not current_item:
                        continue

                    new_value = current_item.text().strip()
                    old_value = original.get(db_field, "")

                    if new_value != old_value:
                        if new_value == "":
                            changes.append(f"{db_field} = NULL")
                        else:
                            changes.append(f"{db_field} = ?")
                            try:
                                # Пытаемся преобразовать в число
                                if '.' in new_value:
                                    num_val = float(new_value)
                                else:
                                    num_val = int(new_value)
                                params.append(num_val)
                            except ValueError:
                                # Если не удалось преобразовать, сохраняем как строку
                                params.append(new_value)

                if changes:
                    try:
                        query = f"UPDATE SET01 SET {', '.join(changes)} WHERE ID = ?"
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

            # После сохранения обновляем JSON
            self.export_to_json()

            if updated_count > 0:
                print(f"Сохранено: {updated_count} строк")
                QMessageBox.information(self, "Успех", f"Сохранено {updated_count} изменений")
            else:
                print("Изменений не было")
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения")

        except Exception as e:
            error_msg = f"Ошибка при сохранении данных: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def add_row(self):
        """Добавляет новую строку в таблицу и в БД"""
        try:
            # Запрашиваем номер новой линии
            nmb, ok = QInputDialog.getInt(self, "Добавить строку", "Введите номер линии:", 1, 1, 9999, 1)
            if not ok:
                return

            # Проверяем, не существует ли уже такая строка
            for row in range(self.table.rowCount()):
                item_nmb = self.table.item(row, 0)
                if item_nmb and int(item_nmb.text()) == nmb:
                    QMessageBox.warning(self, "Ошибка", f"Строка с номером {nmb} уже существует!")
                    return

            # Добавляем новую строку в БД
            try:
                query = f"""
                INSERT INTO SET01
                (ln_nmb, ln_name, ln_en, ln_desc, ln_nc, ln_back)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                self.db.execute(query, [nmb, "", 0.0, "", 0, 0])

                # После вставки перезагружаем данные, чтобы получить правильный ID
                self.load_data()

                QMessageBox.information(self, "Успех", f"Добавлена новая строка с номером {nmb}")

            except Exception as e:
                error_msg = f"Ошибка при добавлении строки в БД: {e}"
                print(error_msg)
                QMessageBox.critical(self, "Ошибка", error_msg)

        except Exception as e:
            error_msg = f"Ошибка при добавлении строки: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def delete_row(self):
        """Удаляет выделенную строку из таблицы и из БД"""
        try:
            selected_rows = self.table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.information(self, "Информация", "Пожалуйста, выберите строку для удаления")
                return

            # Получаем номер строки для удаления
            row = selected_rows[0].row()
            item_nmb = self.table.item(row, 0)
            if not item_nmb:
                return

            nmb_text = item_nmb.text()
            if not nmb_text.isdigit():
                QMessageBox.warning(self, "Ошибка", "Невозможно удалить строку: некорректный номер")
                return

            nmb = int(nmb_text)

            # Проверяем, существует ли эта строка в БД (в original_data)
            row_id_to_delete = None
            for orig_id, orig_data in self.original_data.items():
                if int(orig_data["ln_nmb"]) == nmb:
                    row_id_to_delete = orig_id
                    break

            if row_id_to_delete is None:
                # Строка новая, просто удаляем из таблицы
                self.table.removeRow(row)
                # Обновляем JSON
                self.export_to_json()
                QMessageBox.information(self, "Успех", f"Новая строка с номером {nmb} удалена из таблицы")
                return

            # Подтверждение удаления из БД
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                f"Вы уверены, что хотите удалить строку с номером {nmb} из базы данных?\nЭто действие необратимо!",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                try:
                    # Удаляем из БД
                    query = f"""
                    DELETE FROM SET01
                    WHERE id = ?
                    """
                    self.db.execute(query, [row_id_to_delete])

                    # Удаляем строку из таблицы
                    self.table.removeRow(row)

                    # Удаляем из original_data
                    if row_id_to_delete in self.original_data:
                        del self.original_data[row_id_to_delete]

                    # Обновляем JSON
                    self.export_to_json()

                    QMessageBox.information(self, "Успех", f"Строка с номером {nmb} удалена из базы данных")

                except Exception as e:
                    error_msg = f"Ошибка при удалении строки из БД: {e}"
                    print(error_msg)
                    QMessageBox.critical(self, "Ошибка", error_msg)

        except Exception as e:
            error_msg = f"Ошибка при удалении строки: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def export_to_json(self):
        """Экспортирует данные в JSON файл, включая специальную запись для -1"""
        try:
            lines_data = []
            for row in range(self.table.rowCount()):
                item_nmb = self.table.item(row, 0)
                item_name = self.table.item(row, 1)  # Столбец "Название"

                if item_nmb and item_name:
                    try:
                        number = int(item_nmb.text())
                        name = item_name.text()
                        lines_data.append({
                            "number": number,
                            "name": name
                        })
                    except ValueError:
                        # Пропускаем строки с некорректными номерами
                        continue

            # Сортируем по номеру
            lines_data.sort(key=lambda x: x["number"])

            # Добавляем специальную запись для ln_nmb = -1
            # Проверяем, нет ли уже такой записи, чтобы не дублировать
            if not any(item["number"] == -1 for item in lines_data):
                lines_data.insert(0, {"number": -1, "name": "-"})

            # Определяем путь к JSON файлу
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_dir = os.path.join(base_dir, "..", "..", "config")
            os.makedirs(config_dir, exist_ok=True)
            json_path = os.path.join(config_dir, "lines.json")

            # Записываем в файл
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(lines_data, f, ensure_ascii=False, indent=4)

            print(f"JSON файл линий успешно сохранён: {json_path}")

        except Exception as e:
            error_msg = f"Ошибка при экспорте линий в JSON: {e}"
            print(error_msg)

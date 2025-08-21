# views/measurement/background.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QMessageBox, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QBrush
from database.db import Database
from config import AC_COUNT


class BackgroundPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.table = None
        self.ac_selector = None
        self.current_ac_nmb = 1  # Текущий выбранный прибор
        # Словари для метаданных из SET01
        self.ln_nmb_to_name = {}
        self.ln_nmb_to_back = {}
        # Данные из SET03
        self.data_rows = []
        self.used_sq_nmbs = []
        # Для отслеживания изменений
        self.modified_data = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Матрица влияния спектральных линий")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Выбор прибора ---
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Прибор:"))

        self.ac_selector = QComboBox()
        for i in range(1, AC_COUNT + 1):
            self.ac_selector.addItem(f"Прибор {i}", i)
        self.ac_selector.currentIndexChanged.connect(self.on_ac_changed)
        selector_layout.addWidget(self.ac_selector)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_data)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_data()

    def on_ac_changed(self, index):
        """Обработчик изменения выбора прибора"""
        self.current_ac_nmb = self.ac_selector.currentData()
        self.load_data()

    def on_cell_changed(self, row, column):
        """Обработчик изменения ячейки"""
        if row >= 2:  # Игнорируем заголовки
            item = self.table.item(row, column)
            if item and item.text().strip():
                try:
                    value = float(item.text())
                    # Сохраняем изменение
                    self.modified_data[(row, column)] = value
                except ValueError:
                    pass

    def load_data(self):
        """Загружает и отображает данные о фоне и наложениях"""
        try:
            # Сбрасываем измененные данные
            self.modified_data.clear()

            # 1. Загружаем метаданные из SET01
            query_meta = f"SELECT [ln_nmb], [ln_name], [ln_back] FROM [{self.db.database_name}].[dbo].[SET01]"
            meta_rows = self.db.fetch_all(query_meta)
            self.ln_nmb_to_name = {row["ln_nmb"]: row["ln_name"] for row in meta_rows}
            self.ln_nmb_to_back = {row["ln_nmb"]: row["ln_back"] for row in meta_rows}

            # 2. Загружаем данные из SET03 для выбранного прибора
            query_data = f"""
            SELECT [sq_nmb], [ln_nmb], [k_nmb],
                [ln_01], [ln_02], [ln_03], [ln_04], [ln_05],
                [ln_06], [ln_07], [ln_08], [ln_09], [ln_10],
                [ln_11], [ln_12], [ln_13], [ln_14], [ln_15],
                [ln_16], [ln_17], [ln_18], [ln_19], [ln_20]
            FROM [{self.db.database_name}].[dbo].[SET03]
            WHERE [ac_nmb] = ? AND [ln_nmb] != -1
            ORDER BY [sq_nmb], [k_nmb]
            """
            self.data_rows = self.db.fetch_all(query_data, [self.current_ac_nmb])
            self.used_sq_nmbs = sorted(set(row['sq_nmb'] for row in self.data_rows))

            # 3. Фильтруем строки: оставляем только линии с ln_back = 0 (не фоновые)
            source_sq_nmbs_to_show = []
            for sq_nmb in self.used_sq_nmbs:
                ln_nmb = next(row["ln_nmb"] for row in self.data_rows
                            if row["sq_nmb"] == sq_nmb and row["k_nmb"] == 1)
                if self.ln_nmb_to_back.get(ln_nmb, 0) == 0:  # Показываем только не фоновые линии
                    source_sq_nmbs_to_show.append(sq_nmb)

            # 4. Создаем таблицу
            num_source_lines = len(source_sq_nmbs_to_show)
            num_target_lines = len(self.used_sq_nmbs)

            self.table.setRowCount(num_source_lines + 2)
            self.table.setColumnCount(num_target_lines * 2 + 1)

            # 5. Заполняем заголовки столбцов
            self.table.setItem(0, 0, QTableWidgetItem(""))
            self.table.setItem(1, 0, QTableWidgetItem(""))

            columns_to_hide = []

            for col, target_sq in enumerate(self.used_sq_nmbs):
                target_ln_nmb = next(row["ln_nmb"] for row in self.data_rows
                                   if row["sq_nmb"] == target_sq and row["k_nmb"] == 1)
                target_name = self.ln_nmb_to_name.get(target_ln_nmb, "Unknown")
                target_back = self.ln_nmb_to_back.get(target_ln_nmb, 0)

                col_index = col * 2 + 1
                self.table.setSpan(0, col_index, 1, 2)

                # Название целевой линии
                item = QTableWidgetItem(target_name)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QColor(220, 220, 220))
                item.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(0, col_index, item)

                # Подзаголовки K1 и K2
                item_k1 = QTableWidgetItem("K1")
                item_k1.setTextAlignment(Qt.AlignCenter)
                item_k1.setBackground(QColor(240, 240, 240))
                item_k1.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(1, col_index, item_k1)

                item_k2 = QTableWidgetItem("K2")
                item_k2.setTextAlignment(Qt.AlignCenter)
                item_k2.setBackground(QColor(240, 240, 240))
                item_k2.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(1, col_index + 1, item_k2)

                if target_back == 0:
                    columns_to_hide.append(col_index)

            # 6. Заполняем названия строк и данные
            for row, source_sq in enumerate(source_sq_nmbs_to_show):
                source_ln_nmb = next(row["ln_nmb"] for row in self.data_rows
                                   if row["sq_nmb"] == source_sq and row["k_nmb"] == 1)
                source_name = self.ln_nmb_to_name.get(source_ln_nmb, "Unknown")

                table_row = row + 2

                # Название строки - расширяем столбец
                item = QTableWidgetItem(source_name)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QColor(220, 220, 220))
                item.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(table_row, 0, item)

                # Данные влияния
                for col, target_sq in enumerate(self.used_sq_nmbs):
                    k1_row = next((r for r in self.data_rows
                                 if r["sq_nmb"] == source_sq and r["k_nmb"] == 1), None)
                    k2_row = next((r for r in self.data_rows
                                 if r["sq_nmb"] == source_sq and r["k_nmb"] == 2), None)

                    col_index = col * 2 + 1

                    if k1_row and k2_row:
                        coeff_index = target_sq
                        k1_val = k1_row.get(f"ln_{coeff_index:02d}", 0) or 0
                        k2_val = k2_row.get(f"ln_{coeff_index:02d}", 0) or 0

                        # Коэффициент K1 (2 знака после точки)
                        item_k1 = QTableWidgetItem(f"{k1_val:.2f}")
                        item_k1.setTextAlignment(Qt.AlignCenter)

                        # Коэффициент K2 (2 знака после точки)
                        item_k2 = QTableWidgetItem(f"{k2_val:.2f}")
                        item_k2.setTextAlignment(Qt.AlignCenter)

                        # Подсветка синим если оба коэффициента не нулевые
                        if k1_val != 0 and k2_val != 0:
                            item_k1.setBackground(QColor(200, 220, 255))
                            item_k2.setBackground(QColor(200, 220, 255))

                        # Зачеркиваем нули
                        if k1_val == 0:
                            font = item_k1.font()
                            font.setStrikeOut(True)
                            item_k1.setFont(font)
                            item_k1.setForeground(QBrush(QColor(150, 150, 150)))

                        if k2_val == 0:
                            font = item_k2.font()
                            font.setStrikeOut(True)
                            item_k2.setFont(font)
                            item_k2.setForeground(QBrush(QColor(150, 150, 150)))

                        if source_sq == target_sq:
                            # Диагональ - объединяем и показываем прочерк
                            self.table.setSpan(table_row, col_index, 1, 2)
                            merged_item = QTableWidgetItem("—")
                            merged_item.setTextAlignment(Qt.AlignCenter)
                            merged_item.setBackground(QColor(200, 200, 200))
                            merged_item.setFlags(Qt.ItemIsEnabled)
                            self.table.setItem(table_row, col_index, merged_item)
                        else:
                            self.table.setItem(table_row, col_index, item_k1)
                            self.table.setItem(table_row, col_index + 1, item_k2)

            # 7. Скрываем столбцы K1 для не фоновых линий
            for col_index in columns_to_hide:
                self.table.setColumnHidden(col_index, True)

            # 8. Настраиваем внешний вид
            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
            # Устанавливаем ширину всех столбцов в 80 пикселей
            for col in range(self.table.columnCount()):
                self.table.setColumnWidth(col, 80)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке данных: {str(e)}")

    def save_data(self):
        """Сохраняет изменения в базу данных"""
        try:
            if not self.modified_data:
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения")
                return

            changes_by_cell = {}

            for (row, col), new_value in self.modified_data.items():
                if row < 2 or col < 1:
                    continue

                source_line_idx = row - 2
                target_col_idx = (col - 1) // 2

                non_background_lines = []
                for sq_nmb in self.used_sq_nmbs:
                    ln_nmb = next((r["ln_nmb"] for r in self.data_rows
                                 if r["sq_nmb"] == sq_nmb and r["k_nmb"] == 1), None)
                    if ln_nmb is not None and self.ln_nmb_to_back.get(ln_nmb, 0) == 0:
                        non_background_lines.append(sq_nmb)

                if source_line_idx < len(non_background_lines) and target_col_idx < len(self.used_sq_nmbs):
                    source_sq = non_background_lines[source_line_idx]
                    target_sq = self.used_sq_nmbs[target_col_idx]

                    is_k1_column = (col - 1) % 2 == 0
                    k_nmb = 1 if is_k1_column else 2

                    target_ln_nmb = next((r["ln_nmb"] for r in self.data_rows
                                        if r["sq_nmb"] == target_sq and r["k_nmb"] == 1), None)
                    target_back = self.ln_nmb_to_back.get(target_ln_nmb, 0)

                    if k_nmb == 1 and target_back == 0:
                        continue

                    key = (source_sq, k_nmb)
                    if key not in changes_by_cell:
                        changes_by_cell[key] = {}

                    changes_by_cell[key][target_sq] = new_value

            if not changes_by_cell:
                QMessageBox.information(self, "Информация", "Нет изменений для сохранения")
                return

            updated_count = 0

            with self.db.connect() as conn:
                cursor = conn.cursor()

                try:
                    cursor.execute("BEGIN TRANSACTION")

                    for (source_sq, k_nmb), column_changes in changes_by_cell.items():
                        for target_sq, new_value in column_changes.items():
                            db_column = f"ln_{target_sq:02d}"

                            query = f"""
                            UPDATE [{self.db.database_name}].[dbo].[SET03]
                            SET [{db_column}] = ?
                            WHERE [ac_nmb] = ?
                                AND [sq_nmb] = ?
                                AND [k_nmb] = ?
                            """

                            cursor.execute(query, (new_value, self.current_ac_nmb, source_sq, k_nmb))
                            updated_count += 1

                    cursor.execute("COMMIT")
                    conn.commit()

                    self.modified_data.clear()
                    QMessageBox.information(self, "Успех", f"Успешно сохранено {updated_count} изменений")
                    self.load_data()

                except Exception as e:
                    cursor.execute("ROLLBACK")
                    raise e

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")

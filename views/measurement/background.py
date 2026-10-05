# views/measurement/background.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QMessageBox, QHeaderView, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QBrush
from database.db import Database


class BackgroundPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.table = None
        self.ac_selector = None
        self.current_ac_nmb = None
        self.ln_nmb_to_name = {}
        self.ln_nmb_to_back = {}
        self.data_rows = []
        self.used_sq_nmbs = []
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

        reset_btn = QPushButton("Сбросить коэффициенты")
        reset_btn.setStyleSheet("background-color: #ffcdd2;")
        reset_btn.clicked.connect(self.reset_coefficients)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(reset_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.table = QTableWidget()
        self.table.setEditTriggers(QTableWidget.DoubleClicked)
        self.table.cellChanged.connect(self.on_cell_changed)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        self.setLayout(layout)
        self.load_analyzers()

    def load_analyzers(self):
        try:
            self.ac_selector.blockSignals(True)
            self.ac_selector.clear()

            query = "SELECT ac_nmb, ac_name FROM cfg00 ORDER BY ac_nmb"
            analyzers = self.db.fetch_all(query)

            for ac in analyzers:
                name = ac['ac_name'] or ""
                display_text = f"№{ac['ac_nmb']} - {name}" if name else f"Прибор №{ac['ac_nmb']}"
                self.ac_selector.addItem(display_text, ac['ac_nmb'])

            if self.ac_selector.count() > 0:
                self.ac_selector.setCurrentIndex(0)
                self.current_ac_nmb = self.ac_selector.currentData()

            self.ac_selector.blockSignals(False)

            if self.current_ac_nmb is not None:
                self.load_data()
        except Exception as e:
            print(f"Ошибка загрузки списка приборов: {e}")

    def on_ac_changed(self, index):
        if index >= 0:
            self.current_ac_nmb = self.ac_selector.currentData()
            self.load_data()

    def on_cell_changed(self, row, column):
        if row >= 2:
            item = self.table.item(row, column)
            if item:
                text = item.text().strip()
                try:
                    # Определяем, колонка K1 это или K2
                    is_k1_column = (column - 1) % 2 == 0
                    default_val = 0.0 if is_k1_column else 1.0

                    # Если пользователь стер значение, подставляем дефолтное
                    value = float(text.replace(',', '.')) if text else default_val
                    self.modified_data[(row, column)] = value
                except ValueError:
                    pass

    def load_data(self):
        if self.current_ac_nmb is None:
            return

        try:
            self.modified_data.clear()

            query_meta = f'SELECT ln_nmb, ln_name, ln_back FROM SET01'
            meta_rows = self.db.fetch_all(query_meta)
            self.ln_nmb_to_name = {row["ln_nmb"]: row["ln_name"] for row in meta_rows}
            self.ln_nmb_to_back = {row["ln_nmb"]: row["ln_back"] for row in meta_rows}

            query_data = f"""
            SELECT sq_nmb, ln_nmb, k_nmb,
                ln_01, ln_02, ln_03, ln_04, ln_05,
                ln_06, ln_07, ln_08, ln_09, ln_10,
                ln_11, ln_12, ln_13, ln_14, ln_15,
                ln_16, ln_17, ln_18, ln_19, ln_20
            FROM SET03
            WHERE ac_nmb = ? AND ln_nmb != -1
            ORDER BY sq_nmb, k_nmb
            """
            self.data_rows = self.db.fetch_all(query_data, [self.current_ac_nmb])
            self.used_sq_nmbs = sorted(set(row['sq_nmb'] for row in self.data_rows))

            source_sq_nmbs_to_show = []
            for sq_nmb in self.used_sq_nmbs:
                ln_nmb = next(row["ln_nmb"] for row in self.data_rows
                              if row["sq_nmb"] == sq_nmb and row["k_nmb"] == 1)
                if self.ln_nmb_to_back.get(ln_nmb, 0) == 0:
                    source_sq_nmbs_to_show.append(sq_nmb)

            num_source_lines = len(source_sq_nmbs_to_show)
            num_target_lines = len(self.used_sq_nmbs)

            self.table.setRowCount(num_source_lines + 2)
            self.table.setColumnCount(num_target_lines * 2 + 1)

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

                item = QTableWidgetItem(target_name)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QColor(220, 220, 220))
                item.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(0, col_index, item)

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

            for row, source_sq in enumerate(source_sq_nmbs_to_show):
                source_ln_nmb = next(row["ln_nmb"] for row in self.data_rows
                                     if row["sq_nmb"] == source_sq and row["k_nmb"] == 1)
                source_name = self.ln_nmb_to_name.get(source_ln_nmb, "Unknown")

                table_row = row + 2

                item = QTableWidgetItem(source_name)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QColor(220, 220, 220))
                item.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(table_row, 0, item)

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

                        item_k1 = QTableWidgetItem(f"{k1_val:.2f}")
                        item_k1.setTextAlignment(Qt.AlignCenter)

                        item_k2 = QTableWidgetItem(f"{k2_val:.2f}")
                        item_k2.setTextAlignment(Qt.AlignCenter)

                        # Подсветка синим, если есть реальное влияние (k1 != 0 ИЛИ k2 != 1)
                        if k1_val != 0 or k2_val != 1.0:
                            item_k1.setBackground(QColor(200, 220, 255))
                            item_k2.setBackground(QColor(200, 220, 255))

                        # Зачеркиваем нули для K1
                        if k1_val == 0:
                            font = item_k1.font()
                            font.setStrikeOut(True)
                            item_k1.setFont(font)
                            item_k1.setForeground(QBrush(QColor(150, 150, 150)))

                        # Зачеркиваем единицы для K2
                        if k2_val == 1.0:
                            font = item_k2.font()
                            font.setStrikeOut(True)
                            item_k2.setFont(font)
                            item_k2.setForeground(QBrush(QColor(150, 150, 150)))

                        if source_sq == target_sq:
                            self.table.setSpan(table_row, col_index, 1, 2)
                            merged_item = QTableWidgetItem("—")
                            merged_item.setTextAlignment(Qt.AlignCenter)
                            merged_item.setBackground(QColor(200, 200, 200))
                            merged_item.setFlags(Qt.ItemIsEnabled)
                            self.table.setItem(table_row, col_index, merged_item)
                        else:
                            self.table.setItem(table_row, col_index, item_k1)
                            self.table.setItem(table_row, col_index + 1, item_k2)

            for col_index in columns_to_hide:
                self.table.setColumnHidden(col_index, True)

            self.table.resizeColumnsToContents()
            self.table.resizeRowsToContents()
            for col in range(self.table.columnCount()):
                self.table.setColumnWidth(col, 80)

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке данных: {str(e)}")

    def save_data(self):
        try:
            if not self.modified_data:
                QMessageBox.information(self, "Информация", "Нет валидных изменений для сохранения")
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

            with self.db.transaction() as cur:
                for (source_sq, k_nmb), column_changes in changes_by_cell.items():
                    for target_sq, new_value in column_changes.items():
                        db_column = f"ln_{target_sq:02d}"
                        query = f"UPDATE SET03 SET {db_column} = ? WHERE ac_nmb = ? AND sq_nmb = ? AND k_nmb = ?"

                        cur.execute(query, (float(new_value), self.current_ac_nmb, source_sq, k_nmb))
                        updated_count += 1

            self.modified_data.clear()
            QMessageBox.information(self, "Успех", f"Успешно сохранено {updated_count} изменений")
            self.load_data()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении: {str(e)}")

    def reset_coefficients(self):
        if self.current_ac_nmb is None:
            return

        reply = QMessageBox.question(
            self, 'Внимание!',
            f"Вы уверены, что хотите сбросить ВСЕ коэффициенты влияния для прибора №{self.current_ac_nmb}?\n(K1 станут 0.0, K2 станут 0.0)\nЭто действие необратимо и сразу применится к базе данных!",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # K1 сбрасываем в 0.0
                set_clauses_k1 = ", ".join([f"ln_{i:02d} = 0.0" for i in range(1, 21)])
                query_k1 = f"UPDATE SET03 SET {set_clauses_k1} WHERE ac_nmb = ? AND k_nmb = 1"

                # K2 сбрасываем в 1.0
                set_clauses_k2 = ", ".join([f"ln_{i:02d} = 0.0" for i in range(1, 21)])
                query_k2 = f"UPDATE SET03 SET {set_clauses_k2} WHERE ac_nmb = ? AND k_nmb = 2"

                with self.db.transaction() as cur:
                    cur.execute(query_k1, (self.current_ac_nmb,))
                    cur.execute(query_k2, (self.current_ac_nmb,))

                QMessageBox.information(self, "Успех", "Коэффициенты успешно сброшены к базовым значениям!")
                self.load_data()
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при сбросе коэффициентов: {str(e)}")
# views/measurement/background.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from database.db import Database


class BackgroundPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.table = None
        self.meta_rows = []  # Сохраним для использования в save_data
        self.ordered_ln_nmbs = []  # Сохраним для использования в save_data
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        title = QLabel("Фон и наложения (SET03)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Таблица: без лейблов, заголовки в самой таблице + данные
        self.table = QTableWidget()
        self.table.setRowCount(21) # имя + данные 20строк
        self.table.setColumnCount(41) # имя + данные 40 строк
        self.table.setHorizontalHeaderLabels([""] * 41)
        self.table.setVerticalHeaderLabels([""] * 21)
        # Отключаем стандартные границы, будем рисовать вручную при необходимости
        self.table.setGridStyle(Qt.NoPen)

        # Настройка ширины столбцов и высоты строк
        for col in range(41):
            # Ширина для столбцов с данными
            self.table.setColumnWidth(col, 60)
        for row in range(21):
            self.table.setRowHeight(row, 30)

        layout.addWidget(self.table)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_data)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)
        # Загружаем данные при инициализации
        self.load_data()

    def load_data(self):
        """Загружает SET03 и LN_SET01 и строит таблицу"""
        try:
            # === 1. Загружаем метаданные LN_SET01 ===
            query_meta = """
            SELECT [id], [ln_name], [ln_back]
            FROM [AMMKASAKDB01].[dbo].[LN_SET01]
            WHERE [ak_nmb] = 1 AND [ID] > 1
            ORDER BY [ID]
            """
            self.meta_rows = self.db.fetch_all(query_meta)
            n_lines = len(self.meta_rows)
            if n_lines == 0:
                print("Нет данных в LN_SET01")
                return

            # === 2. Загружаем коэффициенты SET03 ===
            query_coeffs = """
            SELECT [ln_nmb], [k_nmb],
                   [ln_01], [ln_02], [ln_03], [ln_04], [ln_05],
                   [ln_06], [ln_07], [ln_08], [ln_09], [ln_10],
                   [ln_11], [ln_12], [ln_13], [ln_14], [ln_15],
                   [ln_16], [ln_17], [ln_18], [ln_19], [ln_20]
            FROM [AMMKASAKDB01].[dbo].[SET03]
            WHERE [ak_nmb] = 1
            ORDER BY [ln_nmb], [k_nmb]
            """
            coeff_rows = self.db.fetch_all(query_coeffs)
            if len(coeff_rows) == 0:
                print("Нет данных в SET03")
                return

            # === 3. Заполняем заголовки ===
            # Заголовки сверху: ln_name
            for i, meta_row in enumerate(self.meta_rows):
                col_pos = i * 2 + 1 # Позиция в таблице для этой линии

                # Имя линии (ln_name)
                item_name = QTableWidgetItem(meta_row["ln_name"])
                item_name.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(0, col_pos, item_name) # Строка 0
                # Объединяем ячейки для имени, так как оно охватывает обе колонки
                self.table.setSpan(0, col_pos, 1, 2)

            # Заголовки слева: ln_name
            for i, meta_row in enumerate(self.meta_rows):
                row_pos = i + 1 # Позиция в таблице для этой линии
                item_name = QTableWidgetItem(meta_row["ln_name"])
                item_name.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row_pos, 0, item_name) # Столбец 0

            # === 4. Заполняем данные ===
            # Создаем словарь для быстрого поиска коэффициентов по (ln_nmb, k_nmb)
            coeffs_dict = {}
            for row in coeff_rows:
                key = (row["ln_nmb"], row["k_nmb"])
                coeffs_dict[key] = row

            # Получаем упорядоченный список ln_nmb из coeff_rows (по возрастанию ln_nmb)
            self.ordered_ln_nmbs = sorted(list(set(row["ln_nmb"] for row in coeff_rows)))

            # Проходим по каждой строке метаданных (исходная линия) - это строки нашей таблицы
            for row_index, src_meta in enumerate(self.meta_rows):
                # Используем порядковый номер строки вместо ln_nmb из meta
                if row_index < len(self.ordered_ln_nmbs):
                    src_ln_nmb = self.ordered_ln_nmbs[row_index]
                else:
                    continue

                table_row = row_index + 1  # +1 потому что первая строка - заголовки

                # Для каждой исходной линии берем k_nmb=1 и k_nmb=2
                for k_nmb in [1, 2]:
                    coeff_key = (src_ln_nmb, k_nmb)
                    if coeff_key not in coeffs_dict:
                        continue

                    coeff_data = coeffs_dict[coeff_key]

                    # Проходим по каждой целевой линии (столбец) в порядке из meta_rows
                    for col_index, dst_meta in enumerate(self.meta_rows):
                        # Используем порядковый номер столбца вместо ln_nmb из meta
                        if col_index < len(self.ordered_ln_nmbs):
                            dst_ln_nmb = self.ordered_ln_nmbs[col_index]
                        else:
                            continue

                        # Формируем ключ для коэффициента (например, 'ln_01')
                        coeff_field = f"ln_{dst_ln_nmb:02d}"
                        value = coeff_data.get(coeff_field)

                        if value is not None:
                            # Позиция столбца в таблице (2 столбца на линию)
                            # col_index * 2 + 1 - начальная позиция для пары столбцов этой линии
                            table_col_start = col_index * 2 + 1

                            # Для k_nmb=1 используем первый столбец пары (table_col_start)
                            # Для k_nmb=2 используем второй столбец пары (table_col_start + 1)
                            table_col = table_col_start + (k_nmb - 1)

                            item = QTableWidgetItem(str(value))
                            item.setTextAlignment(Qt.AlignCenter)
                            self.table.setItem(table_row, table_col, item)

            # === 5. Применяем форматирование ===
            # Скрываем строки с ln_back = 1
            for i, meta_row in enumerate(self.meta_rows):
                if meta_row["ln_back"] == 1:
                    # Скрываем строку (i + 1, потому что первая строка - заголовки)
                    self.table.setRowHidden(i + 1, True)

            # Скрываем столбцы k_nmb = 1 (нечетные) где ln_back = 0
            for i, meta_row in enumerate(self.meta_rows):
                if meta_row["ln_back"] == 0:
                    # Скрываем столбец k_nmb = 1 (первый в паре)
                    table_col = i * 2 + 1  # Позиция первого столбца пары
                    self.table.setColumnHidden(table_col, True)

            # Покраска столбцов с ln_back = 1 в синий и добавление сетки
            for i, meta_row in enumerate(self.meta_rows):
                table_col_start = i * 2 + 1  # Позиция первого столбца пары

                if meta_row["ln_back"] == 1:
                    # Подсвечиваем оба столбца пары синим цветом
                    for col_offset in [0, 1]:  # 0 для k_nmb=1, 1 для k_nmb=2
                        table_col = table_col_start + col_offset
                        for row in range(1, len(self.meta_rows) + 1):  # От 1 до количества строк с данными
                            item = self.table.item(row, table_col)
                            if not item:
                                item = QTableWidgetItem("")
                                item.setTextAlignment(Qt.AlignCenter)
                                self.table.setItem(row, table_col, item)
                            # Цвет RGB(195, 225, 249) из VBA кода
                            item.setBackground(QColor(195, 225, 249))

                            # Добавляем границы (сетку) для каждой ячейки
                            item.setFlags(item.flags() | Qt.ItemIsEditable)
                else:
                    # Для ln_back = 0 добавляем только сетку
                    table_col = table_col_start + 1  # Только столбец k_nmb=2
                    for row in range(1, len(self.meta_rows) + 1):
                        item = self.table.item(row, table_col)
                        if not item:
                            item = QTableWidgetItem("")
                            item.setTextAlignment(Qt.AlignCenter)
                            self.table.setItem(row, table_col, item)
                        # Добавляем границы (сетку) для каждой ячейки
                        item.setFlags(item.flags() | Qt.ItemIsEditable)

            # Покраска диагональных ячеек в серый
            for i in range(len(self.meta_rows)):
                row = i + 1
                col = i * 2 + 1
                # Объединяем две ячейки для диагонали
                self.table.setSpan(row, col, 1, 2)
                # Устанавливаем серый фон
                item = self.table.item(row, col)
                if not item:
                    item = QTableWidgetItem("")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(row, col, item)
                # Цвет RGB(207, 207, 207) из VBA кода
                item.setBackground(QColor(207, 207, 207))

                # Добавляем границы (сетку) для диагональной ячейки
                item.setFlags(item.flags() | Qt.ItemIsEditable)

        except Exception as e:
            print(f"Ошибка при построении таблицы 'Фон и наложения': {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при загрузке данных: {e}")

    def save_data(self):
        """Сохраняет измененные данные обратно в SET03"""
        try:
            updated_count = 0
            errors = []

            # Проходим по каждой строке метаданных (исходная линия)
            for row_index, src_meta in enumerate(self.meta_rows):
                if row_index < len(self.ordered_ln_nmbs):
                    src_ln_nmb = self.ordered_ln_nmbs[row_index]
                else:
                    continue

                table_row = row_index + 1

                # Проверяем, не скрыта ли строка
                if self.table.isRowHidden(table_row):
                    continue

                # Для каждой исходной линии берем k_nmb=1 и k_nmb=2
                for k_nmb in [1, 2]:
                    # Проходим по каждой целевой линии (столбец)
                    for col_index, dst_meta in enumerate(self.meta_rows):
                        if col_index < len(self.ordered_ln_nmbs):
                            dst_ln_nmb = self.ordered_ln_nmbs[col_index]
                        else:
                            continue

                        # Позиция столбца в таблице
                        table_col_start = col_index * 2 + 1
                        table_col = table_col_start + (k_nmb - 1)

                        # Проверяем, не скрыт ли столбец
                        if self.table.isColumnHidden(table_col):
                            continue

                        # Получаем значение из ячейки
                        item = self.table.item(table_row, table_col)
                        if not item:
                            continue

                        new_value_text = item.text().strip()

                        # Пропускаем пустые значения или диагональные ячейки (они должны быть пустыми)
                        if not new_value_text or (row_index == col_index):
                            continue

                        try:
                            # Преобразуем текст в число
                            new_value = float(new_value_text)

                            # Формируем имя поля в таблице SET03
                            field_name = f"ln_{dst_ln_nmb:02d}"

                            # Формируем SQL-запрос на обновление
                            query = f"""
                            UPDATE [AMMKASAKDB01].[dbo].[SET03]
                            SET [{field_name}] = ?
                            WHERE [ln_nmb] = ? AND [k_nmb] = ? AND [ak_nmb] = 1
                            """

                            # Выполняем запрос
                            self.db.execute(query, [new_value, src_ln_nmb, k_nmb])
                            updated_count += 1

                        except ValueError:
                            # Если не удалось преобразовать в число, пропускаем
                            errors.append(f"Некорректное значение в строке {row_index+1}, столбце {col_index+1}: '{new_value_text}'")
                        except Exception as e:
                            errors.append(f"Ошибка при обновлении ln_nmb={src_ln_nmb}, k_nmb={k_nmb}, поле={field_name}: {e}")

            # Показываем результат
            if errors:
                error_msg = "\n".join(errors[:5])  # Показываем только первые 5 ошибок
                if len(errors) > 5:
                    error_msg += f"\n... и еще {len(errors) - 5} ошибок"
                QMessageBox.warning(self, "Ошибки при сохранении", error_msg)

            if updated_count > 0:
                QMessageBox.information(self, "Сохранение", f"Успешно обновлено {updated_count} записей.")
            elif not errors:
                QMessageBox.information(self, "Сохранение", "Нет изменений для сохранения.")

        except Exception as e:
            print(f"Ошибка при сохранении данных 'Фон и наложения': {e}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении данных: {e}")

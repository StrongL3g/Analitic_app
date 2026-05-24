from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QLineEdit, QLabel,
                               QPushButton, QMessageBox)
from PySide6.QtCore import Qt
from database.db import Database
from config import refresh_app_settings


class CfgacPage(QWidget):
    """Страница справочника приборов (Таблица cfg00)"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # 1. Поле поиска
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Поиск (№ или название):"))
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Введите номер или название")
        self.filter_edit.setFixedWidth(250)
        self.filter_edit.textChanged.connect(self.apply_filter)
        search_layout.addWidget(self.filter_edit)
        search_layout.addStretch()
        layout.addLayout(search_layout)

        # 2. Ряд кнопок
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.clicked.connect(self.save_data)
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.add_row)
        self.del_btn = QPushButton("Удалить")
        self.del_btn.clicked.connect(self.delete_row)

        for btn in (self.save_btn, self.add_btn, self.del_btn):
            btn.setFixedWidth(120)
            btn_layout.addWidget(btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 3. Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["№ (ac_nmb)", "Название", "Описание", "№ измерения"])

        # Настройка ширины колонок
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

    def clone_settings_from_template(self, new_ac_nmb):
        """
        Универсально клонирует все настройки из прибора №1 для нового прибора.
        Автоматически подстраивается под любые колонки в таблицах.
        """
        # Таблицы, зависящие от прибора (ac_nmb)
        tables_to_clone = ['set04', 'set02', 'set03', 'set06', 'cfg01']

        for table in tables_to_clone:
            rows = self.db.fetch_all(f"SELECT * FROM {table} WHERE ac_nmb = 1")

            for row in rows:
                if 'id' in row:
                    del row['id']

                # Подменяем номер прибора на новый
                row['ac_nmb'] = new_ac_nmb

                columns = list(row.keys())
                # Экранируем названия колонок для MSSQL
                escaped_columns = [f"[{col}]" for col in columns]
                placeholders = ", ".join(["?"] * len(columns))

                query = f"INSERT INTO {table} ({', '.join(escaped_columns)}) VALUES ({placeholders})"
                self.db.execute(query, list(row.values()))

    def load_data(self):
        self.table.setRowCount(0)
        try:
            query = "SELECT ac_nmb, ac_name, ac_desc, meas_nmb FROM cfg00 ORDER BY ac_nmb"
            rows = self.db.fetch_all(query)
            if not rows: return

            self.table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                # ID (Только для чтения)
                it_nmb = QTableWidgetItem(str(row['ac_nmb']))
                it_nmb.setFlags(it_nmb.flags() & ~Qt.ItemIsEditable)
                it_nmb.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(i, 0, it_nmb)

                # Название
                self.table.setItem(i, 1, QTableWidgetItem(str(row['ac_name'] if row['ac_name'] else "")))
                # Описание
                self.table.setItem(i, 2, QTableWidgetItem(str(row['ac_desc'] if row['ac_desc'] else "")))
                # Номер измерения
                self.table.setItem(i, 3, QTableWidgetItem(str(row['meas_nmb'] if row['meas_nmb'] else "1")))

        except Exception as e:
            print(f"Ошибка загрузки cfg00: {e}")

    def apply_filter(self, text):
        text = text.lower()
        for i in range(self.table.rowCount()):
            item_id = self.table.item(i, 0)
            item_name = self.table.item(i, 1)

            match_id = text in item_id.text().lower() if item_id else False
            match_name = text in item_name.text().lower() if item_name else False

            self.table.setRowHidden(i, not (match_id or match_name))

    def save_data(self):
        try:
            for i in range(self.table.rowCount()):
                ac_nmb = int(self.table.item(i, 0).text())
                ac_name = self.table.item(i, 1).text().strip()
                ac_desc = self.table.item(i, 2).text().strip()

                # Обработка пустого ввода для номера измерения
                meas_text = self.table.item(i, 3).text().strip()
                new_meas_nmb = int(meas_text) if meas_text.isdigit() else 1

                # 1. Обновляем основные данные прибора в cfg00
                query = "UPDATE cfg00 SET ac_name = ?, ac_desc = ?, meas_nmb = ? WHERE ac_nmb = ?"
                self.db.execute(query, (ac_name, ac_desc, new_meas_nmb, ac_nmb))

                # 2. СИНХРОНИЗАЦИЯ ТАБЛИЦЫ ИЗМЕРЕНИЙ (cfg01)
                # Если количество уменьшилось, удаляем лишние строки, превышающие новый лимит
                self.db.execute("DELETE FROM cfg01 WHERE ac_nmb = ? AND meas_nmb > ?", (ac_nmb, new_meas_nmb))

                # Проверяем текущее максимальное измерение в базе для этого прибора
                res = self.db.fetch_one("SELECT MAX(meas_nmb) as max_meas FROM cfg01 WHERE ac_nmb = ?", (ac_nmb,))
                current_max = res['max_meas'] if res and res['max_meas'] is not None else 0

                # Если количество увеличилось, генерируем недостающие строки на базе дефолтных значений
                if new_meas_nmb > current_max:
                    for meas_idx in range(current_max + 1, new_meas_nmb + 1):
                        # Чередуем кюветы: нечетные - 1, четные - 2
                        cuv_nmb = 1 if meas_idx % 2 != 0 else 2

                        insert_query = """
                        INSERT INTO cfg01 (meas_nmb, cuv_nmb, pr_nmb, sp_nmb, ac_nmb) 
                        VALUES (?, ?, ?, ?, ?)
                        """
                        # В качестве продукта и пробоотборника ставим шаблонные значения (1)
                        self.db.execute(insert_query, (meas_idx, cuv_nmb, 1, 1, ac_nmb))

            QMessageBox.information(self, "Успех", "Данные приборов и циклограммы измерений успешно синхронизированы!")
            refresh_app_settings()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить: {e}")

    def add_row(self):
        """Добавление нового прибора с автогенерацией всех настроек из шаблона №1"""
        try:
            # Ищем максимальный номер
            query = "SELECT MAX(ac_nmb) as max_id FROM cfg00"
            res = self.db.fetch_one(query)
            new_id = (res['max_id'] or 0) + 1

            # Узнаем, сколько измерений у прибора-шаблона, чтобы записать правильную цифру
            template_ac = self.db.fetch_one("SELECT meas_nmb FROM cfg00 WHERE ac_nmb = 1")
            template_meas_nmb = template_ac['meas_nmb'] if template_ac else 1

            # Добавляем прибор
            self.db.execute("INSERT INTO cfg00 (ac_nmb, ac_name, ac_desc, meas_nmb) VALUES (?, ?, ?, ?)",
                            (new_id, f"Прибор {new_id}", "Клон прибора №1", template_meas_nmb))

            # Запускаем клонирование зависимостей
            self.clone_settings_from_template(new_id)

            self.load_data()
            refresh_app_settings()
            self.table.scrollToBottom()

            QMessageBox.information(self, "Успех", f"Прибор №{new_id} и все его настройки успешно созданы!")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить прибор: {e}")

    def delete_row(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Внимание", "Выберите строку для удаления!")
            return

        ac_nmb = self.table.item(row, 0).text()

        # --- ЗАЩИТА ШАБЛОНА ---
        if str(ac_nmb) == "1":
            QMessageBox.warning(self, "Запрет", "Прибор №1 является системным шаблоном. Его нельзя удалить!")
            return
        # ----------------------

        reply = QMessageBox.question(self, 'Подтверждение', f"Удалить прибор №{ac_nmb} и все связанные с ним данные?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            try:
                # 1. Сначала удаляем все зависимые записи по внешнему ключу ac_nmb
                self.db.execute("DELETE FROM cfg01 WHERE ac_nmb = ?", (ac_nmb,))
                self.db.execute("DELETE FROM set06 WHERE ac_nmb = ?", (ac_nmb,))
                self.db.execute("DELETE FROM set03 WHERE ac_nmb = ?", (ac_nmb,))
                self.db.execute("DELETE FROM set02 WHERE ac_nmb = ?", (ac_nmb,))
                self.db.execute("DELETE FROM set04 WHERE ac_nmb = ?", (ac_nmb,))

                # 2. Теперь безопасно удаляем сам прибор
                self.db.execute("DELETE FROM cfg00 WHERE ac_nmb = ?", (ac_nmb,))

                self.load_data()
                refresh_app_settings()
                QMessageBox.information(self, "Успех", f"Прибор №{ac_nmb} успешно удален.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить: {e}")
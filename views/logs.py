# views/logs.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QComboBox, QDateTimeEdit, QPushButton,
    QHeaderView, QMessageBox, QSpinBox, QInputDialog
)
from PySide6.QtCore import Qt, QDateTime

from database.audit import get_audit


class LogsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.audit = get_audit()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Журнал изменений")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Информационная строка: размер файла и число записей ---
        info_layout = QHBoxLayout()
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #555; font-size: 12px;")
        info_layout.addWidget(self.info_label)
        info_layout.addStretch()

        self.purge_btn = QPushButton("Очистить старые...")
        self.purge_btn.setFixedWidth(160)
        self.purge_btn.clicked.connect(self.purge_old)
        info_layout.addWidget(self.purge_btn)

        self.clear_btn = QPushButton("Очистить всё...")
        self.clear_btn.setFixedWidth(140)
        self.clear_btn.setStyleSheet("background-color: #fee2e2;")
        self.clear_btn.clicked.connect(self.purge_all)
        info_layout.addWidget(self.clear_btn)

        layout.addLayout(info_layout)

        # --- Фильтры ---
        filters = QHBoxLayout()

        filters.addWidget(QLabel("Пользователь:"))
        self.cb_user = QComboBox()
        self.cb_user.addItem("Все", None)
        self.cb_user.setFixedWidth(150)
        filters.addWidget(self.cb_user)

        filters.addWidget(QLabel("Операция:"))
        self.cb_op = QComboBox()
        self.cb_op.addItem("Все", None)
        for op in ("INSERT", "UPDATE", "DELETE"):
            self.cb_op.addItem(op, op)
        self.cb_op.setFixedWidth(120)
        filters.addWidget(self.cb_op)

        filters.addWidget(QLabel("Таблица:"))
        self.cb_table = QComboBox()
        self.cb_table.addItem("Все", None)
        self.cb_table.setFixedWidth(150)
        filters.addWidget(self.cb_table)

        filters.addWidget(QLabel("От:"))
        self.dt_from = QDateTimeEdit()
        self.dt_from.setCalendarPopup(True)
        self.dt_from.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.dt_from.setDateTime(QDateTime.currentDateTime().addDays(-7))
        filters.addWidget(self.dt_from)

        filters.addWidget(QLabel("До:"))
        self.dt_to = QDateTimeEdit()
        self.dt_to.setCalendarPopup(True)
        self.dt_to.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.dt_to.setDateTime(QDateTime.currentDateTime().addDays(1))
        filters.addWidget(self.dt_to)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_data)
        filters.addWidget(refresh_btn)

        filters.addStretch()
        layout.addLayout(filters)

        # --- Таблица ---
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Время", "Пользователь", "Роль", "Операция",
            "Таблица", "ID записи", "Было", "Стало"
        ])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        # Двойной клик по строке — показать полный текст "было/стало"
        self.table.cellDoubleClicked.connect(self.show_cell_details)

        # Начальное заполнение списков фильтров и информации
        self.reload_filter_values()

    # ----------------------------------------------------------
    def human_size(self, size_bytes: int) -> str:
        """Человеко-читаемый размер."""
        for unit in ("Б", "КБ", "МБ", "ГБ"):
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} ТБ"

    def update_info(self):
        """Обновляет информационную строку: размер файла и число записей."""
        try:
            size = self.audit.get_size_bytes()
            count = self.audit.count_all()
            size_str = self.human_size(size)
            self.info_label.setText(
                f"Файл журнала: {self.audit.db_path}  |  "
                f"Размер: {size_str}  |  Записей: {count}"
            )
        except Exception as e:
            self.info_label.setText(f"Не удалось получить информацию: {e}")

    def reload_filter_values(self):
        """Заполнить комбобоксы фильтров значениями из БД."""
        rows = self.audit.fetch(limit=1000)
        users = sorted({r["username"] for r in rows if r.get("username")})
        tables = sorted({r["table_name"] for r in rows if r.get("table_name")})

        # Запоминаем текущие значения, чтобы не сбросить выбор пользователя
        cur_user = self.cb_user.currentData()
        cur_table = self.cb_table.currentData()

        self.cb_user.blockSignals(True)
        self.cb_user.clear()
        self.cb_user.addItem("Все", None)
        for u in users:
            self.cb_user.addItem(u, u)
        if cur_user:
            idx = self.cb_user.findData(cur_user)
            if idx >= 0:
                self.cb_user.setCurrentIndex(idx)
        self.cb_user.blockSignals(False)

        self.cb_table.blockSignals(True)
        self.cb_table.clear()
        self.cb_table.addItem("Все", None)
        for t in tables:
            self.cb_table.addItem(t, t)
        if cur_table:
            idx = self.cb_table.findData(cur_table)
            if idx >= 0:
                self.cb_table.setCurrentIndex(idx)
        self.cb_table.blockSignals(False)

    def load_data(self):
        try:
            rows = self.audit.fetch(
                limit=2000,
                username=self.cb_user.currentData(),
                table_name=self.cb_table.currentData(),
                operation=self.cb_op.currentData(),
                date_from=self.dt_from.dateTime().toString("yyyy-MM-ddTHH:mm:ss"),
                date_to=self.dt_to.dateTime().toString("yyyy-MM-ddTHH:mm:ss"),
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать журнал: {e}")
            return

        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            cells = [
                r.get("ts", ""),
                r.get("username", "") or "",
                r.get("role", "") or "",
                r.get("operation", ""),
                r.get("table_name", "") or "",
                r.get("record_id", "") or "",
                (r.get("old_value") or "")[:500],
                (r.get("new_value") or "")[:500],
            ]
            for j, val in enumerate(cells):
                item = QTableWidgetItem(str(val))
                self.table.setItem(i, j, item)

        self.table.resizeRowsToContents()
        self.reload_filter_values()
        self.update_info()

    # ----------------------------------------------------------
    def show_cell_details(self, row, col):
        """Двойной клик по ячейке 'Было' или 'Стало' — показать полный текст."""
        if col not in (6, 7):
            return
        item = self.table.item(row, col)
        if not item:
            return
        # Найдём полную версию — она хранится в фильтрованном списке
        # Проще: заново прочитать именно эту запись из БД
        # Но для простоты — используем текст ячейки (может быть обрезан)
        # Читаем полный текст через повторный запрос по всем полям
        # Здесь воспользуемся тем, что в фильтрованном списке полная запись есть
        # Упрощённый путь: заново запросим 2000 записей и найдём по ts + username
        ts_item = self.table.item(row, 0)
        if not ts_item:
            return
        ts_value = ts_item.text()

        # Перечитываем все записи и ищем нужную
        all_rows = self.audit.fetch(limit=2000)
        target = None
        for r in all_rows:
            if r.get("ts") == ts_value and (r.get("operation") == (self.table.item(row, 3) or "").text()):
                # Ещё проверим таблицу и id, чтобы не перепутать
                if (r.get("table_name") or "") == (self.table.item(row, 4).text() if self.table.item(row, 4) else ""):
                    target = r
                    break

        if not target:
            QMessageBox.information(self, "Полный текст", item.text())
            return

        full_text = target.get("old_value") if col == 6 else target.get("new_value")
        QMessageBox.information(
            self,
            "Полное значение",
            full_text or "(пусто)"
        )

    # ----------------------------------------------------------
    def purge_old(self):
        """Очистка записей старше N дней. N спрашивается у пользователя."""
        days, ok = QInputDialog.getInt(
            self, "Очистка журнала",
            "Удалить записи старше (дней):", 30, 1, 3650, 1
        )
        if not ok:
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить все записи журнала старше {days} дней?\n"
            f"Это действие необратимо.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            n = self.audit.purge_older_than(days)
            QMessageBox.information(self, "Готово", f"Удалено записей: {n}")
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось очистить журнал: {e}")

    def purge_all(self):
        """Полная очистка журнала."""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить ВСЕ записи журнала без возможности восстановления?\n"
            "Продолжить?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        try:
            n = self.audit.purge_all()
            QMessageBox.information(self, "Готово", f"Журнал очищен. Удалено записей: {n}")
            self.load_data()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось очистить журнал: {e}")

    # ----------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()
# views/data/rf_meas.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QLabel, QComboBox, QDateTimeEdit, QMessageBox, QHeaderView
)
from PySide6.QtCore import Qt, QDateTime
from database.db import Database
import statistics


class RfMeasPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_ac_numbers()
        self.setup_connections()  # Подключаем сигналы только после инициализации
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        title = QLabel("Сырые данные измерений (rf_meas)")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Панель фильтров ---
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Прибор:"))
        self.combo_ac = QComboBox()
        self.combo_ac.addItem("Все приборы", -1)
        self.combo_ac.setFixedWidth(150)
        filter_layout.addWidget(self.combo_ac)

        filter_layout.addWidget(QLabel("От:"))
        self.date_from = QDateTimeEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDateTime(QDateTime.currentDateTime().addDays(-1))
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("До:"))
        self.date_to = QDateTimeEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy HH:mm")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDateTime(QDateTime.currentDateTime().addDays(1))
        filter_layout.addWidget(self.date_to)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # --- Таблица ---
        self.table = QTableWidget()
        self.table.setColumnCount(3)  # Оставили только 3 колонки
        self.table.setHorizontalHeaderLabels([
            "Дата измерения", "Прибор (ac_nmb)", "Интенсивность (I)"
        ])

        # Настройка растяжения столбцов
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Дату по ширине содержимого

        # Таблица только для чтения, выделение целыми строками
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table)

        # --- Панель статистики ---
        self.stats_label = QLabel("<b>Статистика:</b> Выделите строки в таблице для расчета")
        self.stats_label.setStyleSheet("""
            QLabel {
                font-size: 14px; 
                padding: 10px; 
                background-color: #f8fafc; 
                border: 1px solid #cbd5e1; 
                border-radius: 6px;
            }
        """)
        self.stats_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.stats_label)

    def setup_connections(self):
        """Подключение сигналов (автоматическое обновление при изменении)"""
        self.combo_ac.currentIndexChanged.connect(self.load_data)
        self.date_from.dateTimeChanged.connect(self.load_data)
        self.date_to.dateTimeChanged.connect(self.load_data)

        # Сигнал выделения ячеек для расчета статистики
        self.table.itemSelectionChanged.connect(self.calculate_statistics)

    def load_ac_numbers(self):
        """Загружает доступные номера приборов из базы данных"""
        try:
            query = "SELECT DISTINCT ac_nmb FROM rf_meas WHERE ac_nmb IS NOT NULL ORDER BY ac_nmb"
            rows = self.db.fetch_all(query)

            # Временно отключаем сигналы, чтобы добавление в комбобокс не вызывало load_data раньше времени
            self.combo_ac.blockSignals(True)
            for row in rows:
                ac = row['ac_nmb']
                self.combo_ac.addItem(f"Прибор №{ac}", ac)
            self.combo_ac.blockSignals(False)
        except Exception as e:
            print(f"Ошибка загрузки списка приборов: {e}")

    def load_data(self):
        """Выгрузка данных из rf_meas с учетом фильтров"""
        dt_from = self.date_from.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        dt_to = self.date_to.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        ac_nmb = self.combo_ac.currentData()

        is_postgres = (self.db.db_type == 'postgres')

        # Убрали лишние столбцы: id, st_ref, i_p, i_b
        select_clause = "SELECT meas_dt, ac_nmb, i FROM rf_meas"
        if not is_postgres:
            select_clause = "SELECT TOP (1000) meas_dt, ac_nmb, i FROM rf_meas"

        where_clause = " WHERE meas_dt BETWEEN ? AND ?"
        params = [dt_from, dt_to]

        if ac_nmb != -1:
            where_clause += " AND ac_nmb = ?"
            params.append(ac_nmb)

        order_clause = " ORDER BY meas_dt DESC"
        limit_clause = " LIMIT 1000" if is_postgres else ""

        query = select_clause + where_clause + order_clause + limit_clause

        try:
            rows = self.db.fetch_all(query, params)

            # Блокируем сигналы таблицы, чтобы при очистке не вызывался расчет статистики
            self.table.blockSignals(True)
            self.table.setRowCount(0)

            if not rows:
                self.table.blockSignals(False)
                self.stats_label.setText("<b>Статистика:</b> Нет данных за выбранный период")
                return

            for row_idx, row in enumerate(rows):
                self.table.insertRow(row_idx)

                # Дата
                dt_val = row.get('meas_dt')
                dt_str = dt_val.strftime("%Y-%m-%d %H:%M:%S") if hasattr(dt_val, 'strftime') else str(dt_val or "")
                self.table.setItem(row_idx, 0, self._create_item(dt_str))

                # Прибор
                self.table.setItem(row_idx, 1, self._create_item(row.get('ac_nmb')))

                # Интенсивность (I)
                self.table.setItem(row_idx, 2, self._create_item(row.get('i'), is_float=True))

            self.table.blockSignals(False)

            # Сбрасываем текст статистики после новой загрузки
            self.stats_label.setText("<b>Статистика:</b> Выделите строки в таблице для расчета")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных: {e}")

    def calculate_statistics(self):
        """Расчет статистики по выделенным строкам для колонки 'I'"""
        # Получаем индексы выделенных строк (используем set, чтобы исключить дубли)
        selected_rows = set(item.row() for item in self.table.selectedItems())

        values = []
        for row in selected_rows:
            item = self.table.item(row, 2)  # Колонка 'I' имеет индекс 2
            if item and item.text():
                try:
                    values.append(float(item.text().replace(',', '.')))
                except ValueError:
                    pass

        n = len(values)
        if n == 0:
            self.stats_label.setText("<b>Статистика:</b> Выделите строки в таблице для расчета")
            return

        mean_val = statistics.mean(values)
        min_val = min(values)
        max_val = max(values)

        if n > 1:
            std_val = statistics.stdev(values)
            rsd_val = (std_val / mean_val * 100) if mean_val != 0 else 0.0

            stats_text = (
                f"<b>Выделено:</b> {n} шт. &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Среднее:</b> <span style='color: #0369a1;'>{mean_val:.4f}</span> &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>СКО:</b> <span style='color: #b91c1c;'>{std_val:.4f}</span> &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Отн. СКО:</b> <span style='color: #b91c1c;'>{rsd_val:.2f}%</span> &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Мин:</b> {min_val:.4f} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Макс:</b> {max_val:.4f}"
            )
        else:
            # Для одного значения СКО посчитать нельзя
            stats_text = (
                f"<b>Выделено:</b> {n} шт. &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Среднее:</b> <span style='color: #0369a1;'>{mean_val:.4f}</span> &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>СКО:</b> - &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Отн. СКО:</b> - &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Мин:</b> {min_val:.4f} &nbsp;&nbsp;|&nbsp;&nbsp; "
                f"<b>Макс:</b> {max_val:.4f}"
            )

        self.stats_label.setText(stats_text)

    def _create_item(self, value, is_float=False):
        """Вспомогательная функция для форматирования ячеек"""
        if value is None:
            text = ""
        elif is_float:
            try:
                text = f"{float(value):.4f}"
            except ValueError:
                text = str(value)
        else:
            text = str(value)

        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def refresh(self):
        """Метод, вызываемый при каждом открытии вкладки (настроено в main.py)"""
        # Если нужно обновлять данные каждый раз при переходе на вкладку,
        # можно раскомментировать строку ниже:
        # self.load_data()
        pass
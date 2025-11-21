from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QPushButton, QLabel,
    QHBoxLayout, QComboBox, QDateTimeEdit, QMessageBox,
    QHeaderView, QScrollArea, QTableWidgetItem, QProgressDialog,
    QTimeEdit, QGroupBox, QFileDialog
)
from PySide6.QtCore import Qt, QDateTime, QTime
from PySide6.QtGui import QFontMetrics, QColor, QFont
from database.db import Database
import math
import json
from pathlib import Path
import statistics
from utils.path_manager import get_config_path

class TimeEdit15Min(QTimeEdit):
    """Кастомный QTimeEdit с шагом 15 минут"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("HH:mm")
        self.setTime(QTime(0, 0))

    def stepBy(self, steps):
        """Переопределяем изменение значения стрелочками с шагом 15 минут"""
        current_time = self.time()
        minutes = current_time.minute()
        hours = current_time.hour()

        # Изменяем время с шагом 15 минут
        new_minutes = minutes + (steps * 15)
        if new_minutes >= 60:
            hours += 1
            new_minutes -= 60
        elif new_minutes < 0:
            hours -= 1
            new_minutes += 60

        # Корректируем часы если вышли за границы
        if hours >= 24:
            hours = 0
        elif hours < 0:
            hours = 23

        self.setTime(QTime(hours, new_minutes))


class ReportPage(QWidget):
    """Виджет для формирования и экспорта отчетов"""

    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.original_data = {}
        self._config_dir = self._get_config_directory()
        self.init_ui()
        self.setup_connections()

    def _get_config_directory(self) -> Path:
        """Получает путь к директории конфигурации"""
        base_dir = Path(__file__).parent
        config_dir = base_dir.parent.parent / "config"
        config_dir.mkdir(exist_ok=True)
        return config_dir

    def _load_config_file(self, filename: str) -> list:
        """Загружает конфигурационный файл JSON"""
        config_path = self._config_dir / filename

        if not config_path.exists():
            print(f"Файл конфигурации не найден: {config_path}")
            return []

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                print(f"Ошибка: {filename} должен содержать список")
                return []

            return data

        except json.JSONDecodeError as e:
            print(f"Ошибка формата JSON в файле {filename}: {str(e)}")
            return []
        except Exception as e:
            print(f"Ошибка загрузки файла {filename}: {str(e)}")
            return []

    def get_configured_elements(self) -> list:
        """Получает список сконфигурированных элементов из JSON-файла"""
        try:
            data = self._load_config_file("elements.json")
            if not data:
                return []

            # Извлекаем имена элементов, исключая невалидные значения
            elements = []
            for item in data:
                try:
                    if not isinstance(item, dict):
                        continue

                    element_name = item.get('name', '').strip()
                    if element_name and element_name not in ('-', 'None', ''):
                        elements.append(element_name)
                except Exception as e:
                    print(f"Ошибка обработки элемента {item}: {str(e)}")
                    continue

            # Сортировка по полю 'number'
            if all('number' in item for item in data):
                elements = sorted(elements,
                                  key=lambda x: next(item['number'] for item in data if item.get('name') == x))

            return elements

        except Exception as e:
            print(f"Ошибка в get_configured_elements: {str(e)}")
            return []

    def get_normatives_from_db(self, pr_nmb: int):
        """Получает нормативы из таблицы set08 для указанного продукта"""
        try:
            query = """
            SELECT el_nmb, delta_c_01, delta_c_02 
            FROM set08 
            WHERE pr_nmb = ?
            ORDER BY el_nmb
            """
            normatives = self.db.fetch_all(query, [pr_nmb])

            # Преобразуем в удобный формат: {el_nmb: (delta_c_01, delta_c_02)}
            normative_dict = {}
            for normative in normatives:
                el_nmb = normative['el_nmb']
                delta_c_01 = self.safe_float(normative['delta_c_01'])
                delta_c_02 = self.safe_float(normative['delta_c_02'])
                normative_dict[el_nmb] = (delta_c_01, delta_c_02)

            return normative_dict

        except Exception as e:
            print(f"Ошибка получения нормативов из БД: {str(e)}")
            return {}

    def round_to_15_min(self, time: QTime) -> QTime:
        """Округляет время до ближайших 15 минут"""
        minute = time.minute()
        rounded_minute = (minute // 15) * 15
        return QTime(time.hour(), rounded_minute)

    def validate_dates(self) -> bool:
        """Проверяет корректность периода"""
        dt_from = QDateTime(self.date_from.date(), self.time_from.time())
        dt_to = QDateTime(self.date_to.date(), self.time_to.time())

        if dt_to < dt_from:
            self.date_to.setStyleSheet("background-color: #ffdddd;")
            QMessageBox.warning(self, "Ошибка", "Дата 'До' не может быть раньше 'От'!")
            return False

        self.date_to.setStyleSheet("")
        return True

    def init_table(self) -> QTableWidget:
        """Инициализация таблицы с данными"""
        table = QTableWidget()
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.verticalHeader().setVisible(False)  # Выключаем вертикальные заголовки
        # Разрешаем выбор строк
        table.setSelectionBehavior(QTableWidget.SelectRows)
        return table

    def configure_table(self):
        """Настройка таблицы отчета"""
        elements = self.get_configured_elements()

        # Столбцы: Время цикла + для каждого элемента: С расч, С хим, ΔC, ΔC/С хим (%)
        column_count = 1 + len(elements) * 4  # Убрали столбец "Модель"
        self.table.clear()
        self.table.setColumnCount(column_count)

        headers = ["Время цикла"]  # Убрали "Модель"
        for element in elements:
            headers.extend([
                f"С расч ({element})",
                f"С хим ({element})",
                f"ΔC ({element})",
                f"ΔC/С хим ({element}) %"
            ])
        self.table.setHorizontalHeaderLabels(headers)

        # Устанавливаем ширину столбцов
        time_width = QFontMetrics(self.font()).horizontalAdvance("Время цикла") + 20
        element_width = max(
            QFontMetrics(self.font()).horizontalAdvance("С расч (XXX)"),
            QFontMetrics(self.font()).horizontalAdvance("С хим (XXX)"),
            QFontMetrics(self.font()).horizontalAdvance("ΔC (XXX)"),
            QFontMetrics(self.font()).horizontalAdvance("ΔC/С хим (XXX) %")
        ) + 20

        self.table.setColumnWidth(0, time_width)

        for i in range(1, column_count):
            self.table.setColumnWidth(i, element_width)

    def safe_float(self, value):
        """Безопасное преобразование в float"""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def safe_int(self, value):
        """Безопасное преобразование в int"""
        if value is None:
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    def get_f_critical_value(self, n):
        """Получает табличное значение F-критерия для уровня значимости 0.95"""
        # Табличные значения F для уровня значимости 0.05 (95% доверительный интервал)
        # df = n - 1 (степени свободы)

        # Таблица F-распределения для alpha=0.05
        # Ключ: степени свободы, значение: F-критерий
        f_table = {
            1: 161.4, 2: 18.51, 3: 10.13, 4: 7.71, 5: 6.61,
            6: 5.99, 7: 5.59, 8: 5.32, 9: 5.12, 10: 4.96,
            11: 4.84, 12: 4.75, 13: 4.67, 14: 4.60, 15: 4.54,
            16: 4.49, 17: 4.45, 18: 4.41, 19: 4.38, 20: 4.35,
            25: 4.24, 30: 4.17, 40: 4.08, 60: 4.00, 120: 3.92
        }

        df = n - 1
        if df < 1:
            df = 1

        # Находим ближайшее значение в таблице
        if df in f_table:
            return f_table[df]
        elif df > 120:
            return 3.84  # Приближение для больших степеней свободы
        else:
            # Линейная интерполяция для промежуточных значений
            keys = sorted(f_table.keys())
            for i in range(len(keys) - 1):
                if keys[i] <= df <= keys[i + 1]:
                    x1, y1 = keys[i], f_table[keys[i]]
                    x2, y2 = keys[i + 1], f_table[keys[i + 1]]
                    return y1 + (y2 - y1) * (df - x1) / (x2 - x1)

        return 4.0  # Значение по умолчанию

    def get_active_model_coefficients(self, pr_nmb: int):
        """Получает коэффициенты активной модели"""
        try:
            # Находим активную модель
            active_model_query = """
            SELECT DISTINCT mdl_nmb 
            FROM PR_SET 
            WHERE pr_nmb = ? AND active_model = 1
            """
            active_model_result = self.db.fetch_one(active_model_query, [pr_nmb])

            if not active_model_result:
                return None, None

            active_model = active_model_result['mdl_nmb']

            # Получаем все коэффициенты для активной модели
            coefficients_query = """
            SELECT 
                el_nmb, meas_type,
                k_i_alin00, k_i_alin01, k_i_alin02, k_i_alin03, k_i_alin04, k_i_alin05,
                k_i_klin00, k_i_klin01,
                operand_i_01_01, operand_i_02_01, operator_i_01,
                operand_i_01_02, operand_i_02_02, operator_i_02,
                operand_i_01_03, operand_i_02_03, operator_i_03,
                operand_i_01_04, operand_i_02_04, operator_i_04,
                operand_i_01_05, operand_i_02_05, operator_i_05,
                k_c_alin00, k_c_alin01, k_c_alin02, k_c_alin03, k_c_alin04, k_c_alin05,
                k_c_klin00, k_c_klin01,
                operand_c_01_01, operand_c_02_01, operator_c_01,
                operand_c_01_02, operand_c_02_02, operator_c_02,
                operand_c_01_03, operand_c_02_03, operator_c_03,
                operand_c_01_04, operand_c_02_04, operator_c_04,
                operand_c_01_05, operand_c_02_05, operator_c_05
            FROM PR_SET 
            WHERE pr_nmb = ? AND mdl_nmb = ?
            ORDER BY el_nmb
            """
            coefficients = self.db.fetch_all(coefficients_query, [pr_nmb, active_model])

            if not coefficients:
                return active_model, None

            return active_model, coefficients

        except Exception as e:
            print(f"Ошибка получения коэффициентов активной модели: {str(e)}")
            return None, None

    def calculate_operation(self, operand1, operand2, operator, row_data, is_intensity=True):
        """Вычисляет операцию согласно логике хранимой процедуры"""
        try:
            if is_intensity:
                # Для интенсивностей: i_00_00 до i_00_19
                val1 = self.safe_float(row_data.get(f'i_00_{operand1:02d}'))
                val2 = self.safe_float(row_data.get(f'i_00_{operand2:02d}'))
            else:
                # Для концентраций: c_01 до c_08 (в PR_SET нумерация с 0, в данных с 1)
                element_num1 = operand1 + 1
                element_num2 = operand2 + 1
                val1 = self.safe_float(row_data.get(f'c_{element_num1:02d}'))
                val2 = self.safe_float(row_data.get(f'c_{element_num2:02d}'))

            # Применяем оператор согласно логике хранимой процедуры
            if operator == 0:  # operand1 * 0 * operand2
                result = val1 * 0 * val2
            elif operator == 1:  # operand1 * 1
                result = val1 * 1
            elif operator == 2:  # operand1 * operand2
                result = val1 * val2
            elif operator == 3:  # operand1 / operand2
                result = val1 / val2 if val2 != 0 else 0
            elif operator == 4:  # operand1 * operand1 (квадрат)
                result = val1 * val1
            elif operator == 5:  # 1 / operand1
                result = 1 / val1 if val1 != 0 else 0
            elif operator == 6:  # operand1 / (operand2 * operand2)
                denominator = val2 * val2
                result = val1 / denominator if denominator != 0 else 0
            elif operator == 7:  # 1 / (operand1 * operand1)
                denominator = val1 * val1
                result = 1 / denominator if denominator != 0 else 0
            else:
                result = 0

            return result

        except Exception as e:
            print(f"Ошибка вычисления операции: {str(e)}")
            return 0

    def calculate_concentration(self, row_data, coeffs, element_num):
        """Расчет концентрации по алгоритму хранимой процедуры"""
        try:
            meas_type = self.safe_int(coeffs.get('meas_type'))
            is_intensity = (meas_type == 0)

            if is_intensity:
                # Коэффициенты для ИНТЕНСИВНОСТЕЙ (meas_type = 0)
                k_alin00 = self.safe_float(coeffs.get('k_i_alin00'))
                k_alin01 = self.safe_float(coeffs.get('k_i_alin01'))
                k_alin02 = self.safe_float(coeffs.get('k_i_alin02'))
                k_alin03 = self.safe_float(coeffs.get('k_i_alin03'))
                k_alin04 = self.safe_float(coeffs.get('k_i_alin04'))
                k_alin05 = self.safe_float(coeffs.get('k_i_alin05'))
                k_klin00 = self.safe_float(coeffs.get('k_i_klin00'))
                k_klin01 = self.safe_float(coeffs.get('k_i_klin01'))

                # Операторы для ИНТЕНСИВНОСТЕЙ
                op_01_01 = self.safe_int(coeffs.get('operand_i_01_01'))
                op_02_01 = self.safe_int(coeffs.get('operand_i_02_01'))
                oper_01 = self.safe_int(coeffs.get('operator_i_01'))
                op_01_02 = self.safe_int(coeffs.get('operand_i_01_02'))
                op_02_02 = self.safe_int(coeffs.get('operand_i_02_02'))
                oper_02 = self.safe_int(coeffs.get('operator_i_02'))
                op_01_03 = self.safe_int(coeffs.get('operand_i_01_03'))
                op_02_03 = self.safe_int(coeffs.get('operand_i_02_03'))
                oper_03 = self.safe_int(coeffs.get('operator_i_03'))
                op_01_04 = self.safe_int(coeffs.get('operand_i_01_04'))
                op_02_04 = self.safe_int(coeffs.get('operand_i_02_04'))
                oper_04 = self.safe_int(coeffs.get('operator_i_04'))
                op_01_05 = self.safe_int(coeffs.get('operand_i_01_05'))
                op_02_05 = self.safe_int(coeffs.get('operand_i_02_05'))
                oper_05 = self.safe_int(coeffs.get('operator_i_05'))

            else:
                # Коэффициенты для КОНЦЕНТРАЦИЙ (meas_type = 1)
                k_alin00 = self.safe_float(coeffs.get('k_c_alin00'))
                k_alin01 = self.safe_float(coeffs.get('k_c_alin01'))
                k_alin02 = self.safe_float(coeffs.get('k_c_alin02'))
                k_alin03 = self.safe_float(coeffs.get('k_c_alin03'))
                k_alin04 = self.safe_float(coeffs.get('k_c_alin04'))
                k_alin05 = self.safe_float(coeffs.get('k_c_alin05'))
                k_klin00 = self.safe_float(coeffs.get('k_c_klin00'))
                k_klin01 = self.safe_float(coeffs.get('k_c_klin01'))

                # Операторы для КОНЦЕНТРАЦИЙ
                op_01_01 = self.safe_int(coeffs.get('operand_c_01_01'))
                op_02_01 = self.safe_int(coeffs.get('operand_c_02_01'))
                oper_01 = self.safe_int(coeffs.get('operator_c_01'))
                op_01_02 = self.safe_int(coeffs.get('operand_c_01_02'))
                op_02_02 = self.safe_int(coeffs.get('operand_c_02_02'))
                oper_02 = self.safe_int(coeffs.get('operator_c_02'))
                op_01_03 = self.safe_int(coeffs.get('operand_c_01_03'))
                op_02_03 = self.safe_int(coeffs.get('operand_c_02_03'))
                oper_03 = self.safe_int(coeffs.get('operator_c_03'))
                op_01_04 = self.safe_int(coeffs.get('operand_c_01_04'))
                op_02_04 = self.safe_int(coeffs.get('operand_c_02_04'))
                oper_04 = self.safe_int(coeffs.get('operator_c_04'))
                op_01_05 = self.safe_int(coeffs.get('operand_c_01_05'))
                op_02_05 = self.safe_int(coeffs.get('operand_c_02_05'))
                oper_05 = self.safe_int(coeffs.get('operator_c_05'))

            # Вычисляем все операции
            oper_result_01 = self.calculate_operation(op_01_01, op_02_01, oper_01, row_data, is_intensity)
            oper_result_02 = self.calculate_operation(op_01_02, op_02_02, oper_02, row_data, is_intensity)
            oper_result_03 = self.calculate_operation(op_01_03, op_02_03, oper_03, row_data, is_intensity)
            oper_result_04 = self.calculate_operation(op_01_04, op_02_04, oper_04, row_data, is_intensity)
            oper_result_05 = self.calculate_operation(op_01_05, op_02_05, oper_05, row_data, is_intensity)

            # Расчет концентрации
            c = (k_alin00 +
                 k_alin01 * oper_result_01 +
                 k_alin02 * oper_result_02 +
                 k_alin03 * oper_result_03 +
                 k_alin04 * oper_result_04 +
                 k_alin05 * oper_result_05)

            # Расчет скорректированной концентрации
            c_cor = k_klin00 + k_klin01 * c

            return c_cor

        except Exception as e:
            print(f"Ошибка расчета концентрации для элемента {element_num}: {str(e)}")
            return 0

    def calculate_statistics_from_table_data(self, elements, data_start_row):
        """Расчет статистики из данных таблицы (начиная с указанной строки)"""
        stats = {}

        for col_idx, element in enumerate(elements):
            element_stats = {
                'calculated': [],
                'chemical': [],
                'deltas': [],
                'relative_deltas': [],
                'valid_count': 0  # Добавляем счетчик валидных значений
            }

            col_base = 1 + col_idx * 4

            for row in range(data_start_row, self.table.rowCount()):
                try:
                    calc_item = self.table.item(row, col_base)
                    chem_item = self.table.item(row, col_base + 1)
                    delta_item = self.table.item(row, col_base + 2)
                    relative_item = self.table.item(row, col_base + 3)

                    if calc_item and chem_item and chem_item.text() != "-":
                        # Только если С хим не прочерк
                        c_calc = float(calc_item.text())
                        c_chem = float(chem_item.text())

                        # Проверяем что delta_item не прочерк
                        if delta_item and delta_item.text() != "-":
                            delta = float(delta_item.text())
                        else:
                            delta = 0

                        # Проверяем что relative_item не прочерк
                        if relative_item and relative_item.text() != "-":
                            relative_text = relative_item.text().replace('%', '').strip()
                            if relative_text != "-":
                                relative_percent = float(relative_text)
                            else:
                                relative_percent = 0
                        else:
                            relative_percent = 0

                        element_stats['calculated'].append(c_calc)
                        element_stats['chemical'].append(c_chem)
                        element_stats['deltas'].append(delta)
                        element_stats['relative_deltas'].append(relative_percent)
                        element_stats['valid_count'] += 1

                except (ValueError, AttributeError) as e:
                    continue

            stats[element] = element_stats

        return stats

    def add_statistics_rows(self, stats, elements, normatives, pr_nmb, data_start_row, total_rows):
        """Добавляет строки статистики в основную таблицу с учетом нормативов из БД и F-критерия"""
        # Создаем жирный шрифт
        bold_font = QFont()
        bold_font.setBold(True)

        # Цвета для подсветки
        light_green = QColor(200, 255, 200)  # Светло-зеленый
        light_red = QColor(255, 200, 200)  # Светло-красный

        # Количество наблюдений для расчета F-критерия
        n = total_rows - data_start_row  # количество наблюдений
        if n < 2:
            n = 2  # минимальное значение для расчета СКО

        # Получаем табличное значение F
        f_critical = self.get_f_critical_value(n)

        for col_idx, element in enumerate(elements):
            element_num = col_idx + 1  # Номер элемента (начинается с 1)

            if element not in stats:
                # Если элемента нет в статистике, ставим прочерки
                col_base = 1 + col_idx * 4
                self.table.setItem(0, col_base, QTableWidgetItem("-"))  # Ср.расч
                self.table.setItem(0, col_base + 1, QTableWidgetItem("-"))  # С хим
                self.table.setItem(0, col_base + 2, QTableWidgetItem("-"))  # ΔC
                self.table.setItem(0, col_base + 3, QTableWidgetItem("-"))  # Отн.ΔC%

                self.table.setItem(1, col_base, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 2, QTableWidgetItem("-"))  # СКО ΔC
                self.table.setItem(1, col_base + 3, QTableWidgetItem("-"))  # СКО Отн.ΔC%

                self.table.setItem(3, col_base, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 2, QTableWidgetItem("-"))  # Вывод ΔC
                self.table.setItem(3, col_base + 3, QTableWidgetItem("-"))  # Вывод Отн.ΔC%
                continue

            element_stats = stats[element]
            col_base = 1 + col_idx * 4  # 1 - потому что первый столбец "Время цикла"

            # Получаем нормативы для текущего элемента и продукта
            normative_delta_c_01 = 0.0  # значение по умолчанию
            normative_delta_c_02 = 0.0  # значение по умолчанию

            if element_num in normatives:
                normative_delta_c_01, normative_delta_c_02 = normatives[element_num]

            # ПРОВЕРКА: достаточно ли данных для статистики (минимум 5 ненулевых С хим)
            if element_stats['valid_count'] < 5:
                # Недостаточно данных - ставим прочерки ВО ВСЕХ полях статистики
                self.table.setItem(0, col_base, QTableWidgetItem("-"))  # Ср.расч
                self.table.setItem(0, col_base + 1, QTableWidgetItem("-"))  # С хим
                self.table.setItem(0, col_base + 2, QTableWidgetItem("-"))  # ΔC
                self.table.setItem(0, col_base + 3, QTableWidgetItem("-"))  # Отн.ΔC%

                self.table.setItem(1, col_base, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 2, QTableWidgetItem("-"))  # СКО ΔC
                self.table.setItem(1, col_base + 3, QTableWidgetItem("-"))  # СКО Отн.ΔC%

                # Обновляем строку "Норматив" (строка 2)
                self.table.setItem(2, col_base, QTableWidgetItem(""))
                self.table.setItem(2, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(2, col_base + 2,
                                   QTableWidgetItem(f"{normative_delta_c_01:.4f}" if normative_delta_c_01 > 0 else "-"))
                self.table.setItem(2, col_base + 3,
                                   QTableWidgetItem(
                                       f"{normative_delta_c_02:.0f}%" if normative_delta_c_02 > 0 else "-"))

                self.table.setItem(3, col_base, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 2, QTableWidgetItem("-"))  # Вывод ΔC
                self.table.setItem(3, col_base + 3, QTableWidgetItem("-"))  # Вывод Отн.ΔC%
                continue  # Переходим к следующему элементу

            # Средние значения - считаем ТОЛЬКО по валидным данным (где С хим ≠ 0)
            if element_stats['calculated'] and element_stats['chemical']:
                avg_calc = statistics.mean(element_stats['calculated'])
                avg_chem = statistics.mean(element_stats['chemical'])
                avg_delta = statistics.mean(element_stats['deltas'])
                avg_relative = statistics.mean(element_stats['relative_deltas'])
            else:
                # Если нет валидных данных, ставим прочерки
                self.table.setItem(0, col_base, QTableWidgetItem("-"))
                self.table.setItem(0, col_base + 1, QTableWidgetItem("-"))
                self.table.setItem(0, col_base + 2, QTableWidgetItem("-"))
                self.table.setItem(0, col_base + 3, QTableWidgetItem("-"))

                self.table.setItem(1, col_base, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 2, QTableWidgetItem("-"))
                self.table.setItem(1, col_base + 3, QTableWidgetItem("-"))

                self.table.setItem(3, col_base, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 2, QTableWidgetItem("-"))
                self.table.setItem(3, col_base + 3, QTableWidgetItem("-"))
                continue

            # СКО - считаем ТОЛЬКО если есть хотя бы 2 валидных значения
            if len(element_stats['deltas']) > 1:
                std_delta = statistics.stdev(element_stats['deltas'])
                std_relative = statistics.stdev(element_stats['relative_deltas'])
            else:
                # Если недостаточно данных для СКО, ставим прочерки
                std_delta = 0
                std_relative = 0

            # Заполняем строку "Среднее" (строка 0)
            self.table.setItem(0, col_base, QTableWidgetItem(f"{avg_calc:.6f}"))
            self.table.setItem(0, col_base + 1, QTableWidgetItem(f"{avg_chem:.6f}"))
            self.table.setItem(0, col_base + 2, QTableWidgetItem(f"{avg_delta:.6f}"))
            self.table.setItem(0, col_base + 3, QTableWidgetItem(f"{avg_relative:.1f}%"))

            # Заполняем строку "СКО" (строка 1)
            self.table.setItem(1, col_base, QTableWidgetItem(""))
            self.table.setItem(1, col_base + 1, QTableWidgetItem(""))
            if len(element_stats['deltas']) > 1:
                self.table.setItem(1, col_base + 2, QTableWidgetItem(f"{std_delta:.6f}"))
                self.table.setItem(1, col_base + 3, QTableWidgetItem(f"{std_relative:.1f}%"))
            else:
                self.table.setItem(1, col_base + 2, QTableWidgetItem("-"))
                self.table.setItem(1, col_base + 3, QTableWidgetItem("-"))

            # Заполняем строку "Норматив" (строка 2) - теперь берем из БД
            self.table.setItem(2, col_base, QTableWidgetItem(""))
            self.table.setItem(2, col_base + 1, QTableWidgetItem(""))
            self.table.setItem(2, col_base + 2,
                               QTableWidgetItem(f"{normative_delta_c_01:.4f}" if normative_delta_c_01 > 0 else "-"))
            self.table.setItem(2, col_base + 3,
                               QTableWidgetItem(f"{normative_delta_c_02:.0f}%" if normative_delta_c_02 > 0 else "-"))

            # Заполняем строку "Вывод" (строка 3) - проверяем по нормативам из БД с F-критерием
            # Для процентного отношения - простое сравнение
            if normative_delta_c_02 == 0 or len(element_stats['relative_deltas']) <= 1:
                relative_status = "-"
                is_relative_ok = True
            else:
                is_relative_ok = std_relative <= normative_delta_c_02 if element_stats['relative_deltas'] else True
                relative_status = "Норма" if is_relative_ok else "Не норма"

            # Для delta C - используем F-критерий
            if normative_delta_c_01 == 0 or len(element_stats['deltas']) <= 1:
                # Если нет норматива для delta C или недостаточно данных
                delta_status = "-"
                is_delta_ok = True
            else:
                # Вычисляем F-расчетное как (СКО / Норматив delta C)
                f_calculated = std_delta / normative_delta_c_01

                # F-расчетное < F-табличное => Норма
                if f_calculated < f_critical:
                    delta_status = "Норма"
                    is_delta_ok = True
                else:
                    delta_status = "Не норма"
                    is_delta_ok = False

            delta_item = QTableWidgetItem(delta_status)
            relative_item = QTableWidgetItem(relative_status)

            # Подсветка вывода
            if is_delta_ok:
                delta_item.setBackground(light_green)
            else:
                delta_item.setBackground(light_red)

            if is_relative_ok:
                relative_item.setBackground(light_green)
            else:
                relative_item.setBackground(light_red)

            self.table.setItem(3, col_base, QTableWidgetItem(""))
            self.table.setItem(3, col_base + 1, QTableWidgetItem(""))
            self.table.setItem(3, col_base + 2, delta_item)
            self.table.setItem(3, col_base + 3, relative_item)

        # Добавляем пустую строку-разделитель после "Вывод"
        separator_row = 4  # Это будет 5-я строка (индекс 4)
        self.table.insertRow(separator_row)

        # Заполняем всю строку серым цветом
        for col in range(self.table.columnCount()):
            item = QTableWidgetItem("")
            item.setBackground(QColor(220, 220, 220))  # Серый фон
            self.table.setItem(separator_row, col, item)

        # Устанавливаем жирный шрифт для заголовков статистики в столбце "Время цикла"
        stat_names = ["Среднее", "СКО", "Норматив", "Вывод"]
        for i, name in enumerate(stat_names):
            item = self.table.item(i, 0)
            if item:
                item.setFont(bold_font)

    def load_report_data(self):
        """Загружает данные для отчета с расчетом c_cor на основе активной модели"""
        try:
            self.table.setRowCount(0)

            if not self.validate_dates():
                return

            dt_from = QDateTime(self.date_from.date(), self.time_from.time()).toString("yyyy-MM-dd HH:mm:ss")
            dt_to = QDateTime(self.date_to.date(), self.time_to.time()).toString("yyyy-MM-dd HH:mm:ss")

            selected_product = self.product_combo.currentText()
            try:
                pr_nmb = int(selected_product.split()[-1])
            except:
                QMessageBox.warning(self, "Ошибка", "Неверный формат номера продукта")
                return

            # Получаем нормативы из БД
            normatives = self.get_normatives_from_db(pr_nmb)
            if not normatives:
                QMessageBox.warning(self, "Предупреждение",
                                    f"Не найдены нормативы для продукта {pr_nmb} в таблице set08")

            # Получаем коэффициенты активной модели
            active_model, coefficients = self.get_active_model_coefficients(pr_nmb)
            if not coefficients:
                QMessageBox.warning(self, "Ошибка", "Не найдены коэффициенты для активной модели")
                return

            # Загружаем данные измерений
            query = """
            SELECT 
                id, mdl_nmb, meas_dt,
                c_01, c_02, c_03, c_04, c_05, c_06, c_07, c_08,
                c_chem_01, c_chem_02, c_chem_03, c_chem_04, 
                c_chem_05, c_chem_06, c_chem_07, c_chem_08,
                i_00_00, i_00_01, i_00_02, i_00_03, i_00_04, i_00_05, i_00_06, i_00_07, i_00_08, i_00_09,
                i_00_10, i_00_11, i_00_12, i_00_13, i_00_14, i_00_15, i_00_16, i_00_17, i_00_18, i_00_19
            FROM pr_meas
            WHERE meas_dt BETWEEN ? AND ?
            AND pr_nmb = ? AND mdl_nmb = ? AND active_model = 1
            AND (
                c_chem_01 <> 0 OR c_chem_02 <> 0 OR c_chem_03 <> 0 OR c_chem_04 <> 0 OR
                c_chem_05 <> 0 OR c_chem_06 <> 0 OR c_chem_07 <> 0 OR c_chem_08 <> 0
            )
            ORDER BY meas_dt
            """

            params = [dt_from, dt_to, pr_nmb, active_model]
            rows = self.db.fetch_all(query, params)

            if not rows:
                QMessageBox.information(self, "Информация",
                                        "Данные не найдены для выбранного периода и продукта.")
                return

            elements = self.get_configured_elements()

            # Настраиваем таблицу
            self.configure_table()

            # Сначала добавляем 4 строки для статистики
            self.table.setRowCount(4)

            # Записываем названия статистики в столбец "Время цикла" жирным шрифтом
            bold_font = QFont()
            bold_font.setBold(True)

            stat_names = ["Среднее", "СКО", "Норматив", "Вывод"]
            for i, name in enumerate(stat_names):
                item = QTableWidgetItem(name)
                item.setFont(bold_font)
                self.table.setItem(i, 0, item)

            # Теперь добавляем основные данные, начиная с 5-й строки
            data_start_row = 4
            self.table.setRowCount(data_start_row + len(rows))

            for row_idx, row in enumerate(rows):
                row_position = data_start_row + row_idx

                # Время цикла
                meas_dt = row.get('meas_dt')
                if isinstance(meas_dt, str):
                    dt_str = meas_dt
                elif hasattr(meas_dt, 'strftime'):
                    dt_str = meas_dt.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    dt_str = str(meas_dt) if meas_dt else ""

                time_item = QTableWidgetItem(dt_str)
                self.table.setItem(row_position, 0, time_item)

                # Данные по элементам
                for i, element in enumerate(elements, 1):
                    if i > 8:
                        break

                    col_base = 1 + (i - 1) * 4  # Смещение из-за убранного столбца "Модель"

                    # Находим коэффициенты для текущего элемента
                    element_coeffs = next((coeff for coeff in coefficients if coeff['el_nmb'] == i), None)
                    if not element_coeffs:
                        c_calc = 0
                    else:
                        # Расчет концентрации на основе коэффициентов активной модели
                        c_calc = self.calculate_concentration(row, element_coeffs, i)

                    # С расчетное (рассчитанное)
                    c_calc_item = QTableWidgetItem(f"{c_calc:.4f}")
                    c_calc_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    self.table.setItem(row_position, col_base, c_calc_item)

                    # С химическое
                    c_chem = row.get(f'c_chem_{i:02d}', 0)
                    if c_chem is None or float(c_chem) == 0:
                        # Если С хим равно нулю, ставим прочерки
                        c_chem_item = QTableWidgetItem("-")
                        delta_c_item = QTableWidgetItem("-")
                        delta_percent_item = QTableWidgetItem("-")
                    else:
                        c_chem_item = QTableWidgetItem(f"{float(c_chem):.4f}")

                        # ΔC (разница)
                        delta_c = c_calc - float(c_chem)
                        delta_c_item = QTableWidgetItem(f"{delta_c:.4f}")

                        # ΔC/С хим (%)
                        delta_percent = (delta_c / float(c_chem)) * 100
                        delta_percent = round(delta_percent)
                        delta_percent_item = QTableWidgetItem(f"{delta_percent:.0f}%")

                        # Подсветка больших отклонений
                        if abs(delta_c) > 0.1:
                            delta_c_item.setBackground(QColor(255, 255, 200))
                        if abs(delta_percent) > 10:
                            delta_percent_item.setBackground(QColor(255, 255, 200))

                    c_chem_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    delta_c_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    delta_percent_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                    self.table.setItem(row_position, col_base + 1, c_chem_item)
                    self.table.setItem(row_position, col_base + 2, delta_c_item)
                    self.table.setItem(row_position, col_base + 3, delta_percent_item)

            # Теперь рассчитываем статистику из данных таблицы
            stats = self.calculate_statistics_from_table_data(elements,
                                                              data_start_row + 1)  # +1 из-за добавленной пустой строки
            self.add_statistics_rows(stats, elements, normatives, pr_nmb, data_start_row + 1, self.table.rowCount())

            self.table.resizeColumnsToContents()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка загрузки данных отчета: {str(e)}")
            self.table.setRowCount(0)

    def export_to_file(self):
        """Экспорт данных в файл"""
        try:
            if self.table.rowCount() == 0:
                QMessageBox.warning(self, "Предупреждение", "Нет данных для экспорта")
                return

            # Получаем настройки для формирования имени файла
            selected_product = self.product_combo.currentText()
            dt_from = QDateTime(self.date_from.date(), self.time_from.time()).toString("yyyy-MM-dd_HH-mm")
            dt_to = QDateTime(self.date_to.date(), self.time_to.time()).toString("yyyy-MM-dd_HH-mm")

            # Предлагаем пользователю выбрать файл для сохранения
            from PySide6.QtWidgets import QFileDialog
            default_filename = f"отчет_{selected_product}_{dt_from}_по_{dt_to}.csv"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить отчет как CSV",
                default_filename,
                "CSV Files (*.csv);;All Files (*)"
            )

            if not file_path:
                return  # Пользователь отменил сохранение

            # Добавляем расширение .csv если его нет
            if not file_path.lower().endswith('.csv'):
                file_path += '.csv'

            # Экспортируем данные в CSV
            self.export_to_csv(file_path)

            QMessageBox.information(self, "Успех", f"Отчет успешно сохранен в файл:\n{file_path}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка при экспорте: {str(e)}")

    def export_to_csv(self, file_path):
        """Экспорт данных таблицы в CSV файл"""
        try:
            import csv
            from pathlib import Path

            # Создаем директорию если не существует
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile, delimiter=';', quoting=csv.QUOTE_MINIMAL)

                # Записываем заголовок с информацией о периоде и продукте
                self.write_csv_header(writer)

                # Записываем заголовки таблицы
                headers = []
                for col in range(self.table.columnCount()):
                    header = self.table.horizontalHeaderItem(col)
                    headers.append(header.text() if header else f"Column_{col}")
                writer.writerow(headers)

                # Записываем данные таблицы
                for row in range(self.table.rowCount()):
                    row_data = []
                    for col in range(self.table.columnCount()):
                        item = self.table.item(row, col)
                        if item is not None:
                            # Обрабатываем специальные случаи (серые строки и т.д.)
                            text = self.process_cell_text(item.text(), row, col)
                            row_data.append(text)
                        else:
                            row_data.append("")

                    writer.writerow(row_data)

        except Exception as e:
            raise Exception(f"Ошибка записи CSV файла: {str(e)}")

    def write_csv_header(self, writer):
        """Записывает заголовочную информацию в CSV"""
        try:
            # Информация о периоде
            dt_from = QDateTime(self.date_from.date(), self.time_from.time()).toString("dd.MM.yyyy HH:mm")
            dt_to = QDateTime(self.date_to.date(), self.time_to.time()).toString("dd.MM.yyyy HH:mm")
            selected_product = self.product_combo.currentText()

            writer.writerow(["Отчет по химическим содержаниям"])
            writer.writerow([f"Продукт: {selected_product}"])
            writer.writerow([f"Период: с {dt_from} по {dt_to}"])
            writer.writerow([f"Дата формирования: {QDateTime.currentDateTime().toString('dd.MM.yyyy HH:mm:ss')}"])
            writer.writerow([])  # Пустая строка

        except Exception as e:
            print(f"Ошибка записи заголовка CSV: {str(e)}")

    def process_cell_text(self, text, row, col):
        """Обрабатывает текст ячейки для корректного отображения в CSV"""
        try:
            if row == 4:  # Серая строка-разделитель
                    return "---"

            # Обработка статистических строк
            stat_rows = {
                0: "Среднее",
                1: "СКО",
                2: "Норматив",
                3: "Вывод"
            }

            if row in stat_rows and col == 0:
                return stat_rows[row]

            # Заменяем прочерки и специальные символы если нужно
            if text.strip() in ['-', '--', '---']:
                return text

            # Для числовых значений убираем лишние пробелы
            return text.strip()

        except Exception as e:
            print(f"Ошибка обработки текста ячейки: {str(e)}")
            return text

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        self.setMinimumWidth(1200)
        self.setMinimumHeight(700)

        title = QLabel("Отчет по химическим содержаниям")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Верхняя панель с настройками
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(15)

        # Выбор продукта - САМЫЙ ВЕРХ
        product_layout = QHBoxLayout()
        product_layout.addWidget(QLabel("Продукт:"))
        self.product_combo = QComboBox()
        products = [f"Продукт {i}" for i in range(1, 9)]
        self.product_combo.addItems(products)
        self.product_combo.setFixedWidth(120)
        product_layout.addWidget(self.product_combo)
        product_layout.addStretch()
        settings_layout.addLayout(product_layout)

        # Даты и время - В СТОЛБИК
        dates_layout = QVBoxLayout()
        dates_layout.setSpacing(8)

        # Период "От" - отдельная строка
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("От:"))

        self.date_from = QDateTimeEdit()
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        self.date_from.setCalendarPopup(True)
        self.date_from.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self.date_from.setFixedWidth(90)

        self.time_from = TimeEdit15Min()
        self.time_from.setTime(self.round_to_15_min(QTime(0, 0)))
        self.time_from.setFixedWidth(60)

        from_layout.addWidget(self.date_from)
        from_layout.addWidget(self.time_from)
        from_layout.addStretch()
        dates_layout.addLayout(from_layout)

        # Период "До" - отдельная строка
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("До:"))

        self.date_to = QDateTimeEdit()
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        self.date_to.setCalendarPopup(True)
        self.date_to.setDateTime(QDateTime.currentDateTime())
        self.date_to.setFixedWidth(90)

        self.time_to = TimeEdit15Min()
        self.time_to.setTime(self.round_to_15_min(QTime.currentTime()))
        self.time_to.setFixedWidth(60)

        to_layout.addWidget(self.date_to)
        to_layout.addWidget(self.time_to)
        to_layout.addStretch()
        dates_layout.addLayout(to_layout)

        settings_layout.addLayout(dates_layout)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.load_btn = QPushButton("Выгрузка из БД")
        self.load_btn.setFixedSize(150, 30)
        buttons_layout.addWidget(self.load_btn)

        self.export_btn = QPushButton("Выгрузка в файл")
        self.export_btn.setFixedSize(150, 30)
        buttons_layout.addWidget(self.export_btn)

        buttons_layout.addStretch()
        settings_layout.addLayout(buttons_layout)

        main_layout.addLayout(settings_layout)

        # Основная таблица (теперь содержит и статистику и данные)
        self.table = self.init_table()
        self.configure_table()

        scroll_area = QScrollArea()
        scroll_area.setWidget(self.table)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        main_layout.addWidget(scroll_area)

    def setup_connections(self):
        """Настройка соединений сигналов и слотов"""
        self.load_btn.clicked.connect(self.load_report_data)
        self.export_btn.clicked.connect(self.export_to_file)

        # Обработка двойного клика для удаления строк
        self.table.doubleClicked.connect(self.delete_selected_row)

        # Валидация дат при изменении
        self.date_from.dateTimeChanged.connect(self.validate_dates)
        self.time_from.timeChanged.connect(self.validate_dates)
        self.date_to.dateTimeChanged.connect(self.validate_dates)
        self.time_to.timeChanged.connect(self.validate_dates)

    def delete_selected_row(self, index):
        """Удаляет выбранную строку при двойном клике"""
        row = index.row()

        # Не позволяем удалять строки статистики (первые 5 строк)
        if row < 5:  # Среднее, СКО, Норматив, Вывод, пустая строка
            return

        # Создаем кастомное окно подтверждения с русскими кнопками
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Подтверждение удаления")
        msg_box.setText("Вы уверены, что хотите удалить эту строку?")
        msg_box.setIcon(QMessageBox.Question)

        # Создаем кнопки с русским текстом
        btn_yes = msg_box.addButton("Да", QMessageBox.YesRole)
        btn_no = msg_box.addButton("Нет", QMessageBox.NoRole)
        msg_box.setDefaultButton(btn_no)

        msg_box.exec()

        if msg_box.clickedButton() == btn_yes:
            self.table.removeRow(row)
            # После удаления пересчитываем статистику
            self.recalculate_statistics_after_deletion()

    def recalculate_statistics_after_deletion(self):
        """Пересчитывает статистику после удаления строки"""
        elements = self.get_configured_elements()
        data_start_row = 5  # Строка, с которой начинаются данные (после статистики)

        if self.table.rowCount() > data_start_row:
            # Пересчитываем статистику из оставшихся данных
            stats = self.calculate_statistics_from_table_data(elements, data_start_row)

            # Получаем номер продукта для нормативов
            selected_product = self.product_combo.currentText()
            try:
                pr_nmb = int(selected_product.split()[-1])
                normatives = self.get_normatives_from_db(pr_nmb)
            except:
                normatives = {}

            # Обновляем строки статистики
            self.update_statistics_rows(stats, elements, normatives, pr_nmb, data_start_row, self.table.rowCount())

    def update_statistics_rows(self, stats, elements, normatives, pr_nmb, data_start_row, total_rows):
        """Обновляет строки статистики без изменения структуры таблицы"""
        # Создаем жирный шрифт
        bold_font = QFont()
        bold_font.setBold(True)

        # Цвета для подсветки
        light_green = QColor(200, 255, 200)  # Светло-зеленый
        light_red = QColor(255, 200, 200)  # Светло-красный

        # Количество наблюдений для расчета F-критерия
        n = total_rows - data_start_row  # количество наблюдений
        if n < 2:
            n = 2  # минимальное значение для расчета СКО

        # Получаем табличное значение F
        f_critical = self.get_f_critical_value(n)

        for col_idx, element in enumerate(elements):
            element_num = col_idx + 1  # Номер элемента (начинается с 1)

            if element not in stats:
                # Если элемента нет в статистике, ставим прочерки
                col_base = 1 + col_idx * 4
                self.table.setItem(0, col_base, QTableWidgetItem("-"))  # Ср.расч
                self.table.setItem(0, col_base + 1, QTableWidgetItem("-"))  # С хим
                self.table.setItem(0, col_base + 2, QTableWidgetItem("-"))  # ΔC
                self.table.setItem(0, col_base + 3, QTableWidgetItem("-"))  # Отн.ΔC%

                self.table.setItem(1, col_base, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 2, QTableWidgetItem("-"))  # СКО ΔC
                self.table.setItem(1, col_base + 3, QTableWidgetItem("-"))  # СКО Отн.ΔC%

                self.table.setItem(3, col_base, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 2, QTableWidgetItem("-"))  # Вывод ΔC
                self.table.setItem(3, col_base + 3, QTableWidgetItem("-"))  # Вывод Отн.ΔC%
                continue

            element_stats = stats[element]
            col_base = 1 + col_idx * 4  # 1 - потому что первый столбец "Время цикла"

            # Получаем нормативы для текущего элемента и продукта
            normative_delta_c_01 = 0.0  # значение по умолчанию
            normative_delta_c_02 = 0.0  # значение по умолчанию

            if element_num in normatives:
                normative_delta_c_01, normative_delta_c_02 = normatives[element_num]

            # Проверяем достаточно ли данных для статистики (минимум 5 ненулевых С хим)
            if element_stats['valid_count'] < 5:
                # Недостаточно данных - ставим прочерки ВО ВСЕХ полях статистики
                self.table.setItem(0, col_base, QTableWidgetItem("-"))  # Ср.расч
                self.table.setItem(0, col_base + 1, QTableWidgetItem("-"))  # С хим
                self.table.setItem(0, col_base + 2, QTableWidgetItem("-"))  # ΔC
                self.table.setItem(0, col_base + 3, QTableWidgetItem("-"))  # Отн.ΔC%

                self.table.setItem(1, col_base, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 2, QTableWidgetItem("-"))  # СКО ΔC
                self.table.setItem(1, col_base + 3, QTableWidgetItem("-"))  # СКО Отн.ΔC%

                self.table.setItem(3, col_base, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 2, QTableWidgetItem("-"))  # Вывод ΔC
                self.table.setItem(3, col_base + 3, QTableWidgetItem("-"))  # Вывод Отн.ΔC%
                continue  # Переходим к следующему элементу

            # Остальной код без изменений...
            # Средние значения - считаем ТОЛЬКО по валидным данным (где С хим ≠ 0)
            if element_stats['calculated'] and element_stats['chemical']:
                avg_calc = statistics.mean(element_stats['calculated'])
                avg_chem = statistics.mean(element_stats['chemical'])
                avg_delta = statistics.mean(element_stats['deltas'])
                avg_relative = statistics.mean(element_stats['relative_deltas'])
            else:
                # Если нет валидных данных, ставим прочерки
                self.table.setItem(0, col_base, QTableWidgetItem("-"))
                self.table.setItem(0, col_base + 1, QTableWidgetItem("-"))
                self.table.setItem(0, col_base + 2, QTableWidgetItem("-"))
                self.table.setItem(0, col_base + 3, QTableWidgetItem("-"))

                self.table.setItem(1, col_base, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(1, col_base + 2, QTableWidgetItem("-"))
                self.table.setItem(1, col_base + 3, QTableWidgetItem("-"))

                self.table.setItem(3, col_base, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 1, QTableWidgetItem(""))
                self.table.setItem(3, col_base + 2, QTableWidgetItem("-"))
                self.table.setItem(3, col_base + 3, QTableWidgetItem("-"))
                continue

            # СКО - считаем ТОЛЬКО если есть хотя бы 2 валидных значения
            if len(element_stats['deltas']) > 1:
                std_delta = statistics.stdev(element_stats['deltas'])
                std_relative = statistics.stdev(element_stats['relative_deltas'])
            else:
                # Если недостаточно данных для СКО, ставим прочерки
                std_delta = 0
                std_relative = 0
                self.table.setItem(1, col_base + 2, QTableWidgetItem("-"))
                self.table.setItem(1, col_base + 3, QTableWidgetItem("-"))

            # Обновляем строку "Среднее" (строка 0) - только если есть данные
            self.table.setItem(0, col_base, QTableWidgetItem(f"{avg_calc:.6f}"))
            self.table.setItem(0, col_base + 1, QTableWidgetItem(f"{avg_chem:.6f}"))
            self.table.setItem(0, col_base + 2, QTableWidgetItem(f"{avg_delta:.6f}"))
            self.table.setItem(0, col_base + 3, QTableWidgetItem(f"{avg_relative:.1f}%"))

            # Обновляем строку "СКО" (строка 1) - только если рассчитано СКО
            self.table.setItem(1, col_base, QTableWidgetItem(""))
            self.table.setItem(1, col_base + 1, QTableWidgetItem(""))
            if len(element_stats['deltas']) > 1:
                self.table.setItem(1, col_base + 2, QTableWidgetItem(f"{std_delta:.6f}"))
                self.table.setItem(1, col_base + 3, QTableWidgetItem(f"{std_relative:.1f}%"))
            else:
                self.table.setItem(1, col_base + 2, QTableWidgetItem("-"))
                self.table.setItem(1, col_base + 3, QTableWidgetItem("-"))

            # Обновляем строку "Вывод" (строка 3) - только если можно рассчитать
            if len(element_stats['deltas']) <= 1 or normative_delta_c_01 == 0:
                # Недостаточно данных для вывода или нет норматива
                delta_status = "-"
                is_delta_ok = True
            else:
                # Вычисляем F-расчетное как (СКО / Норматив delta C)
                f_calculated = std_delta / normative_delta_c_01

                # F-расчетное < F-табличное => Норма
                if f_calculated < f_critical:
                    delta_status = "Норма"
                    is_delta_ok = True
                else:
                    delta_status = "Не норма"
                    is_delta_ok = False

            if len(element_stats['relative_deltas']) <= 1 or normative_delta_c_02 == 0:
                relative_status = "-"
                is_relative_ok = True
            else:
                is_relative_ok = std_relative <= normative_delta_c_02
                relative_status = "Норма" if is_relative_ok else "Не норма"

            delta_item = QTableWidgetItem(delta_status)
            relative_item = QTableWidgetItem(relative_status)

            # Подсветка вывода
            if is_delta_ok:
                delta_item.setBackground(light_green)
            else:
                delta_item.setBackground(light_red)

            if is_relative_ok:
                relative_item.setBackground(light_green)
            else:
                relative_item.setBackground(light_red)

            self.table.setItem(3, col_base, QTableWidgetItem(""))
            self.table.setItem(3, col_base + 1, QTableWidgetItem(""))
            self.table.setItem(3, col_base + 2, delta_item)
            self.table.setItem(3, col_base + 3, relative_item)

    def showEvent(self, event):
        """Обработчик события показа виджета"""
        super().showEvent(event)
        self.configure_table()

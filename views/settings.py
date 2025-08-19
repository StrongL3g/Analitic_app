# views/settings.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QSpinBox, QPushButton, QMessageBox, QGroupBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from database.db import Database
from config import get_config, set_config
import os


class SettingsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Настройки")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Группа настроек количества приборов ---
        devices_group = QGroupBox("Количество приборов")
        devices_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        devices_layout = QFormLayout()
        devices_layout.setLabelAlignment(Qt.AlignLeft)

        self.ac_count_spinbox = QSpinBox()
        self.ac_count_spinbox.setRange(1, 10)
        self.ac_count_spinbox.setValue(int(get_config("AC_COUNT", 1)))
        self.ac_count_spinbox.setSuffix(" прибор(ов)")

        apply_and_update_btn = QPushButton("Применить настройки и обновить БД")
        apply_and_update_btn.clicked.connect(self.apply_settings_and_update_db)
        apply_and_update_btn.setFixedWidth(300)

        devices_layout.addRow(QLabel("Количество приборов (1-10):"), self.ac_count_spinbox)
        devices_layout.addRow(QLabel(""), apply_and_update_btn)
        devices_group.setLayout(devices_layout)
        layout.addWidget(devices_group)

        # --- Информационная панель ---
        info_group = QGroupBox("Информация")
        info_layout = QVBoxLayout()
        info_label = QLabel(
            "<p><b>Важно:</b></p>"
            "<p>• При увеличении количества приборов будут созданы новые группы строк в таблицах SET02, SET03, SET04 и SET06</p>"
            "<p>• При уменьшении количества приборов группы с номерами больше нового значения будут удалены</p>"
            "<p>• Удаление групп данных необратимо!</p>"
            "<p>• Настройки применяются после перезапуска приложения или обновления соответствующих вкладок</p>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { background-color: #f9f9f9; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }")
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        layout.addStretch()
        self.setLayout(layout)

    def apply_settings_and_update_db(self):
        """Применяет новые настройки и обновляет группы в БД"""
        try:
            new_ac_count = self.ac_count_spinbox.value()
            old_ac_count = int(get_config("AC_COUNT", 1))

            if new_ac_count != old_ac_count:
                set_config("AC_COUNT", new_ac_count)
                QMessageBox.information(
                    self,
                    "Настройки сохранены",
                    f"Количество приборов изменено с {old_ac_count} на {new_ac_count}\n"
                    f"Настройки сохранены в файле .env."
                )
            else:
                QMessageBox.information(self, "Информация", "Количество приборов не изменилось")

            # Обновляем все таблицы
            self._update_db_groups_for_table("SET02", rows_per_group=21)
            self._update_db_groups_for_table("SET03", rows_per_group=40)
            self._update_db_groups_for_table("SET04", rows_per_group=1)  # 1 строка на прибор
            self._update_db_groups_for_table("SET06", rows_per_group=8)   # 8 строк на прибор

            QMessageBox.information(
                self,
                "Успех",
                f"Конфигурация для {new_ac_count} приборов успешно применена и группы в БД обновлены."
            )

        except Exception as e:
            error_msg = f"Ошибка при применении настроек и обновлении БД: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def _update_db_groups_for_table(self, table_name: str, rows_per_group: int):
        """Обновляет группы в указанной таблице БД"""
        try:
            ac_count = int(get_config("AC_COUNT", 1))

            # Проверяем/создаем базовую группу
            if not self._check_group_exists_in_table(table_name, 1):
                reply = QMessageBox.question(
                    self,
                    "Создать базовую группу",
                    f"Базовая группа данных для прибора 1 (ac_nmb = 1) в таблице {table_name} не существует. Создать её на основе шаблона?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    if table_name == "SET02":
                        success = self._create_base_group_set02()
                    elif table_name == "SET03":
                        success = self._create_base_group_set03()
                    elif table_name == "SET04":
                        success = self._create_base_group_set04()
                    elif table_name == "SET06":
                        success = self._create_base_group_set06()
                    else:
                        success = False

                    if success:
                        QMessageBox.information(self, "Успех", f"Базовая группа (ac_nmb = 1) в таблице {table_name} создана")
                    else:
                        QMessageBox.critical(self, "Ошибка", f"Не удалось создать базовую группу (ac_nmb = 1) в таблице {table_name}")
                        raise Exception(f"Не удалось создать базовую группу для {table_name}")
                else:
                    QMessageBox.warning(self, "Отмена", f"Операция отменена. Невозможно продолжить без базовой группы в {table_name}.")
                    raise Exception(f"Отмена создания базовой группы для {table_name}")

            # Создаем недостающие группы
            groups_created = []
            for ac_nmb in range(2, ac_count + 1):
                if not self._check_group_exists_in_table(table_name, ac_nmb):
                    if self._create_group_from_template(table_name, ac_nmb, template_ac_nmb=1, rows_per_group=rows_per_group):
                        groups_created.append(ac_nmb)
                    else:
                        QMessageBox.warning(self, "Предупреждение", f"Не удалось создать группу для прибора {ac_nmb} в таблице {table_name}")

            # Удаляем лишние группы
            groups_to_delete = []
            existing_groups = self._get_existing_groups_in_table(table_name)
            for ac_nmb in existing_groups:
                if ac_nmb > ac_count:
                     groups_to_delete.append(ac_nmb)

            groups_deleted = []
            if groups_to_delete:
                delete_list = ", ".join(map(str, groups_to_delete))
                reply = QMessageBox.question(
                    self,
                    "Подтверждение удаления",
                    f"Будут удалены группы данных для приборов: {delete_list} из таблицы {table_name}.\n"
                    f"Это действие необратимо!\nПродолжить?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    for ac_nmb in groups_to_delete:
                         if self._delete_group_from_table(table_name, ac_nmb):
                             groups_deleted.append(ac_nmb)
                         else:
                             QMessageBox.warning(self, "Ошибка", f"Не удалось удалить группу для прибора {ac_nmb} из таблице {table_name}")
                else:
                     QMessageBox.information(self, "Отмена", f"Удаление групп из таблицы {table_name} отменено.")

        except Exception as e:
            raise e

    # --- Вспомогательные методы для работы с БД ---

    def _check_group_exists_in_table(self, table_name: str, ac_nmb: int) -> bool:
        """Проверяет существование группы с указанным ac_nmb в таблице"""
        try:
            query = f"""
            SELECT COUNT(*) as cnt
            FROM [{self.db.database_name}].[dbo].[{table_name}]
            WHERE [ac_nmb] = ?
            """
            result = self.db.fetch_one(query, [ac_nmb])
            return result and result.get('cnt', 0) > 0
        except Exception as e:
            print(f"Ошибка при проверке существования группы ac_nmb={ac_nmb} в [{table_name}]: {e}")
            return False

    def _get_existing_groups_in_table(self, table_name: str) -> list:
        """Получает список существующих групп ac_nmb в таблице"""
        try:
            query = f"""
            SELECT DISTINCT [ac_nmb]
            FROM [{self.db.database_name}].[dbo].[{table_name}]
            WHERE [ac_nmb] IS NOT NULL
            ORDER BY [ac_nmb]
            """
            results = self.db.fetch_all(query)
            return [row['ac_nmb'] for row in results]
        except Exception as e:
            print(f"Ошибка при получении списка существующих групп в [{table_name}]: {e}")
            return []

    # --- Методы для создания базовых групп ---

    def _create_base_group_set02(self) -> bool:
        """Создает базовую группу (ac_nmb = 1) с 21 строкой в SET02"""
        try:
            insert_query = f"""
            INSERT INTO [{self.db.database_name}].[dbo].[SET02]
            ([ac_nmb], [sq_nmb], [ln_nmb], [ln_ch_min], [ln_ch_max])
            VALUES (?, ?, ?, ?, ?)
            """

            self.db.execute(insert_query, [1, 0, 0, 0.0, 0.0])

            for sq_nmb in range(1, 21):
                 self.db.execute(insert_query, [1, sq_nmb, -1, 0.0, 0.0])

            print(f"Базовая группа (ac_nmb=1) успешно создана в SET02")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовой группы в SET02: {e}"
            print(error_msg)
            return False

    def _create_base_group_set03(self) -> bool:
        """Создает базовую группу (ac_nmb = 1) с 40 строками в SET03"""
        try:
            insert_query = f"""
            INSERT INTO [{self.db.database_name}].[dbo].[SET03]
            ([ac_nmb], [sq_nmb], [ln_nmb], [k_nmb],
             [ln_01], [ln_02], [ln_03], [ln_04], [ln_05], [ln_06], [ln_07], [ln_08], [ln_09], [ln_10],
             [ln_11], [ln_12], [ln_13], [ln_14], [ln_15], [ln_16], [ln_17], [ln_18], [ln_19], [ln_20])
            VALUES (?, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """

            for sq_nmb in range(1, 21):
                params_k1 = [1, sq_nmb, -1, 1] + [0.0] * 20
                self.db.execute(insert_query, params_k1)
                params_k2 = [1, sq_nmb, -1, 2] + [0.0] * 20
                self.db.execute(insert_query, params_k2)

            print(f"Базовая группа (ac_nmb=1) успешно создана в SET03")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовой группы в SET03: {e}"
            print(error_msg)
            return False

    def _create_base_group_set04(self) -> bool:
        """Создает базовую группу (ac_nmb = 1) с 1 строкой в SET04"""
        try:
            insert_query = f"""
            INSERT INTO [{self.db.database_name}].[dbo].[SET04]
            ([ac_nmb], [current_00], [current_01], [current_02], [current_03], [current_04],
             [current_05], [current_06], [current_07], [current_08], [voltage_00], [voltage_01],
             [voltage_02], [voltage_03], [voltage_04], [voltage_05], [voltage_06], [voltage_07],
             [voltage_08], [time_00], [time_01], [time_02], [time_03], [time_04], [time_05],
             [time_06], [time_07], [time_08], [I_DEF], [I_B], [K_D_DEF], [SD])
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Значения по умолчанию (аналогично вашим данным)
            default_values = [
                1,  # ac_nmb
                30, 30, 30, 30, 30, 30, 30, 30, 30,  # current_00 - current_08
                35, 35, 35, 35, 35, 35, 35, 35, 35,  # voltage_00 - voltage_08
                10, 10, 10, 10, 10, 10, 10, 10, 10,  # time_00 - time_08
                5, 105430, 20, 2  # I_DEF, I_B, K_D_DEF, SD
            ]

            self.db.execute(insert_query, default_values)
            print(f"Базовая группа (ac_nmb=1) успешно создана в SET04")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовой группы в SET04: {e}"
            print(error_msg)
            return False

    def _create_base_group_set06(self) -> bool:
        """Создает базовую группу (ac_nmb = 1) с 8 строками в SET06"""
        try:
            insert_query = f"""
            INSERT INTO [{self.db.database_name}].[dbo].[SET06]
            ([ac_nmb], [sq_nmb], [ln_nmb], [ln_en], [ch_nmb])
            VALUES (?, ?, ?, ?, ?)
            """

            # Данные по умолчанию (аналогично вашим данным)
            default_data = [
                [1, 1, 17, 5.41, 656],
                [1, 2, 18, 5.95, 719],
                [1, 3, 21, 6.4, 776],
                [1, 4, 22, 7.06, 856],
                [1, 5, 25, 7.47, 907],
                [1, 6, 51, 17.43, 2120],
                [1, 7, 51, 17.43, 0],
                [1, 8, 55, 19.21, 0]
            ]

            for data in default_data:
                self.db.execute(insert_query, data)

            print(f"Базовая группа (ac_nmb=1) успешно создана в SET06")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовой группы в SET06: {e}"
            print(error_msg)
            return False

    def _create_group_from_template(self, table_name: str, ac_nmb: int, template_ac_nmb: int, rows_per_group: int) -> bool:
        """Создает новую группу, копируя структуру и данные из шаблонной группы"""
        try:
            if table_name == "SET02":
                select_fields = "[sq_nmb], [ln_nmb], [ln_ch_min], [ln_ch_max]"
                insert_fields = "([ac_nmb], [sq_nmb], [ln_nmb], [ln_ch_min], [ln_ch_max])"
                values_placeholder = "(?, ?, ?, ?, ?)"
            elif table_name == "SET03":
                select_fields = "[sq_nmb], [ln_nmb], [k_nmb], [ln_01], [ln_02], [ln_03], [ln_04], [ln_05], [ln_06], [ln_07], [ln_08], [ln_09], [ln_10], [ln_11], [ln_12], [ln_13], [ln_14], [ln_15], [ln_16], [ln_17], [ln_18], [ln_19], [ln_20]"
                insert_fields = "([ac_nmb], [sq_nmb], [ln_nmb], [k_nmb], [ln_01], [ln_02], [ln_03], [ln_04], [ln_05], [ln_06], [ln_07], [ln_08], [ln_09], [ln_10], [ln_11], [ln_12], [ln_13], [ln_14], [ln_15], [ln_16], [ln_17], [ln_18], [ln_19], [ln_20])"
                values_placeholder = "(?, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            elif table_name == "SET04":
                select_fields = "[current_00], [current_01], [current_02], [current_03], [current_04], [current_05], [current_06], [current_07], [current_08], [voltage_00], [voltage_01], [voltage_02], [voltage_03], [voltage_04], [voltage_05], [voltage_06], [voltage_07], [voltage_08], [time_00], [time_01], [time_02], [time_03], [time_04], [time_05], [time_06], [time_07], [time_08], [I_DEF], [I_B], [K_D_DEF], [SD]"
                insert_fields = "([ac_nmb], [current_00], [current_01], [current_02], [current_03], [current_04], [current_05], [current_06], [current_07], [current_08], [voltage_00], [voltage_01], [voltage_02], [voltage_03], [voltage_04], [voltage_05], [voltage_06], [voltage_07], [voltage_08], [time_00], [time_01], [time_02], [time_03], [time_04], [time_05], [time_06], [time_07], [time_08], [I_DEF], [I_B], [K_D_DEF], [SD])"
                values_placeholder = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            elif table_name == "SET06":
                select_fields = "[sq_nmb], [ln_nmb], [ln_en], [ch_nmb]"
                insert_fields = "([ac_nmb], [sq_nmb], [ln_nmb], [ln_en], [ch_nmb])"
                values_placeholder = "(?, ?, ?, ?, ?)"
            else:
                print(f"Неподдерживаемая таблица для копирования: {table_name}")
                return False

            select_query = f"""
            SELECT {select_fields}
            FROM [{self.db.database_name}].[dbo].[{table_name}]
            WHERE [ac_nmb] = ?
            ORDER BY [id]
            """
            template_rows = self.db.fetch_all(select_query, [template_ac_nmb])

            if not template_rows:
                print(f"Шаблонная группа (ac_nmb={template_ac_nmb}) в [{table_name}] пуста или не существует")
                return False

            insert_query = f"""
            INSERT INTO [{self.db.database_name}].[dbo].[{table_name}]
            {insert_fields}
            VALUES {values_placeholder}
            """

            for row in template_rows:
                values_list = [ac_nmb]

                if table_name == "SET02":
                    values_list.extend([
                        row['sq_nmb'], row['ln_nmb'],
                        row['ln_ch_min'], row['ln_ch_max']
                    ])
                elif table_name == "SET03":
                    values_list.extend([
                        row['sq_nmb'], row['ln_nmb'], row['k_nmb'],
                        row['ln_01'], row['ln_02'], row['ln_03'], row['ln_04'], row['ln_05'],
                        row['ln_06'], row['ln_07'], row['ln_08'], row['ln_09'], row['ln_10'],
                        row['ln_11'], row['ln_12'], row['ln_13'], row['ln_14'], row['ln_15'],
                        row['ln_16'], row['ln_17'], row['ln_18'], row['ln_19'], row['ln_20']
                    ])
                elif table_name == "SET04":
                    values_list.extend([
                        row['current_00'], row['current_01'], row['current_02'], row['current_03'],
                        row['current_04'], row['current_05'], row['current_06'], row['current_07'],
                        row['current_08'], row['voltage_00'], row['voltage_01'], row['voltage_02'],
                        row['voltage_03'], row['voltage_04'], row['voltage_05'], row['voltage_06'],
                        row['voltage_07'], row['voltage_08'], row['time_00'], row['time_01'],
                        row['time_02'], row['time_03'], row['time_04'], row['time_05'], row['time_06'],
                        row['time_07'], row['time_08'], row['I_DEF'], row['I_B'], row['K_D_DEF'], row['SD']
                    ])
                elif table_name == "SET06":
                    values_list.extend([
                        row['sq_nmb'], row['ln_nmb'], row['ln_en'], row['ch_nmb']
                    ])

                self.db.execute(insert_query, values_list)

            print(f"Группа (ac_nmb={ac_nmb}) успешно создана в [{table_name}] на основе шаблона (ac_nmb={template_ac_nmb})")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании группы (ac_nmb={ac_nmb}) в [{table_name}] из шаблона (ac_nmb={template_ac_nmb}): {e}"
            print(error_msg)
            return False

    def _delete_group_from_table(self, table_name: str, ac_nmb: int) -> bool:
        """Удаляет группу с указанным ac_nmb из таблицы"""
        try:
            delete_query = f"""
            DELETE FROM [{self.db.database_name}].[dbo].[{table_name}]
            WHERE [ac_nmb] = ?
            """
            self.db.execute(delete_query, [ac_nmb])
            print(f"Группа (ac_nmb={ac_nmb}) успешно удалена из [{table_name}]")
            return True
        except Exception as e:
            error_msg = f"Ошибка при удалении группы (ac_nmb={ac_nmb}) из [{table_name}]: {e}"
            print(error_msg)
            return False

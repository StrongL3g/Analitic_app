# views/settings.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QSpinBox, QPushButton, QMessageBox, QGroupBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from database.db import Database
from config import get_config, set_config, AC_COUNT, PR_COUNT
import os


class SettingsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()

    def init_ui(self):
        print(f"AC_COUNT: {AC_COUNT}, PR_COUNT: {PR_COUNT}")

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Настройки")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Группа настроек количества приборов и продуктов ---
        devices_group = QGroupBox("Количество приборов и продуктов")
        devices_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        devices_layout = QFormLayout()
        devices_layout.setLabelAlignment(Qt.AlignLeft)

        self.ac_count_spinbox = QSpinBox()
        self.ac_count_spinbox.setRange(1, 10)
        self.ac_count_spinbox.setValue(int(AC_COUNT))
        self.ac_count_spinbox.setSuffix(" прибор(ов)")

        self.pr_count_spinbox = QSpinBox()
        self.pr_count_spinbox.setRange(1, 10)
        self.pr_count_spinbox.setValue(int(PR_COUNT))
        self.pr_count_spinbox.setSuffix(" продукт(ов)")

        apply_and_update_btn = QPushButton("Применить настройки и обновить БД")
        apply_and_update_btn.clicked.connect(self.apply_settings_and_update_db)
        apply_and_update_btn.setFixedWidth(300)

        devices_layout.addRow(QLabel("Количество приборов (1-10):"), self.ac_count_spinbox)
        devices_layout.addRow(QLabel("Количество продуктов (1-10):"), self.pr_count_spinbox)
        devices_layout.addRow(QLabel(""), apply_and_update_btn)
        devices_group.setLayout(devices_layout)
        layout.addWidget(devices_group)

        # --- Информационная панель ---
        info_group = QGroupBox("Информация")
        info_layout = QVBoxLayout()
        info_label = QLabel(
            "<p><b>Важно:</b></p>"
            "<p>• При увеличении количества приборов/продуктов будут созданы новые группы строк в таблицах</p>"
            "<p>• При уменьшении количества приборов/продуктов группы с номерами больше нового значения будут удалены</p>"
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
            new_pr_count = self.pr_count_spinbox.value()

            old_ac_count = int(get_config("AC_COUNT", 1))
            old_pr_count = int(get_config("PR_COUNT", 1))

            print(new_ac_count)
            print(old_ac_count)

            print(new_pr_count)
            print(old_pr_count)

            # Обновляем SET00
            self._update_set00(new_ac_count, new_pr_count)

            if new_ac_count != old_ac_count:
                set_config("AC_COUNT", new_ac_count)
                # Обновляем таблицы для приборов
                self._update_db_groups_for_table("SET02", "ac_nmb", new_ac_count, rows_per_group=21)
                self._update_db_groups_for_table("SET03", "ac_nmb", new_ac_count, rows_per_group=40)
                self._update_db_groups_for_table("SET04", "ac_nmb", new_ac_count, rows_per_group=1)
                self._update_db_groups_for_table("SET06", "ac_nmb", new_ac_count, rows_per_group=8)
                # Обновляем cfg01 для приборов
                self._update_cfg01_groups(new_ac_count)

                QMessageBox.information(
                    self,
                    "Настройки сохранены",
                    f"Количество приборов изменено с {old_ac_count} на {new_ac_count}"
                )

            if new_pr_count != old_pr_count:
                set_config("PR_COUNT", new_pr_count)
                # Обновляем таблицы для продуктов
                self._update_db_groups_for_table("SET07", "pr_nmb", new_pr_count, rows_per_group=20)
                self._update_db_groups_for_table("PR_SET", "pr_nmb", new_pr_count, rows_per_group=24)
                # Обновляем set08 для продуктов
                self._update_set08_groups(new_pr_count)
                # Обновляем cfg02 для продуктов
                self._update_cfg02_groups(new_pr_count)

                QMessageBox.information(
                    self,
                    "Настройки сохранены",
                    f"Количество продуктов изменено с {old_pr_count} на {new_pr_count}"
                )

            QMessageBox.information(
                self,
                "Успех",
                f"Конфигурация для {new_ac_count} приборов и {new_pr_count} продуктов успешно применена."
            )

        except Exception as e:
            error_msg = f"Ошибка при применении настроек и обновлении БД: {e}"
            print(error_msg)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def _update_cfg01_groups(self, new_ac_count: int):
        """Обновляет группы приборов в таблице cfg01"""
        try:
            table_name = "cfg01"
            group_field = "ac_nmb"

            # Проверяем/создаём базовую группу (ac_nmb = 1), если её нет
            if not self._check_group_exists_in_table(table_name, group_field, 1):
                if self._create_base_group_cfg01():
                    print(f"Базовая группа (ac_nmb=1) создана в {table_name}")
                else:
                    raise Exception(f"Не удалось создать базовую группу для {table_name}")

            # Создаём недостающие группы (ac_nmb = 2..new_ac_count)
            groups_created = []
            for ac_nmb in range(2, new_ac_count + 1):
                if not self._check_group_exists_in_table(table_name, group_field, ac_nmb):
                    if self._create_cfg01_group_from_template(ac_nmb, template_ac_nmb=1):
                        groups_created.append(ac_nmb)
                    else:
                        QMessageBox.warning(self, "Предупреждение", f"Не удалось создать прибор {ac_nmb} в {table_name}")

            # Удаляем лишние группы (ac_nmb > new_ac_count)
            existing_groups = self._get_existing_groups_in_table(table_name, group_field)
            groups_to_delete = [g for g in existing_groups if g > new_ac_count]

            if groups_to_delete:
                delete_list = ", ".join(map(str, groups_to_delete))
                reply = QMessageBox.question(
                    self,
                    "Подтверждение удаления",
                    f"Будут удалены приборы: {delete_list} из таблицы {table_name}.\n"
                    f"Это действие необратимо!\nПродолжить?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    for ac_nmb in groups_to_delete:
                        if self._delete_group_from_table(table_name, group_field, ac_nmb):
                            print(f"Прибор {ac_nmb} удален из {table_name}")
                        else:
                            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить прибор {ac_nmb} из {table_name}")
                else:
                    QMessageBox.information(self, "Отмена", f"Удаление из {table_name} отменено.")

        except Exception as e:
            error_msg = f"Ошибка при обновлении cfg01: {e}"
            print(error_msg)
            raise e

    def _create_base_group_cfg01(self) -> bool:
        """Создает базовую группу приборов (ac_nmb = 1) в cfg01"""
        try:
            insert_query = """
            INSERT INTO cfg01
            (meas_nmb, cuv_nmb, pr_nmb, sp_nmb, ac_nmb)
            VALUES (?, ?, ?, ?, ?)
            """

            # Данные для базовой группы (ac_nmb = 1)
            base_data = [
                [101, 1, 1, 1, 1],
                [102, 2, 3, 2, 1],
                [103, 1, 1, 3, 1],
                [104, 2, 3, 4, 1],
                [105, 1, 1, 5, 1],
                [106, 2, 3, 6, 1],
                [107, 1, 1, 7, 1],
                [108, 2, 3, 8, 1]
            ]

            for data in base_data:
                self.db.execute(insert_query, data)

            print("Базовая группа приборов (ac_nmb=1) успешно создана в cfg01")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовой группы в cfg01: {e}"
            print(error_msg)
            return False

    def _create_cfg01_group_from_template(self, ac_nmb: int, template_ac_nmb: int = 1) -> bool:
        """Создает группу приборов в cfg01 на основе шаблона"""
        try:
            # Получаем данные из шаблонной группы
            select_query = """
            SELECT meas_nmb, cuv_nmb, pr_nmb, sp_nmb
            FROM cfg01
            WHERE ac_nmb = ?
            ORDER BY meas_nmb
            """
            template_rows = self.db.fetch_all(select_query, [template_ac_nmb])

            if not template_rows:
                print(f"Шаблонная группа (ac_nmb={template_ac_nmb}) в cfg01 не найдена")
                return False

            insert_query = """
            INSERT INTO cfg01
            (meas_nmb, cuv_nmb, pr_nmb, sp_nmb, ac_nmb)
            VALUES (?, ?, ?, ?, ?)
            """

            for row in template_rows:
                # Преобразуем meas_nmb: первая цифра становится номером прибора
                old_meas_nmb = row['meas_nmb']
                new_meas_nmb = int(str(ac_nmb) + str(old_meas_nmb)[1:])

                # cuv_nmb оставляем как в шаблоне, pr_nmb и sp_nmb ставим 0 для нового прибора
                new_cuv_nmb = row['cuv_nmb']
                new_pr_nmb = 0  # Для новых приборов ставим 0
                new_sp_nmb = 0  # Для новых приборов ставим 0

                self.db.execute(insert_query, [new_meas_nmb, new_cuv_nmb, new_pr_nmb, new_sp_nmb, ac_nmb])

            print(f"Группа приборов (ac_nmb={ac_nmb}) успешно создана в cfg01")
            return True

        except Exception as e:
            error_msg = f"Ошибка при создании группы приборов (ac_nmb={ac_nmb}) в cfg01: {e}"
            print(error_msg)
            return False

    def _update_cfg02_groups(self, new_pr_count: int):
        """Обновляет группы продуктов в таблице cfg02"""
        try:
            table_name = "cfg02"
            group_field = "pr_nmb"

            # Проверяем/создаём базовую группу (pr_nmb = 1), если её нет
            if not self._check_group_exists_in_table(table_name, group_field, 1):
                if self._create_base_group_cfg02():
                    print(f"Базовая группа (pr_nmb=1) создана в {table_name}")
                else:
                    raise Exception(f"Не удалось создать базовую группу для {table_name}")

            # Создаём недостающие группы (pr_nmb = 2..new_pr_count)
            groups_created = []
            for pr_nmb in range(2, new_pr_count + 1):
                if not self._check_group_exists_in_table(table_name, group_field, pr_nmb):
                    if self._create_cfg02_group(pr_nmb):
                        groups_created.append(pr_nmb)
                    else:
                        QMessageBox.warning(self, "Предупреждение", f"Не удалось создать продукт {pr_nmb} в {table_name}")

            # Удаляем лишние группы (pr_nmb > new_pr_count)
            existing_groups = self._get_existing_groups_in_table(table_name, group_field)
            groups_to_delete = [g for g in existing_groups if g > new_pr_count]

            if groups_to_delete:
                delete_list = ", ".join(map(str, groups_to_delete))
                reply = QMessageBox.question(
                    self,
                    "Подтверждение удаления",
                    f"Будут удалены продукты: {delete_list} из таблицы {table_name}.\n"
                    f"Это действие необратимо!\nПродолжить?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    for pr_nmb in groups_to_delete:
                        if self._delete_group_from_table(table_name, group_field, pr_nmb):
                            print(f"Продукт {pr_nmb} удален из {table_name}")
                        else:
                            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить продукт {pr_nmb} из {table_name}")
                else:
                    QMessageBox.information(self, "Отмена", f"Удаление из {table_name} отменено.")

        except Exception as e:
            error_msg = f"Ошибка при обновлении cfg02: {e}"
            print(error_msg)
            raise e

    def _create_base_group_cfg02(self) -> bool:
        """Создает базовые продукты в cfg02"""
        try:
            insert_query = """
            INSERT INTO cfg02
            (pr_nmb, pr_name, pr_desc)
            VALUES (?, ?, ?)
            """

            # Базовые продукты
            base_products = [
                [1, "Продукт №1", "Концентрат Ni-пирротиновый ТОФ"],
                [2, "Продукт №2", "Конц. коллект. флотации"],
                [3, "Продукт №3", "Тонкоизмельченные обороты из ЦПСиШ"],
                [4, "Продукт №4", "Хвост селективной флотации"],
                [5, "Продукт №5", "Конц. Cu флотации"],
                [6, "Продукт №6", "Конц. Mo перечистки"],
                [7, "Продукт №7", "Общие хвосты"],
                [8, "Продукт №8", "хвост Cu флотации"]
            ]

            for product in base_products:
                self.db.execute(insert_query, product)

            print("Базовые продукты успешно созданы в cfg02")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовых продуктов в cfg02: {e}"
            print(error_msg)
            return False

    def _create_cfg02_group(self, pr_nmb: int) -> bool:
        """Создает новый продукт в cfg02"""
        try:
            insert_query = """
            INSERT INTO cfg02
            (pr_nmb, pr_name, pr_desc)
            VALUES (?, ?, ?)
            """

            # Для новых продуктов используем стандартные названия и описание
            pr_name = f"Продукт №{pr_nmb}"
            pr_desc = "-"

            self.db.execute(insert_query, [pr_nmb, pr_name, pr_desc])

            print(f"Продукт {pr_nmb} успешно создан в cfg02")
            return True

        except Exception as e:
            error_msg = f"Ошибка при создании продукта {pr_nmb} в cfg02: {e}"
            print(error_msg)
            return False

    def _update_set08_groups(self, new_pr_count: int):
        """Обновляет группы продуктов в таблице SET08 (по 8 элементов на продукт, все delta = 0)"""
        try:
            table_name = "set08"
            group_field = "pr_nmb"

            # Проверяем/создаём базовую группу (pr_nmb = 1), если её нет
            if not self._check_group_exists_in_table(table_name, group_field, 1):
                reply = QMessageBox.question(
                    self,
                    "Создать базовую группу",
                    f"Базовая группа данных ({group_field}=1) в таблице {table_name} не существует. Создать её?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    if self._create_empty_group_set08(1):
                        QMessageBox.information(self, "Успех", f"Базовая группа ({group_field}=1) в таблице {table_name} создана")
                    else:
                        raise Exception(f"Не удалось создать базовую группу для {table_name}")
                else:
                    raise Exception(f"Отмена: базовая группа для {table_name} обязательна")

            # --- Создаём недостающие группы (pr_nmb = 2..new_pr_count) ---
            groups_created = []
            for pr_nmb in range(2, new_pr_count + 1):
                if not self._check_group_exists_in_table(table_name, group_field, pr_nmb):
                    if self._create_empty_group_set08(pr_nmb):
                        groups_created.append(pr_nmb)
                    else:
                        QMessageBox.warning(self, "Предупреждение", f"Не удалось создать продукт {pr_nmb} в {table_name}")

            # --- Удаляем лишние группы (pr_nmb > new_pr_count) ---
            existing_groups = self._get_existing_groups_in_table(table_name, group_field)
            groups_to_delete = [g for g in existing_groups if g > new_pr_count]

            if groups_to_delete:
                delete_list = ", ".join(map(str, groups_to_delete))
                reply = QMessageBox.question(
                    self,
                    "Подтверждение удаления",
                    f"Будут удалены продукты: {delete_list} из таблицы {table_name}.\n"
                    f"Это действие необратимо!\nПродолжить?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    for pr_nmb in groups_to_delete:
                        if self._delete_group_from_table(table_name, group_field, pr_nmb):
                            pass  # можно логгировать
                        else:
                            QMessageBox.warning(self, "Ошибка", f"Не удалось удалить продукт {pr_nmb} из {table_name}")
                else:
                    QMessageBox.information(self, "Отмена", f"Удаление из {table_name} отменено.")

        except Exception as e:
            error_msg = f"Ошибка при обновлении SET08: {e}"
            print(error_msg)
            raise e

    def _create_empty_group_set08(self, pr_nmb: int) -> bool:
        """Создаёт продукт в SET08 с 8 элементами, все delta_c_01 = delta_c_02 = 0.0"""
        try:
            insert_query = """
            INSERT INTO set08 (pr_nmb, el_nmb, delta_c_01, delta_c_02)
            VALUES (?, ?, ?, ?)
            """

            # Создаём 8 элементов: el_nmb = 1..8
            for el_nmb in range(1, 9):  # 1 to 8 inclusive
                self.db.execute(insert_query, [pr_nmb, el_nmb, 0.0, 0.0])

            print(f"Группа продукта (pr_nmb={pr_nmb}) успешно создана в SET08 (8 элементов, все delta = 0)")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании продукта {pr_nmb} в SET08: {e}"
            print(error_msg)
            return False

    def _update_set00(self, new_ac_count: int, new_pr_count: int):
        """Обновляет таблицу SET00 с новыми значениями"""
        try:
            # Проверяем существование записи
            check_query = f"""
            SELECT COUNT(*) as cnt
            FROM SET00
            """
            result = self.db.fetch_one(check_query)

            if result and result.get('cnt', 0) > 0:
                # Обновляем существующую запись
                update_query = f"""
                UPDATE SET00
                SET ac_nmb = ?, pr_nmb = ?
                """
                self.db.execute(update_query, [new_ac_count, new_pr_count])
            else:
                # Создаем новую запись
                insert_query = f"""
                INSERT INTO SET00
                (ac_nmb, pr_nmb)
                VALUES (?, ?)
                """
                self.db.execute(insert_query, [new_ac_count, new_pr_count])

            print(f"Таблица SET00 обновлена: ac_nmb={new_ac_count}, pr_nmb={new_pr_count}")

        except Exception as e:
            error_msg = f"Ошибка при обновлении SET00: {e}"
            print(error_msg)
            raise e

    def _update_db_groups_for_table(self, table_name: str, group_field: str, new_count: int, rows_per_group: int):
        """Обновляет группы в указанной таблице БД"""
        try:
            # Проверяем/создаем базовую группу
            if not self._check_group_exists_in_table(table_name, group_field, 1):
                reply = QMessageBox.question(
                    self,
                    "Создать базовую группу",
                    f"Базовая группа данных ({group_field}=1) в таблице {table_name} не существует. Создать её?",
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
                    elif table_name == "SET07":
                        success = self._create_base_group_set07()
                    elif table_name == "PR_SET":
                        success = self._create_base_group_pr_set()
                    else:
                        success = False

                    if success:
                        QMessageBox.information(self, "Успех", f"Базовая группа ({group_field}=1) в таблице {table_name} создана")
                    else:
                        QMessageBox.critical(self, "Ошибка", f"Не удалось создать базовую группу ({group_field}=1) в таблице {table_name}")
                        raise Exception(f"Не удалось создать базовую группу для {table_name}")
                else:
                    QMessageBox.warning(self, "Отмена", f"Операция отменена. Невозможно продолжить без базовой группы в {table_name}.")
                    raise Exception(f"Отмена создания базовой группы для {table_name}")

            # Создаем недостающие группы
            groups_created = []
            for group_nmb in range(2, new_count + 1):
                if not self._check_group_exists_in_table(table_name, group_field, group_nmb):
                    if self._create_group_from_template(table_name, group_field, group_nmb, template_group_nmb=1, rows_per_group=rows_per_group):
                        groups_created.append(group_nmb)
                    else:
                        QMessageBox.warning(self, "Предупреждение", f"Не удалось создать группу {group_field}={group_nmb} в таблице {table_name}")

            # Удаляем лишние группы
            groups_to_delete = []
            existing_groups = self._get_existing_groups_in_table(table_name, group_field)
            for group_nmb in existing_groups:
                if group_nmb > new_count:
                     groups_to_delete.append(group_nmb)

            groups_deleted = []
            if groups_to_delete:
                delete_list = ", ".join(map(str, groups_to_delete))
                reply = QMessageBox.question(
                    self,
                    "Подтверждение удаления",
                    f"Будут удалены группы данных {group_field}: {delete_list} из таблицы {table_name}.\n"
                    f"Это действие необратимо!\nПродолжить?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply == QMessageBox.Yes:
                    for group_nmb in groups_to_delete:
                         if self._delete_group_from_table(table_name, group_field, group_nmb):
                             groups_deleted.append(group_nmb)
                         else:
                             QMessageBox.warning(self, "Ошибка", f"Не удалось удалить группу {group_field}={group_nmb} из таблицы {table_name}")
                else:
                     QMessageBox.information(self, "Отмена", f"Удаление групп из таблицы {table_name} отменено.")

        except Exception as e:
            raise e

    # --- Вспомогательные методы для работы с БД ---

    def _check_group_exists_in_table(self, table_name: str, group_field: str, group_nmb: int) -> bool:
        """Проверяет существование группы с указанным номером в таблице"""
        try:
            query = f"""
            SELECT COUNT(*) as cnt
            FROM {table_name}
            WHERE {group_field} = ?
            """
            result = self.db.fetch_one(query, [group_nmb])
            return result and result.get('cnt', 0) > 0
        except Exception as e:
            print(f"Ошибка при проверке существования группы {group_field}={group_nmb} в [{table_name}]: {e}")
            return False

    def _get_existing_groups_in_table(self, table_name: str, group_field: str) -> list:
        """Получает список существующих групп в таблице"""
        try:
            query = f"""
            SELECT DISTINCT {group_field}
            FROM {table_name}
            WHERE {group_field} IS NOT NULL
            ORDER BY {group_field}
            """
            results = self.db.fetch_all(query)
            return [row[group_field] for row in results]
        except Exception as e:
            print(f"Ошибка при получении списка существующих групп в {table_name}: {e}")
            return []

    # --- Методы для создания базовых групп ---

    def _create_base_group_set02(self) -> bool:
        """Создает базовую группу (ac_nmb = 1) с 21 строкой в SET02"""
        try:
            insert_query = f"""
            INSERT INTO SET02
            (ac_nmb, sq_nmb, ln_nmb, ln_ch_min, ln_ch_max)
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
            INSERT INTO SET03
            (ac_nmb, sq_nmb, ln_nmb, k_nmb,
             ln_01, ln_02, ln_03, ln_04, ln_05, ln_06, ln_07, ln_08, ln_09, ln_10,
             ln_11, ln_12, ln_13, ln_14, ln_15, ln_16, ln_17, ln_18, ln_19, ln_20)
            VALUES (?, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """

            for sq_nmb in range(1, 21):
                params_k1 = [1, sq_nmb, -1, 1] + [0.0] * 20
                self.db.execute(insert_query, params_k1)
                params_k2 = [1, sq_nmb, -1, 2] + [0.0] * 20
                self.db.execute(insert_query, params_k2)

            print(f"Базовая группы (ac_nmb=1) успешно создана в SET03")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовой группы в SET03: {e}"
            print(error_msg)
            return False

    def _create_base_group_set04(self) -> bool:
        """Создает базовую группу (ac_nmb = 1) с 1 строкой в SET04"""
        try:
            insert_query = f"""
            INSERT INTO SET04
            (ac_nmb, current_00, current_01, current_02, current_03, current_04,
             current_05, current_06, current_07, current_08, voltage_00, voltage_01,
             voltage_02, voltage_03, voltage_04, voltage_05, voltage_06, voltage_07,
             voltage_08, time_00, time_01, time_02, time_03, time_04, time_05,
             time_06, time_07, time_08, i_def, i_b, k_d_def, sd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            # Значения по умолчанию
            default_values = [
                1,  # ac_nmb
                30, 30, 30, 30, 30, 30, 30, 30, 30,  # current_00 - current_08
                35, 35, 35, 35, 35, 35, 35, 35, 35,  # voltage_00 - voltage_08
                10, 10, 10, 10, 10, 10, 10, 10, 10,  # time_00 - time_08
                5, 105430, 20, 2  # i_def, i_b, k_d_def, sd
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
            INSERT INTO SET06
            (ac_nmb, sq_nmb, ln_nmb, ln_en, ch_nmb)
            VALUES (?, ?, ?, ?, ?)
            """

            # Данные по умолчанию
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

    def _create_base_group_set07(self) -> bool:
        """Создает базовую группу (pr_nmb = 1) с 20 строками в SET07"""
        try:
            insert_query = f"""
            INSERT INTO SET07
            (pr_nmb, sq_nmb, ln_nmb, i_min, i_max)
            VALUES (?, ?, ?, ?, ?)
            """

            # Берем значения из первого существующего продукта или используем значения по умолчанию
            template_query = f"""
            SELECT TOP 1 ln_nmb
            FROM SET07
            WHERE pr_nmb = 1
            ORDER BY sq_nmb
            """
            template_result = self.db.fetch_one(template_query)

            ln_nmb_default = -1  # Значение по умолчанию
            if template_result and 'ln_nmb' in template_result:
                ln_nmb_default = template_result['ln_nmb']

            for sq_nmb in range(1, 21):
                self.db.execute(insert_query, [1, sq_nmb, ln_nmb_default, 1, 1000000])

            print(f"Базовая группа (pr_nmb=1) успешно создана в SET07")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовой группы в SET07: {e}"
            print(error_msg)
            return False

    def _create_base_group_pr_set(self) -> bool:
        """Создает базовую группу (pr_nmb = 1) с 24 строками в PR_SET (3 модели × 8 элементов)"""
        try:
            insert_query = f"""
            INSERT INTO PR_SET
            (pr_nmb, mdl_nmb, active_model, el_nmb, meas_type, mdl_desc,
            k_i_alin00, k_c_alin00, k_i_alin01, k_c_alin01,
            operand_c_01_01, operand_c_02_01, operator_c_01,
            operand_i_01_01, operand_i_02_01, operator_i_01,
            k_i_alin02, k_c_alin02, operand_c_01_02, operand_c_02_02, operator_c_02,
            operand_i_01_02, operand_i_02_02, operator_i_02,
            k_i_alin03, k_c_alin03, operand_c_01_03, operand_c_02_03, operator_c_03,
            operand_i_01_03, operand_i_02_03, operator_i_03,
            k_i_alin04, k_c_alin04, operand_c_01_04, operand_c_02_04, operator_c_04,
            operand_i_01_04, operand_i_02_04, operator_i_04,
            k_i_alin05, k_c_alin05, operand_c_01_05, operand_c_02_05, operator_c_05,
            operand_i_01_05, operand_i_02_05, operator_i_05,
            k_i_klin00, k_c_klin00, k_i_klin01, k_c_klin01,
            c_min, c_max, water_crit, empty_crit, w_sq_nmb, e_sq_nmb, w_operator, e_operator)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            default_values = [
                0.0, 0.0, 0.0, 0.0,  # k_i_alin00, k_c_alin00, k_i_alin01, k_c_alin01
                0, 0, 0, 0, 0, 0,     # operand_c_01_01, operand_c_02_01, operator_c_01, operand_i_01_01, operand_i_02_01, operator_i_01
                0.0, 0.0, 0, 0, 0, 0, 0, 0,  # k_i_alin02, k_c_alin02, operand_c_01_02, operand_c_02_02, operator_c_02, operand_i_01_02, operand_i_02_02, operator_i_02
                0.0, 0.0, 0, 0, 0, 0, 0, 0,  # k_i_alin03, k_c_alin03, operand_c_01_03, operand_c_02_03, operator_c_03, operand_i_01_03, operand_i_02_03, operator_i_03
                0.0, 0.0, 0, 0, 0, 0, 0, 0,  # k_i_alin04, k_c_alin04, operand_c_01_04, operand_c_02_04, operator_c_04, operand_i_01_04, operand_i_02_04, operator_i_04
                0.0, 0.0, 0, 0, 0, 0, 0, 0,  # k_i_alin05, k_c_alin05, operand_c_01_05, operand_c_02_05, operator_c_05, operand_i_01_05, operand_i_02_05, operator_i_05
                0.0, 0.0, 0.0, 0.0,  # k_i_klin00, k_c_klin00, k_i_klin01, k_c_klin01
                0, 100, 40000, 5000, 3, 1, 1, 0  # c_min, c_max, water_crit, empty_crit, w_sq_nmb, e_sq_nmb, w_operator, e_operator
            ]

            for mdl_nmb in range(1, 4):  # 3 модели
                active_model = 1 if mdl_nmb == 1 else 0  # Активна только первая модель

                for el_nmb in range(1, 9):  # 8 элементов
                    params = [1, mdl_nmb, active_model, el_nmb, 0, "-"] + default_values
                    self.db.execute(insert_query, params)

            print(f"Базовая группа (pr_nmb=1) успешно создана в PR_SET")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовой группы в PR_SET: {e}"
            print(error_msg)
            return False

    def _create_group_from_template(self, table_name: str, group_field: str, group_nmb: int,
                                  template_group_nmb: int, rows_per_group: int) -> bool:
        """Создает новую группу, копируя структуру и данные из шаблонной группы"""
        try:
            if table_name == "SET02":
                select_fields = "sq_nmb, ln_nmb, ln_ch_min, ln_ch_max"
                insert_fields = "(ac_nmb, sq_nmb, ln_nmb, ln_ch_min, ln_ch_max)"
                values_placeholder = "(?, ?, ?, ?, ?)"
            elif table_name == "SET03":
                select_fields = "sq_nmb, ln_nmb, k_nmb, ln_01, ln_02, ln_03, ln_04, ln_05, ln_06, ln_07, ln_08, ln_09, ln_10, ln_11, ln_12, ln_13, ln_14, ln_15, ln_16, ln_17, ln_18, ln_19, ln_20"
                insert_fields = "(ac_nmb, sq_nmb, ln_nmb, k_nmb, ln_01, ln_02, ln_03, ln_04, ln_05, ln_06, ln_07, ln_08, ln_09, ln_10, ln_11, ln_12, ln_13, ln_14, ln_15, ln_16, ln_17, ln_18, ln_19, ln_20)"
                values_placeholder = "(?, ?, ?, ?, ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
            elif table_name == "SET04":
                select_fields = "current_00, current_01, current_02, current_03, current_04, current_05, current_06, current_07, current_08, voltage_00, voltage_01, voltage_02, voltage_03, voltage_04, voltage_05, voltage_06, voltage_07, voltage_08, time_00, time_01, time_02, time_03, time_04, time_05, time_06, time_07, time_08, i_def, i_b, k_d_def, sd"
                insert_fields = "(ac_nmb, current_00, current_01, current_02, current_03, current_04, current_05, current_06, current_07, current_08, voltage_00, voltage_01, voltage_02, voltage_03, voltage_04, voltage_05, voltage_06, voltage_07, voltage_08, time_00, time_01, time_02, time_03, time_04, time_05, time_06, time_07, time_08, i_def, i_b, k_d_def, sd)"
                values_placeholder = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            elif table_name == "SET06":
                select_fields = "sq_nmb, ln_nmb, ln_en, ch_nmb"
                insert_fields = "(ac_nmb, sq_nmb, ln_nmb, ln_en, ch_nmb)"
                values_placeholder = "(?, ?, ?, ?, ?)"
            elif table_name == "SET07":
                select_fields = "sq_nmb, ln_nmb, i_min, i_max"
                insert_fields = "(pr_nmb, sq_nmb, ln_nmb, i_min, i_max)"
                values_placeholder = "(?, ?, ?, ?, ?)"
            elif table_name == "PR_SET":
                # Более полный список полей с обработкой NULL значений
                select_fields = """
                mdl_nmb, active_model, el_nmb, meas_type, mdl_desc,
                k_i_alin00, k_c_alin00, k_i_alin01, k_c_alin01,
                operand_c_01_01, operand_c_02_01, operator_c_01,
                operand_i_01_01, operand_i_02_01, operator_i_01,
                k_i_alin02, k_c_alin02, operand_c_01_02, operand_c_02_02, operator_c_02,
                operand_i_01_02, operand_i_02_02, operator_i_02,
                k_i_alin03, k_c_alin03, operand_c_01_03, operand_c_02_03, operator_c_03,
                operand_i_01_03, operand_i_02_03, operator_i_03,
                k_i_alin04, k_c_alin04, operand_c_01_04, operand_c_02_04, operator_c_04,
                operand_i_01_04, operand_i_02_04, operator_i_04,
                k_i_alin05, k_c_alin05, operand_c_01_05, operand_c_02_05, operator_c_05,
                operand_i_01_05, operand_i_02_05, operator_i_05,
                k_i_klin00, k_c_klin00, k_i_klin01, k_c_klin01,
                c_min, c_max, water_crit, empty_crit, w_sq_nmb, e_sq_nmb, w_operator, e_operator
                """
                insert_fields = """
                (pr_nmb, mdl_nmb, active_model, el_nmb, meas_type, mdl_desc,
                k_i_alin00, k_c_alin00, k_i_alin01, k_c_alin01,
                operand_c_01_01, operand_c_02_01, operator_c_01,
                operand_i_01_01, operand_i_02_01, operator_i_01,
                k_i_alin02, k_c_alin02, operand_c_01_02, operand_c_02_02, operator_c_02,
                operand_i_01_02, operand_i_02_02, operator_i_02,
                k_i_alin03, k_c_alin03, operand_c_01_03, operand_c_02_03, operator_c_03,
                operand_i_01_03, operand_i_02_03, operator_i_03,
                k_i_alin04, k_c_alin04, operand_c_01_04, operand_c_02_04, operator_c_04,
                operand_i_01_04, operand_i_02_04, operator_i_04,
                k_i_alin05, k_c_alin05, operand_c_01_05, operand_c_02_05, operator_c_05,
                operand_i_01_05, operand_i_02_05, operator_i_05,
                k_i_klin00, k_c_klin00, k_i_klin01, k_c_klin01,
                c_min, c_max, water_crit, empty_crit, w_sq_nmb, e_sq_nmb, w_operator, e_operator)
                """
                values_placeholder = "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            else:
                print(f"Неподдерживаемая таблица для копирования: {table_name}")
                return False

            select_query = f"""
            SELECT {select_fields}
            FROM {table_name}
            WHERE {group_field} = ?
            ORDER BY id
            """
            template_rows = self.db.fetch_all(select_query, [template_group_nmb])

            if not template_rows:
                print(f"Шаблонная группа ({group_field}={template_group_nmb}) в [{table_name}] пуста или не существует")
                return False

            insert_query = f"""
            INSERT INTO {table_name}
            {insert_fields}
            VALUES {values_placeholder}
            """

            for row in template_rows:
                values_list = [group_nmb]  # Новый номер группы

                if table_name in ["SET02", "SET03", "SET04", "SET06"]:
                    # Для таблиц приборов копируем все поля
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
                            row['time_07'], row['time_08'], row['i_def'], row['i_b'], row['k_d_def'], row['sd']
                        ])
                    elif table_name == "SET06":
                        values_list.extend([
                            row['sq_nmb'], row['ln_nmb'], row['ln_en'], row['ch_nmb']
                        ])

                elif table_name == "SET07":
                    values_list.extend([
                        row['sq_nmb'], row['ln_nmb'], row['i_min'], row['i_max']
                    ])

                elif table_name == "PR_SET":
                    # Функция для безопасного получения значений с заменой NULL на 0
                    def get_value(key, default=0):
                        value = row.get(key)
                        return default if value is None else value

                    # Функция для строковых значений с заменой NULL на пустую строку
                    def get_str_value(key, default=""):
                        value = row.get(key)
                        return default if value is None else value

                    values_list.extend([
                        # Основные поля
                        get_value('mdl_nmb'),
                        get_value('active_model'),
                        get_value('el_nmb'),
                        get_value('meas_type'),
                        get_str_value('mdl_desc', '-'),

                        # Коэффициенты alin00-01
                        get_value('k_i_alin00', 0.0),
                        get_value('k_c_alin00', 0.0),
                        get_value('k_i_alin01', 0.0),
                        get_value('k_c_alin01', 0.0),

                        # Операторы 01
                        get_value('operand_c_01_01'),
                        get_value('operand_c_02_01'),
                        get_value('operator_c_01'),
                        get_value('operand_i_01_01'),
                        get_value('operand_i_02_01'),
                        get_value('operator_i_01'),

                        # Коэффициенты и операторы 02
                        get_value('k_i_alin02', 0.0),
                        get_value('k_c_alin02', 0.0),
                        get_value('operand_c_01_02'),
                        get_value('operand_c_02_02'),
                        get_value('operator_c_02'),
                        get_value('operand_i_01_02'),
                        get_value('operand_i_02_02'),
                        get_value('operator_i_02'),

                        # Коэффициенты и операторы 03
                        get_value('k_i_alin03', 0.0),
                        get_value('k_c_alin03', 0.0),
                        get_value('operand_c_01_03'),
                        get_value('operand_c_02_03'),
                        get_value('operator_c_03'),
                        get_value('operand_i_01_03'),
                        get_value('operand_i_02_03'),
                        get_value('operator_i_03'),

                        # Коэффициенты и операторы 04
                        get_value('k_i_alin04', 0.0),
                        get_value('k_c_alin04', 0.0),
                        get_value('operand_c_01_04'),
                        get_value('operand_c_02_04'),
                        get_value('operator_c_04'),
                        get_value('operand_i_01_04'),
                        get_value('operand_i_02_04'),
                        get_value('operator_i_04'),

                        # Коэффициенты и операторы 05
                        get_value('k_i_alin05', 0.0),
                        get_value('k_c_alin05', 0.0),
                        get_value('operand_c_01_05'),
                        get_value('operand_c_02_05'),
                        get_value('operator_c_05'),
                        get_value('operand_i_01_05'),
                        get_value('operand_i_02_05'),
                        get_value('operator_i_05'),

                        # Коэффициенты klin
                        get_value('k_i_klin00', 0.0),
                        get_value('k_c_klin00', 0.0),
                        get_value('k_i_klin01', 0.0),
                        get_value('k_c_klin01', 0.0),

                        # Критические значения
                        get_value('c_min', 0),
                        get_value('c_max', 100),
                        get_value('water_crit', 40000),
                        get_value('empty_crit', 5000),
                        get_value('w_sq_nmb', 3),
                        get_value('e_sq_nmb', 1),
                        get_value('w_operator', 1),
                        get_value('e_operator', 0)
                    ])

                self.db.execute(insert_query, values_list)

            print(f"Группа ({group_field}={group_nmb}) успешно создана в [{table_name}] на основе шаблона ({group_field}={template_group_nmb})")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании группы ({group_field}={group_nmb}) в [{table_name}] из шаблона ({group_field}={template_group_nmb}): {e}"
            print(error_msg)
            return False

    def _delete_group_from_table(self, table_name: str, group_field: str, group_nmb: int) -> bool:
        """Удаляет группу с указанным номером из таблицы"""
        try:
            delete_query = f"""
            DELETE FROM {table_name}
            WHERE {group_field} = ?
            """
            self.db.execute(delete_query, [group_nmb])
            print(f"Группа ({group_field}={group_nmb}) успешно удалена из [{table_name}]")
            return True
        except Exception as e:
            error_msg = f"Ошибка при удалении группы ({group_field}={group_nmb}) из [{table_name}]: {e}"
            print(error_msg)
            return False

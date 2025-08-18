# views/settings.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QSpinBox, QPushButton, QMessageBox, QGroupBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt
from database.db import Database
from config import get_config, set_config # Импортируем функции из config
import os


class SettingsPage(QWidget):
    def __init__(self, db: Database): # Принимаем db в конструкторе
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
        devices_group.setStyleSheet("QGroupBox { font-weight: bold; }") # Стиль для заголовка группы
        devices_layout = QFormLayout()
        devices_layout.setLabelAlignment(Qt.AlignLeft) # Выравнивание меток

        # Спинбокс для количества приборов
        self.ac_count_spinbox = QSpinBox()
        self.ac_count_spinbox.setRange(1, 10)  # Ограничение от

        # Загружаем текущее значение из config.py (который читает из .env)
        self.ac_count_spinbox.setValue(int(get_config("AC_COUNT", 1)))
        self.ac_count_spinbox.setSuffix(" прибор(ов)")

        # Кнопка применения настроек
        apply_settings_btn = QPushButton("Применить настройки")
        apply_settings_btn.clicked.connect(self.apply_settings)
        apply_settings_btn.setFixedWidth(180)

        # Кнопка обновления групп в БД
        update_db_btn = QPushButton("Обновить группы в БД")
        update_db_btn.clicked.connect(self.update_db_groups)
        update_db_btn.setFixedWidth(200)

        # Добавляем виджеты в форму настроек
        devices_layout.addRow(QLabel("Количество приборов (1-10):"), self.ac_count_spinbox)
        devices_layout.addRow(QLabel(""), apply_settings_btn) # Пустая метка для выравнивания
        devices_layout.addRow(QLabel(""), update_db_btn)

        devices_group.setLayout(devices_layout)
        layout.addWidget(devices_group)

        # --- Информационная панель ---
        info_group = QGroupBox("Информация")
        info_layout = QVBoxLayout()
        info_label = QLabel(
            "<p><b>Важно:</b></p>"
            "<p>• При увеличении количества приборов будут созданы новые группы строк в таблице SET02</p>"
            "<p>• При уменьшении количества приборов группы с номерами больше нового значения будут удалены</p>"
            "<p>• Удаление групп данных необратимо!</p>"
            "<p>• Настройки применяются после перезапуска приложения или обновления соответствующих вкладок</p>"
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { background-color: #f9f9f9; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }") # Стиль для информационного блока
        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # --- Отступ внизу ---
        layout.addStretch()

        self.setLayout(layout)

    def apply_settings(self):
        """Применяет новые настройки (сохраняет в .env)"""
        try:
            new_ac_count = self.ac_count_spinbox.value()
            old_ac_count = int(get_config("AC_COUNT", 1))

            if new_ac_count == old_ac_count:
                QMessageBox.information(self, "Информация", "Количество приборов не изменилось")
                return

            # Сохраняем новое значение в .env используя функцию из config.py
            set_config("AC_COUNT", new_ac_count)

            QMessageBox.information(
                self,
                "Успех",
                f"Количество приборов изменено с {old_ac_count} на {new_ac_count}\n"
                f"Настройки сохранены в файле .env.\n"
                f"Для полного применения изменений рекомендуется перезапустить приложение или обновить вкладки, работающие с данными приборов."
            )

        except Exception as e:
            error_msg = f"Ошибка при применении настроек: {e}"
            print(error_msg) # Логируем в консоль
            QMessageBox.critical(self, "Ошибка", error_msg)

    def update_db_groups(self):
        """Обновляет группы в БД в соответствии с настройками AC_COUNT"""
        try:
            # Получаем актуальное значение AC_COUNT из .env через config.py
            ac_count = int(get_config("AC_COUNT", 1))

            # --- 1. Проверяем/создаем базовую группу (ac_nmb = 1) ---
            if not self._check_group_exists(1):
                reply = QMessageBox.question(
                    self,
                    "Создать базовую группу",
                    "Базовая группа данных для прибора 1 (ac_nmb = 1) не существует. Создать её на основе шаблона?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes # По умолчанию "Да"
                )

                if reply == QMessageBox.Yes:
                    if self._create_base_group():
                        QMessageBox.information(self, "Успех", "Базовая группа (ac_nmb = 1) создана")
                    else:
                        QMessageBox.critical(self, "Ошибка", "Не удалось создать базовую группу (ac_nmb = 1)")
                        return # Прерываем процесс, если не смогли создать базовую группу
                else:
                    QMessageBox.warning(self, "Отмена", "Операция отменена. Невозможно продолжить без базовой группы.")
                    return

            # --- 2. Создаем недостающие группы (ac_nmb = 2 ... ac_count) ---
            groups_created = []
            for ac_nmb in range(2, ac_count + 1):
                if not self._check_group_exists(ac_nmb):
                    if self._create_group_from_template(ac_nmb, template_ac_nmb=1):
                        groups_created.append(ac_nmb)
                    else:
                        QMessageBox.warning(self, "Предупреждение", f"Не удалось создать группу для прибора {ac_nmb}")

            # --- 3. Удаляем лишние группы (ac_nmb > ac_count) ---
            groups_to_delete = []
            # Получаем список всех существующих групп
            existing_groups = self._get_existing_groups()
            for ac_nmb in existing_groups:
                if ac_nmb > ac_count:
                     groups_to_delete.append(ac_nmb)

            groups_deleted = []
            if groups_to_delete:
                # Формируем список для подтверждения
                delete_list = ", ".join(map(str, groups_to_delete))
                reply = QMessageBox.question(
                    self,
                    "Подтверждение удаления",
                    f"Будут удалены группы данных для приборов: {delete_list}.\n"
                    f"Это действие необратимо!\nПродолжить?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No # По умолчанию "Нет"
                )

                if reply == QMessageBox.Yes:
                    for ac_nmb in groups_to_delete:
                         if self._delete_group(ac_nmb):
                             groups_deleted.append(ac_nmb)
                         else:
                             QMessageBox.warning(self, "Ошибка", f"Не удалось удалить группу для прибора {ac_nmb}")
                else:
                     QMessageBox.information(self, "Отмена", "Удаление групп отменено.")

            # --- 4. Формируем итоговое сообщение ---
            messages = []
            if groups_created:
                messages.append(f"Созданы группы для приборов: {', '.join(map(str, groups_created))}")
            if groups_deleted:
                messages.append(f"Удалены группы для приборов: {', '.join(map(str, groups_deleted))}")

            if messages:
                QMessageBox.information(self, "Успех", "\n".join(messages))
            else:
                QMessageBox.information(self, "Информация", "Все группы БД соответствуют настройке количества приборов.")

        except Exception as e:
            error_msg = f"Ошибка при обновлении групп в БД: {e}"
            print(error_msg) # Логируем в консоль
            QMessageBox.critical(self, "Ошибка", error_msg)


    # --- Вспомогательные методы для работы с БД ---

    def _check_group_exists(self, ac_nmb: int) -> bool:
        """Проверяет существование группы с указанным ac_nmb"""
        try:
            query = f"""
            SELECT COUNT(*) as cnt
            FROM [{self.db.database_name}].[dbo].[SET02]
            WHERE [ac_nmb] = ?
            """
            # Предполагается, что fetch_one возвращает словарь
            result = self.db.fetch_one(query, [ac_nmb])
            return result and result.get('cnt', 0) > 0
        except Exception as e:
            print(f"Ошибка при проверке существования группы ac_nmb={ac_nmb}: {e}")
            return False # В случае ошибки считаем, что группа не существует

    def _get_existing_groups(self) -> list:
        """Получает список существующих групп ac_nmb"""
        try:
            query = f"""
            SELECT DISTINCT [ac_nmb]
            FROM [{self.db.database_name}].[dbo].[SET02]
            WHERE [ac_nmb] IS NOT NULL
            ORDER BY [ac_nmb]
            """
            results = self.db.fetch_all(query)
            return [row['ac_nmb'] for row in results]
        except Exception as e:
            print(f"Ошибка при получении списка существующих групп: {e}")
            return [] # В случае ошибки возвращаем пустой список

    def _create_base_group(self) -> bool:
        """Создает базовую группу (ac_nmb = 1) с 21 строкой"""
        try:
            # Создаем 21 строку для базовой группы (sq_nmb от 0 до 20)
            # Для sq_nmb=0: ln_nmb=0, для sq_nmb=1..20: ln_nmb=-1 (по логике из VBA)
            insert_query = f"""
            INSERT INTO [{self.db.database_name}].[dbo].[SET02]
            ([ac_nmb], [sq_nmb], [ln_nmb], [ln_ch_min], [ln_ch_max])
            VALUES (?, ?, ?, ?, ?)
            """

            # Вставляем строку sq_nmb=0
            self.db.execute(insert_query, [1, 0, 0, 0.0, 0.0])

            # Вставляем строки sq_nmb=1..20
            for sq_nmb in range(1, 21):
                 self.db.execute(insert_query, [1, sq_nmb, -1, 0.0, 0.0])

            print(f"Базовая группа (ac_nmb=1) успешно создана в [{self.db.database_name}].[dbo].[SET02]")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании базовой группы (ac_nmb=1): {e}"
            print(error_msg)
            return False

    def _create_group_from_template(self, ac_nmb: int, template_ac_nmb: int) -> bool:
        """Создает новую группу, копируя структуру и данные из шаблонной группы"""
        try:
            # 1. Получаем все строки из шаблонной группы
            select_query = f"""
            SELECT [sq_nmb], [ln_nmb], [ln_ch_min], [ln_ch_max]
            FROM [{self.db.database_name}].[dbo].[SET02]
            WHERE [ac_nmb] = ?
            ORDER BY [sq_nmb]
            """
            template_rows = self.db.fetch_all(select_query, [template_ac_nmb])

            if not template_rows:
                print(f"Шаблонная группа (ac_nmb={template_ac_nmb}) пуста или не существует")
                return False # Нечего копировать

            # 2. Вставляем скопированные строки с новым ac_nmb
            insert_query = f"""
            INSERT INTO [{self.db.database_name}].[dbo].[SET02]
            ([ac_nmb], [sq_nmb], [ln_nmb], [ln_ch_min], [ln_ch_max])
            VALUES (?, ?, ?, ?, ?)
            """

            for row in template_rows:
                self.db.execute(insert_query, [
                    ac_nmb,               # Новый ac_nmb
                    row['sq_nmb'],       # sq_nmb копируем как есть
                    row['ln_nmb'],       # ln_nmb копируем как есть
                    row['ln_ch_min'],    # ln_ch_min копируем как есть
                    row['ln_ch_max']     # ln_ch_max копируем как есть
                ])

            print(f"Группа (ac_nmb={ac_nmb}) успешно создана на основе шаблона (ac_nmb={template_ac_nmb})")
            return True
        except Exception as e:
            error_msg = f"Ошибка при создании группы (ac_nmb={ac_nmb}) из шаблона (ac_nmb={template_ac_nmb}): {e}"
            print(error_msg)
            return False

    def _delete_group(self, ac_nmb: int) -> bool:
        """Удаляет группу с указанным ac_nmb"""
        try:
            delete_query = f"""
            DELETE FROM [{self.db.database_name}].[dbo].[SET02]
            WHERE [ac_nmb] = ?
            """
            self.db.execute(delete_query, [ac_nmb])
            print(f"Группа (ac_nmb={ac_nmb}) успешно удалена из [{self.db.database_name}].[dbo].[SET02]")
            return True
        except Exception as e:
            error_msg = f"Ошибка при удалении группы (ac_nmb={ac_nmb}): {e}"
            print(error_msg)
            return False


# /home/astra/Analitic_app/services/alarm_manager.py
from collections import OrderedDict
from datetime import datetime
from PySide6.QtCore import QObject, Signal


class AlarmManager(QObject):
    alarms_updated = Signal(list)

    def __init__(self, db, alarm_config):
        super().__init__()
        self.db = db
        self.alarm_config = alarm_config
        self.active_alarms_live = OrderedDict()
        self.max_live_alarms = 500
        self._create_table_if_not_exists()

    def _create_table_if_not_exists(self):
        """Создает таблицу. Универсально для Postgres и MS SQL"""
        db_type = getattr(self.db, 'db_type', 'mssql')

        if db_type == 'postgres':
            query = """
            CREATE TABLE IF NOT EXISTS ac_alarms (
                id SERIAL PRIMARY KEY,
                tag_name TEXT,
                message TEXT,
                start_time TIMESTAMP,
                ack_time TIMESTAMP,
                end_time TIMESTAMP,
                is_active INTEGER DEFAULT 1,
                is_acked INTEGER DEFAULT 0
            )
            """
        else:
            # Синтаксис MS SQL
            query = """
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[ac_alarms]') AND type in (N'U'))
            BEGIN
                CREATE TABLE [dbo].[ac_alarms](
                    [id] [int] IDENTITY(1,1) PRIMARY KEY,
                    [tag_name] [nvarchar](max) NULL,
                    [message] [nvarchar](max) NULL,
                    [start_time] [datetime] NULL,
                    [ack_time] [datetime] NULL,
                    [end_time] [datetime] NULL,
                    [is_active] [int] DEFAULT 1,
                    [is_acked] [int] DEFAULT 0
                )
            END
            """
        try:
            self.db.execute(query)
            print(f"AlarmManager: Таблица ac_alarms проверена ({db_type}).")
        except Exception as e:
            print(f"AlarmManager: Ошибка при создании таблицы: {e}")

    def check_data(self, plc_data):
        """
        Универсальный метод проверки данных.
        Работает с объектами datetime для исключения ошибок конвертации nvarchar -> datetime.
        """
        changed = False
        for cfg in self.alarm_config:
            tag = cfg['tag']
            if tag not in plc_data:
                continue

            try:
                current_val = int(plc_data[tag])
                trigger_val = int(cfg['trigger_value'])
            except (ValueError, TypeError):
                continue

            is_alarm_active = (current_val == trigger_val)

            # 1. Новая авария
            if is_alarm_active and tag not in self.active_alarms_live:
                if len(self.active_alarms_live) >= self.max_live_alarms:
                    self.active_alarms_live.popitem(last=False)

                # ПОЛУЧАЕМ ОБЪЕКТ ВРЕМЕНИ (Универсально)
                now_obj = datetime.now()

                # Для UI храним строку, для БД передаем объект
                self.active_alarms_live[tag] = {
                    'tag': tag,
                    'message': cfg['message'],
                    'start_time': now_obj.strftime("%Y-%m-%d %H:%M:%S"),
                    'is_acked': 0,
                    'level': cfg.get('level', 2)
                }

                # В INSERT передаем кортеж с объектом datetime
                query = "INSERT INTO ac_alarms (tag_name, message, start_time, is_active, is_acked) VALUES (?, ?, ?, 1, 0)"
                self.db.execute(query, (tag, cfg['message'], now_obj))
                changed = True

            # 2. Авария ушла
            elif not is_alarm_active and tag in self.active_alarms_live:
                now_obj = datetime.now()
                del self.active_alarms_live[tag]

                # В UPDATE передаем объект datetime
                query = "UPDATE ac_alarms SET is_active = 0, end_time = ? WHERE tag_name = ? AND is_active = 1"
                self.db.execute(query, (now_obj, tag))
                changed = True

        if changed:
            self.alarms_updated.emit(list(self.active_alarms_live.values()))

    def acknowledge_all(self):
        """Квитирование всех активных аварий"""
        now_obj = datetime.now()
        for tag in self.active_alarms_live:
            self.active_alarms_live[tag]['is_acked'] = 1

        query = "UPDATE ac_alarms SET is_acked = 1, ack_time = ? WHERE is_acked = 0"
        try:
            self.db.execute(query, (now_obj,))
            self.alarms_updated.emit(list(self.active_alarms_live.values()))
        except Exception as e:
            print(f"AlarmManager: Ошибка квитирования: {e}")
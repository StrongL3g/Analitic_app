from PySide6.QtWidgets import (QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
                               QLabel, QGroupBox)
from PySide6.QtCore import Qt, Slot
from database.db import Database

class EMPage(QWidget):
    def __init__(self, db: Database, plc_worker):
        super().__init__()
        self.db = db
        self.plc_worker = plc_worker

        # Внутренние ключи теперь соответствуют именам в plc_tags
        self.ui_mapping = {
            # Кювета 1
            "cuv_01_flow": "var_di.cuv_01_flow_good.val",
            "cuv_01_rewind": "var_di.cuv_01_rewind.val",
            "ctank_01_level": "var_di.ctank_01_level.val",
            "tank_01_sample": "var_do.tank_01_sample.val",

            # Общие системы (МП и АК)
            "mp_air_good": "var_di.mp_air_good.val",
            "mp_water_good": "var_di.mp_water_good.val",
            "cpcu_door": "var_di.cpcu_door_closed.val",
            "emergency_stop": "var_di.emergency_stop.val",
            "ac_air_good": "var_di.ac_air_good.val",
            "accu_door": "var_di.accu_door_closed.val",
            "g1_good": "var_di.g1_good.val",
            "g2_good": "var_di.g2_good.val",

            # Кювета 2
            "cuv_02_flow": "var_di.cuv_02_flow_good.val",
            "cuv_02_rewind": "var_di.cuv_02_rewind.val",
            "ctank_02_level": "var_di.ctank_02_level.val",
            "tank_02_sample": "var_do.tank_02_sample.val",

            # Аналоговые сигналы
            "area_temp": "var_ai.meas_area_temperature.ff",
            "rfsu_temp": "var_ai.rfsu_temperature.ff"
        }

        self.labels = {}
        self.init_ui()

        if self.plc_worker:
            self.plc_worker.data_updated.connect(self.update_states)
            self.plc_worker.status_changed.connect(self.update_connection_status)

    def init_ui(self):
        self.main_layout = QVBoxLayout()
        top_grid = QGridLayout()

        self.group_style = """
            QGroupBox { 
                font-weight: bold; 
                border: 2px solid #555; 
                border-radius: 5px; 
                margin-top: 15px; 
            }
            QGroupBox::title { 
                subcontrol-origin: margin; 
                left: 10px; 
                padding: 0 5px;
                color: #222; 
            }
        """

        # Группировка элементов
        top_grid.addWidget(self.create_group("Статусы Кювета 1", [
            ("cuv_01_flow", "Проток пульпы (К1)"),
            ("cuv_01_rewind", "Перемотка пленки (К1)"),
            ("ctank_01_level", "Уровень в емкости 1"),
            ("tank_01_sample", "Пробоотбор 1")]), 0, 0)

        top_grid.addWidget(self.create_group("Статусы МП и АК", [
            ("mp_air_good", "Давление воздуха МП"),
            ("mp_water_good", "Давление воды МП"),
            ("cpcu_door", "Дверь ШУП"),
            ("emergency_stop", "АВАРИЙНЫЙ СТОП"),
            ("ac_air_good", "Давление воздуха АК"),
            ("accu_door", "Дверь ШУАК"),
            ("g1_good", "Блок питания G1"),
            ("g2_good", "Блок питания G2")]), 0, 1)

        top_grid.addWidget(self.create_group("Статусы Кювета 2", [
            ("cuv_02_flow", "Проток пульпы (К2)"),
            ("cuv_02_rewind", "Перемотка пленки (К2)"),
            ("ctank_02_level", "Уровень в емкости 2"),
            ("tank_02_sample", "Пробоотбор 2")]), 0, 2)

        top_grid.addWidget(self.create_temp_group("Температурный контроль", [
            ("area_temp", "Зона измерения"),
            ("rfsu_temp", "Внутри РФСУ")]), 1, 0, 1, 3)

        self.main_layout.addLayout(top_grid)

        self.conn_status = QLabel("СВЯЗЬ С ПЛК: ОЖИДАНИЕ ДАННЫХ...")
        self.conn_status.setStyleSheet("color: orange; font-weight: bold; padding: 10px; font-size: 14px;")
        self.main_layout.addStretch()
        self.main_layout.addWidget(self.conn_status)

        self.setLayout(self.main_layout)

    def create_group(self, title, items):
        group = QGroupBox(title)
        group.setStyleSheet(self.group_style)
        layout = QVBoxLayout()
        for ui_key, text in items:
            lbl = QLabel(f"• {text}")
            lbl.setStyleSheet("color: #777; font-size: 13px;")
            layout.addWidget(lbl)
            self.labels[ui_key] = lbl
        group.setLayout(layout)
        return group

    def create_temp_group(self, title, items):
        group = QGroupBox(title)
        group.setStyleSheet(self.group_style)
        layout = QHBoxLayout()
        for ui_key, text in items:
            container = QVBoxLayout()
            name_lbl = QLabel(text)
            name_lbl.setStyleSheet("font-weight: normal; color: #333;")
            val_lbl = QLabel("--.- °C")
            val_lbl.setStyleSheet("color: #008B8B; font-weight: bold; font-size: 22px;")
            container.addWidget(name_lbl)
            container.addWidget(val_lbl)
            layout.addLayout(container)
            layout.addStretch()
            self.labels[ui_key] = val_lbl
        group.setLayout(layout)
        return group

    @Slot(dict)
    def update_states(self, data):
        if "УСТАНОВЛЕНА" not in self.conn_status.text():
            self.update_connection_status(True)

        for ui_key, tag_name in self.ui_mapping.items():
            if tag_name in data:
                val = data[tag_name]
                label = self.labels.get(ui_key)
                if not label: continue

                if ui_key in ["area_temp", "rfsu_temp"]:
                    try:
                        temp_val = float(val)
                        label.setText(f"{temp_val:.1f} °C")
                        color = "#FF4500" if temp_val > 45 else "#008B8B"
                        label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 22px;")
                    except:
                        label.setText("???.? °C")
                else:
                    if int(val) == 1:
                        label.setStyleSheet(
                            "color: #00AA00; font-weight: bold; font-size: 13px; text-decoration: none;")
                    else:
                        label.setStyleSheet("color: #777; font-weight: normal; font-size: 13px; text-decoration: none;")

    @Slot(bool)
    def update_connection_status(self, connected):
        if connected:
            self.conn_status.setText("СВЯЗЬ С ПЛК: УСТАНОВЛЕНА")
            self.conn_status.setStyleSheet("color: #00AA00; font-weight: bold; padding: 10px; font-size: 14px;")
        else:
            self.conn_status.setText("СВЯЗЬ С ПЛК: РАЗОРВАНА (RECONNECT...)")
            self.conn_status.setStyleSheet("color: #FF0000; font-weight: bold; padding: 10px; font-size: 14px;")

            for ui_key, label in self.labels.items():
                if ui_key in ["area_temp", "rfsu_temp"]:
                    label.setText("--.- °C")
                    label.setStyleSheet("color: #444; font-weight: bold; font-size: 22px;")
                else:
                    label.setStyleSheet(
                        "color: #222; font-weight: normal; font-size: 13px; text-decoration: line-through;")
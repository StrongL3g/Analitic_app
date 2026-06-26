# /home/astra/Analitic_app/config/alarms_list.py
from plc.tags_list import plc_tags

# trigger_value: 0 если авария по False (разрыв цепи), 1 если по True
alarms = [
    {
        "tag": 'var_di.emergency_stop.val',
        "trigger_value": 0,
        "message": "Критическая авария: Нажата кнопка аварийного останова (ШУАК/ШУЦП)",
        "level": 1
    },
    {
        "tag": 'var_di.ac_ctrl_5vdc.val',
        "trigger_value": 0,
        "message": "Ошибка питания: Пропадание напряжения управления 5VDC",
        "level": 1
    },
    {
        "tag": 'var_di.g1_good.val',
        "trigger_value": 0,
        "message": "Неисправность блока питания G1",
        "level": 2
    },
    {
        "tag": 'var_di.g2_good.val',
        "trigger_value": 0,
        "message": "Неисправность блока питания G2",
        "level": 2
    },
    {
        "tag": 'var_di.mp_air_good.val',
        "trigger_value": 0,
        "message": "Низкое давление воздуха в измерительной системе",
        "level": 2
    },
    {
        "tag": 'var_di.mp_water_good.val',
        "trigger_value": 0,
        "message": "Ошибка системы охлаждения: Низкое давление воды",
        "level": 2
    },
    {
        "tag": 'var_di.accu_door_closed.val',
        "trigger_value": 0,
        "message": "Внимание: Открыта дверь шкафа ШУАК",
        "level": 3
    },
    {
        "tag": 'var_di.cpcu_door_closed.val',
        "trigger_value": 0,
        "message": "Внимание: Открыта дверь шкафа ШУЦП",
        "level": 3
    },
    {
        "tag": 'var_di.accu_temperature.val',
        "trigger_value": 1,
        "message": "Предупреждение: Перегрев внутри шкафа ШУАК",
        "level": 2
    },
    {
        "tag": 'var_di.rfsu_connect.val',
        "trigger_value": 0,
        "message": "Ошибка связи: Потеряно соединение с блоком RFSU",
        "level": 1
    }
]
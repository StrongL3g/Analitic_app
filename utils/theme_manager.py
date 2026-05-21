# utils/theme_manager.py
from config import load_app_config


def apply_application_theme(app_instance):
    config = load_app_config()
    theme_type = config.get("THEME", "Системная")

    # Общие стили для кнопок и списков, чтобы они не ломались
    base_controls = """
        QPushButton { 
            padding: 5px 10px; 
            border: 1px solid #999; 
            border-radius: 4px; 
        }
        QComboBox { 
            padding: 3px; 
            border: 1px solid #999; 
            border-radius: 3px; 
            selection-background-color: #2196F3;
        }
        QComboBox::drop-down { border: none; }
    """

    light_qss = base_controls + """
        QMainWindow, QWidget { background-color: #f5f5f5; color: #222222; }
        QCheckBox { color: #222222; }
        QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #999; background: white; }
        QCheckBox::indicator:checked { background: #2196F3; }
        QPushButton { background-color: #e0e0e0; }
        QComboBox { background-color: white; color: black; }
        QTabWidget::pane { border: 1px solid #cccccc; background: #ffffff; }
        QTabBar::tab { background: #e0e0e0; padding: 8px; border: 1px solid #cccccc; }
        QTabBar::tab:selected { background: #ffffff; }
    """

    dark_qss = base_controls + """
        QMainWindow, QWidget { background-color: #2b2b2b; color: #e0e0e0; }
        QCheckBox { color: #e0e0e0; }
        QCheckBox::indicator { width: 16px; height: 16px; border: 1px solid #555; background: #232323; }
        QCheckBox::indicator:checked { background: #1a4975; }
        QPushButton { background-color: #3c3f41; color: #e0e0e0; }
        QComboBox { background-color: #232323; color: #e0e0e0; border: 1px solid #555; }
        QTabWidget::pane { border: 1px solid #555; background: #232323; }
        QTabBar::tab { background: #383838; color: #e0e0e0; padding: 8px; border: 1px solid #555; }
        QTabBar::tab:selected { background: #232323; border-top: 2px solid #1a4975; }
    """

    if theme_type == "Тёмная":
        app_instance.setStyleSheet(dark_qss)
    elif theme_type == "Светлая":
        app_instance.setStyleSheet(light_qss)
    elif theme_type == "Кастомная":
        bg = config.get("CUSTOM_BG", "#ffffff")
        text = config.get("CUSTOM_TEXT", "#000000")
        accent = config.get("CUSTOM_ACCENT", "#2196F3")
        app_instance.setStyleSheet(f"""
            QWidget {{ background-color: {bg}; color: {text}; }}
            QPushButton {{ background-color: {accent}; color: white; border: none; }}
            QComboBox {{ background-color: {bg}; border: 1px solid {accent}; }}
            QCheckBox {{ color: {text}; }}
        """)
    else:
        app_instance.setStyleSheet("")
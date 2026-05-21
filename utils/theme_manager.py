# utils/theme_manager.py
from config import load_app_config


def apply_application_theme(app_instance):
    """
    Читает тему из config.json и накладывает глобальный QSS стиль на QApplication instance.
    Гарантирует читаемость всех элементов как на светлом, так и на тёмном мониторах.
    """
    config = load_app_config()
    theme_type = config.get("THEME", "Системная")

    # 1. СВЕТЛАЯ ТЕМА ПО УМОЛЧАНИЮ
    light_qss = """
        QMainWindow, QWidget { background-color: #f5f5f5; color: #222222; }
        QTableWidget { background-color: #ffffff; color: #222222; gridline-color: #d0d0d0; }
        QHeaderView::section { background-color: #e0e0e0; color: #222222; padding: 4px; border: 1px solid #d0d0d0; }
        QLineEdit, QComboBox, QSpinBox { background-color: #ffffff; color: #222222; border: 1px solid #cccccc; padding: 3px; border-radius: 3px; }
        QPushButton { background-color: #e0e0e0; color: #222222; border: 1px solid #b8b8b8; padding: 5px; border-radius: 4px; }
        QPushButton:hover { background-color: #d0d0d0; }
        QGroupBox { font-weight: bold; border: 1px solid #cccccc; border-radius: 6px; margin-top: 12px; padding-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
        QTreeWidget { background-color: #ffffff; color: #222222; }
    """

    # 2. ПОЛНОЦЕННАЯ ТЁМНАЯ ТЕМА
    dark_qss = """
        QMainWindow, QWidget { background-color: #2b2b2b; color: #e0e0e0; }
        QTableWidget { background-color: #232323; color: #e0e0e0; gridline-color: #3f3f3f; selection-background-color: #1a4975; }
        QHeaderView::section { background-color: #383838; color: #e0e0e0; padding: 4px; border: 1px solid #3f3f3f; }
        QLineEdit, QComboBox, QSpinBox { background-color: #232323; color: #e0e0e0; border: 1px solid #555555; padding: 3px; border-radius: 3px; }
        QComboBox QAbstractItemView { background-color: #232323; color: #e0e0e0; selection-background-color: #1a4975; }
        QPushButton { background-color: #3c3f41; color: #e0e0e0; border: 1px solid #555555; padding: 5px; border-radius: 4px; }
        QPushButton:hover { background-color: #4c4f51; }
        QGroupBox { font-weight: bold; border: 1px solid #555555; border-radius: 6px; margin-top: 12px; padding-top: 10px; color: #ffffff; }
        QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }
        QTreeWidget { background-color: #232323; color: #e0e0e0; }
        QTreeWidget::item:hover { background-color: #383838; }
        QTreeWidget::item:selected { background-color: #1a4975; color: #ffffff; }
    """

    if theme_type == "Тёмная":
        app_instance.setStyleSheet(dark_qss)
    elif theme_type == "Светлая":
        app_instance.setStyleSheet(light_qss)
    elif theme_type == "Кастомная":
        # Динамически собираем стиль из выбранных пользователем HEX-палитр
        bg = config.get("CUSTOM_BG", "#ffffff")
        text = config.get("CUSTOM_TEXT", "#000000")
        accent = config.get("CUSTOM_ACCENT", "#2196F3")

        custom_qss = f"""
            QMainWindow, QWidget {{ background-color: {bg}; color: {text}; }}
            QTableWidget {{ background-color: {bg}; color: {text}; gridline-color: {text}33; }}
            QHeaderView::section {{ background-color: {bg}; color: {text}; border: 1px solid {text}33; }}
            QLineEdit, QComboBox, QSpinBox {{ background-color: {bg}; color: {text}; border: 1px solid {accent}; border-radius: 3px; }}
            QPushButton {{ background-color: {accent}; color: #ffffff; border: none; padding: 5px; border-radius: 4px; font-weight: bold; }}
            QPushButton:hover {{ background-color: {accent}cc; }}
            QGroupBox {{ border: 1px solid {accent}; border-radius: 6px; margin-top: 12px; padding-top: 10px; }}
            QTreeWidget {{ background-color: {bg}; color: {text}; }}
        """
        app_instance.setStyleSheet(custom_qss)
    else:
        # "Системная" — очищаем кастомные стили, позволяя PySide6 использовать дефолт ОС
        app_instance.setStyleSheet("")
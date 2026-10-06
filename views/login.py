# views/login.py
import os
import platform

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QMessageBox, QComboBox
)
from PySide6.QtCore import Qt

# ============================================================
#  Определение платформы.
#  На Linux работаем через системные группы (pwd + grp),
#  на Windows — через fallback-словарь для отладки.
# ============================================================
IS_UNIX = platform.system() in ("Linux", "Darwin")

if IS_UNIX:
    import pwd
    import grp

# ============================================================
#  Соответствие "группа → роль".
#  Первая совпавшая группа выигрывает (порядок важен!).
# ============================================================
GROUP_ROLE_MAP = [
    ("lastadmin",    "Инженер-программист"),
    ("lastanalysts", "Аналитик"),
    ("lastguests",   "Гость"),
]

# ============================================================
#  Fallback-пользователи для отладки под Windows.
#  На Astra Linux этот блок не используется.
# ============================================================
DEV_USERS = {
    "Инженер":  {"password": "admin", "role": "Инженер-программист"},
    "Аналитик": {"password": "123",   "role": "Аналитик"},
    "Гость":    {"password": "guest", "role": "Гость"},
}


def get_system_user_info():
    """
    Возвращает (username, role) для текущего процесса на Unix.
    Если пользователь не входит ни в одну разрешённую группу —
    возвращает (username, None).
    Если ОС не Unix — возвращает (None, None).
    """
    if not IS_UNIX:
        return None, None

    uid = os.getuid()
    try:
        pwent = pwd.getpwuid(uid)
    except KeyError:
        return None, None

    username = pwent.pw_name

    # Собираем все группы пользователя: основную + дополнительные
    try:
        gids = os.getgrouplist(username, pwent.pw_gid)
    except Exception:
        gids = [pwent.pw_gid]

    groups = set()
    for gid in gids:
        try:
            groups.add(grp.getgrgid(gid).gr_name)
        except KeyError:
            continue

    for grp_name, role in GROUP_ROLE_MAP:
        if grp_name in groups:
            return username, role

    return username, None


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setFixedWidth(360)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint |
                            Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        self.user_role = None
        self.username = None

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Вход в систему")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        if IS_UNIX:
            self._init_unix(layout)
        else:
            self._init_dev(layout)

    # ---------- Linux: проверка системных групп ----------
    def _init_unix(self, layout):
        username, role = get_system_user_info()

        if username is None:
            QMessageBox.critical(
                self, "Ошибка",
                "Не удалось определить системного пользователя.\n"
                "Обратитесь к администратору системы."
            )
            self.reject()
            return

        info = QLabel(f"Пользователь: <b>{username}</b>")
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)

        if role is None:
            # Ни в одной из разрешённых групп
            msg = QLabel(
                "У вашей учётной записи нет прав для работы с приложением.<br><br>"
                "Разрешённые группы: "
                "<b>lastadmin</b>, <b>lastanalysts</b>, <b>lastguests</b>.<br><br>"
                "Обратитесь к администратору системы."
            )
            msg.setAlignment(Qt.AlignCenter)
            msg.setWordWrap(True)
            msg.setStyleSheet("color: #b91c1c;")
            layout.addWidget(msg)

            self.btn_login = QPushButton("Выход")
            self.btn_login.setFixedHeight(35)
            self.btn_login.clicked.connect(self.reject)
            layout.addWidget(self.btn_login)
            return

        role_lbl = QLabel(f"Роль: <b>{role}</b>")
        role_lbl.setAlignment(Qt.AlignCenter)
        role_lbl.setStyleSheet("color: #15803d;")
        layout.addWidget(role_lbl)

        self.username = username
        self.user_role = role

        self.btn_login = QPushButton("Войти")
        self.btn_login.setFixedHeight(35)
        self.btn_login.setDefault(True)
        self.btn_login.clicked.connect(self.accept)
        layout.addWidget(self.btn_login)

    # ---------- Windows: dev-режим ----------
    def _init_dev(self, layout):
        layout.addWidget(QLabel("Пользователь:"))
        self.combo_user = QComboBox()
        self.combo_user.addItems(DEV_USERS.keys())
        layout.addWidget(self.combo_user)

        layout.addWidget(QLabel("Пароль:"))
        self.line_password = QLineEdit()
        self.line_password.setEchoMode(QLineEdit.Password)
        self.line_password.returnPressed.connect(self.check_login)
        layout.addWidget(self.line_password)

        self.btn_login = QPushButton("Войти")
        self.btn_login.setFixedHeight(35)
        self.btn_login.clicked.connect(self.check_login)
        layout.addWidget(self.btn_login)

    def check_login(self):
        """Только для Windows (dev-режим)."""
        username = self.combo_user.currentText()
        password = self.line_password.text()

        entry = DEV_USERS.get(username)
        if not entry or entry["password"] != password:
            QMessageBox.warning(self, "Ошибка", "Неверный пароль!")
            self.line_password.clear()
            return

        self.username = username
        self.user_role = entry["role"]
        self.accept()
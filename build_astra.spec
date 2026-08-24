# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Убираем config/*.json, так как они будут создаваться при первом запуске
    ],
    hiddenimports=[
        'config',
        'database.db',
        'utils.helpers',
        'utils.path_manager',
        'views.dashboard',
        'views.logs',
        'views.settings',
        'views.users',
        'views.data.composition',
        'views.data.correction',
        'views.data.recalc',
        'views.data.regression',
        'views.data.report',
        'views.data.sample_dialog',
        'views.data.standards',
        'views.measurement.background',
        'views.measurement.criteria',
        'views.measurement.elements',
        'views.measurement.lines',
        'views.measurement.params',
        'views.measurement.ranges',
        'views.products.equations',
        'views.products.models',

        # --- Зависимости из requirements.txt ---
        'psycopg2._psycopg',
        'cryptography',
        'cryptography.fernet',
        'pyodbc',
        'asyncua',

        # === PySide6 (Вместо PyQt5) ===
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSql',       # Если используете работу с БД через Qt
        'PySide6.QtPrintSupport',
        'shiboken6',           # Критично для PySide6!
        'shiboken6.Shiboken',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Analitic_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,             # ⚠️ Отключаем UPX для режима "Максимальная защищенность" Astra Linux
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,         # Без консоли (GUI режим)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
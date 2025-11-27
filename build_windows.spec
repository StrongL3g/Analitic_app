a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('.env', '.'),
        ('config/*.json', 'config'),
        ('config/sample/*.json', 'config/sample'),
        ('views/data/*.py', 'views/data'),
        ('views/measurement/*.py', 'views/measurement'), 
        ('views/products/*.py', 'views/products'),
    ],
    hiddenimports=[
        'config',
        'database.db',
        'utils.helpers',
        'utils.path_manager',
        
        # Добавляем ВСЕ модули которые могут быть нужны
        'utils',  # ← ДОБАВЬ ЭТУ СТРОКУ
        'json',
        'os',
        'sys',
        'pathlib',
        
        # Все view модули
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
        
        # Дополнительные импорты для конфигов
        'dotenv',
        'python-dotenv',
        
        'psycopg2._psycopg',
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

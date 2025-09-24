# 📊 Аналитик

> Десктопное приложение для анализа и визуализации спектральных данных

Приложение **"Аналитика"** работает с базами данных **Microsoft SQL Server** и предоставляет удобный графический интерфейс для просмотра и анализа спектров. Написано на Python с использованием PySide6.

---

## 🔧 Установка Git

### Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install git -y
```

### Настройка пользователя
```bash
git config --global user.name "Ваше Имя"
git config --global user.email "ваша@почта.com"
```

### Генерация SSH-ключа
```bash
ssh-keygen -t ed25519 -C "ваша@почта.com"
```

### Запуск SSH-агента и добавление ключа
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

### Добавление ключа в GitHub
1. Выведите публичный ключ:
   ```bash
   cat ~/.ssh/id_ed25519.pub
   ```
2. Скопируйте вывод (всю строку).
3. Перейдите на [github.com/settings/keys](https://github.com/settings/keys).
4. Нажмите **New SSH Key**, вставьте ключ и сохраните.

### Проверка подключения
```bash
ssh -T git@github.com
```
✅ Успешный ответ:
```
Hi username! You've successfully authenticated, but GitHub does not provide shell access.
```

---

## 📦 Установка ODBC-драйвера для PostgreSQL

### Установка зависимостей

Это значит нужно установить библиотеку для PostgreSQL. Выполните в терминале:
```bash
pip install psycopg2-binary
```

---

## 📦 Установка ODBC-драйвера для MS SQL Server

Поддерживаемые версии Debian: **8, 9, 10, 11, 12, 13** (см. [официальный репозиторий](https://packages.microsoft.com/debian/)).

### Установка `lsb-release` (если не установлен)
```bash
sudo apt-get install -y lsb-release
```

### Добавление GPG-ключа Microsoft
```bash
curl -s https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft.gpg
```

### Добавление репозитория
```bash
echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/$(lsb_release -rs)/prod $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/mssql-release.list
```

### Установка драйвера
```bash
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
```

> ⚠️ Если возникает ошибка, связанная с отсутствием пакетов, убедитесь, что ваша версия ОС поддерживается. Например, для Debian 13 (trixie) репозиторий существует, но пакеты могут быть в процессе обновления.

---

## 🚀 Запуск приложения

### 1. Клонирование репозитория
```bash
git clone git@github.com:StrongL3g/Analitic_app.git
cd Analitic_app
```

### 2. Создание виртуального окружения
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Установка зависимостей
```bash
pip install --upgrade pip
pip install PySide6 pyodbc python-dotenv matplotlib
```

### 4. Настройка подключения к БД
```bash
cp .env.example .env
```

Отредактируйте файл `.env`:
```env
DB_TYPE=postgres

USERNAME=your_username
PASSWORD=your_password
```
тип базы выбирается именно в .env файле (postgres/mssql)
также нужно коментить/раскоментить нужные строки в зависимости от выбранной базы

### 5. Запуск приложения
```bash
python3 main.py
```

---

## ❗ Возможные проблемы и решения

| Проблема | Решение |
|--------|--------|
| `GPG error: invalid signature` | Убедитесь, что ключ добавлен через `gpg --dearmor` |
| `No such file or directory: /etc/apt/sources.list.d/mssql-release.list` | Проверьте права на запись или выполните команду через `sudo tee` |
| Не удаётся подключиться к SQL Server | Проверьте: порт 1433, firewall, включён ли TCP/IP в SQL Server, правильность логина/пароля |
| `Driver not loaded` | Убедитесь, что `msodbcsql18` установлен и доступен в системе |

---

## 🎯 Функционал приложения
- Подключение к MS SQL Server
- Загрузка данных о спектрах
- Визуализация графиков (matplotlib)
- Экспорт данных и изображений

---

✅ **Готово!** Приложение запущено и готово к использованию.

---

💡 **Подсказка**: Для автозапуска виртуального окружения можно добавить алиас в `~/.bashrc`:
```bash
alias analitic='cd /path/to/Analitic_app && source venv/bin/activate && python3 main.py'


## Анализатор спектров

Десктопное приложение Аналитика, работающее с MS SQL Server.

## Установка git

# Linux (Ubuntu/Debian)
	```bash
	sudo apt update && sudo apt install git -y

# Настройка git
	```bash
	git config --global user.name "Ваше Имя"
	git config --global user.email "ваша@почта.com"

# Создание SSH ключа
	```bash
	ssh-keygen -t ed25519 -C "ваша@почта.com"

# Добавление ключа
	```bash
	eval "$(ssh-agent -s)"  # запуск агента
	ssh-add ~/.ssh/id_ed25519  # добавление ключа

# Добавление SSH-ключа в GitHub
	```bash
	cat ~/.ssh/id_ed25519.pub

Копируйте всю строку
Добавьте ключ в GitHub
Откройте github.com/settings/keys
Нажмите New SSH Key
Вставьте скопированный ключ
Сохраните (Add SSH Key)

# проверка подключения
	```bash
	ssh -T git@github.com

должны увидеть "Hi username! You've successfully authenticated..."

## Установка репозитория

1. Установка odbc 
# Установка lsb-release (если нужно)
	```bash	
	sudo apt-get install -y lsb-release

# Добавление ключа
	```bash
	curl https://packages.microsoft.com/keys/microsoft.asc | sudo gpg --dearmor -o /usr/share/keyrings/microsoft.gpg

# Добавление репозитория
	```bash
	echo "deb [signed-by=/usr/share/keyrings/microsoft.gpg] https://packages.microsoft.com/debian/$(lsb_release -rs)/prod $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/mssql-release.list

# Установка драйвера
	``` bash	
	sudo apt-get update
	sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18

2. Клонируйте репозиторий:
   	```bash
   	git clone https://github.com/StrongL3g/Analitic_app.git


3. Активируйте виртуальное окружение:
	```bash
	python3 -m venv venv
	source venv/bin/activate	

4. Установите зависимости:
	```bash
	pip install PySide6 pyodbc python-dotenv matplotlib

5. Создайте .env
	```bash
	cp .env.example .env

6. Запустите:
	```bash
	python3 main.py

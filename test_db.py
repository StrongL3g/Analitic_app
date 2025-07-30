# test_db.py
from database.db import Database

def main():
    db = Database()
    try:
        query = "SELECT TOP 15 name FROM sys.tables"
        result = db.fetch_all(query)
        print("Подключение успешно.")
        print("Первые 5 таблиц в базе данных:")
        for row in result:
            print(row["name"])
    except Exception as e:
        print("Не удалось подключиться к базе данных.")
        print(str(e))

if __name__ == "__main__":
    main()

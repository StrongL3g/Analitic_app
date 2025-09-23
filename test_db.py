from database.db import Database
from config import DB_CONFIG

def test_postgres():
    try:
        db = Database(DB_CONFIG)

        # Простой тестовый запрос
        result = db.fetch_one("SELECT version() as version")
        if result:
            print("✅ Подключение к PostgreSQL успешно!")
            print(f"Версия PostgreSQL: {result['version']}")

        # Ваш запрос к таблице SET01
        query = """
        SELECT id, ln_nmb, ln_name, ln_en, ln_desc, ln_nc, ln_back
        FROM SET01
        ORDER BY ln_nmb
        """

        print("\n🔍 Запрос к таблице SET01:")
        print(query)

        data = db.fetch_all(query)

        if data:
            print(f"✅ Найдено записей: {len(data)}")
            print("\n📊 Первые 5 записей:")
            for i, row in enumerate(data[:5]):
                print(f"{i+1}. {row}")
        else:
            print("⚠ Таблица SET01 пуста или не найдена")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_postgres()

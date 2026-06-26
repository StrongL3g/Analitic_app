import asyncio
from asyncua import Client
import os


async def main():
    url = "opc.tcp://192.168.102.7:4840"
    client = Client(url=url)
    try:
        # Устанавливаем короткий таймаут для безопасности
        client.session_timeout = 30000

        async with client:
            print(f"--- Подключение к {url} ---")

            # Навигация к Variables (через Objects i=85)
            obj_node = client.get_node("i=85")

            # Поиск Application
            app_node = None
            for child in await obj_node.get_children():
                if (await child.read_browse_name()).Name == "Application":
                    app_node = child
                    break

            if not app_node:
                print("Папка Application не найдена")
                return

            # Поиск Variables
            vars_node = None
            for child in await app_node.get_children():
                if (await child.read_browse_name()).Name == "Variables":
                    vars_node = child
                    break

            if not vars_node:
                print("Папка Variables не найдена")
                return

            mapping = {}
            print("Сбор тегов...")
            for item in await vars_node.get_children():
                n_class = await item.read_node_class()
                if n_class.name == "Variable":
                    name = (await item.read_browse_name()).Name
                    raw_id = item.nodeid

                    # Фикс префикса: s для строк, i для чисел
                    prefix = "s" if isinstance(raw_id.Identifier, str) else "i"

                    mapping[name] = f"ns={raw_id.NamespaceIndex};{prefix}={raw_id.Identifier}"
                    print(f"  [OK] {name} -> {mapping[name]}")

            # Запись в файл
            if mapping:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                mapping_path = os.path.join(current_dir, "tags_list.py")
                with open(mapping_path, "w", encoding="utf-8") as f:
                    f.write("# Автоматически сгенерированный файл маппинга\n")
                    f.write("plc_tags = {\n")
                    for k, v in sorted(mapping.items()):
                        f.write(f"    '{k}': '{v}',\n")
                    f.write("}\n")
                print(f"\n--- УСПЕХ: Импортировано {len(mapping)} тегов ---")

    except Exception as e:
        print(f"Критическая ошибка при импорте: {e}")

    finally:
        # ГАРАНТИРОВАННОЕ ЗАКРЫТИЕ
        print("Завершение сессии импорта...")
        try:
            await client.disconnect()
            print("Сессия закрыта.")
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())
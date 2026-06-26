import asyncio
import socket
from PySide6.QtCore import QThread, Signal
from asyncua import Client
from .tags_list import plc_tags


class OPCUAWorker(QThread):
    """
    Фоновый воркер для связи с ПЛК Regul.
    Обеспечивает опрос тегов и автоматическое восстановление при перезагрузке ПЛК.
    """
    data_updated = Signal(dict)
    status_changed = Signal(bool)

    def __init__(self, endpoint="opc.tcp://192.168.102.7:4840"):
        super().__init__()
        self.endpoint = endpoint
        self._running = True
        self.client = Client(url=self.endpoint)

    def run(self):
        asyncio.run(self.main_loop())

    async def main_loop(self):
        while self._running:
            try:
                # Устанавливаем таймаут сессии (60 секунд для стабильности)
                self.client.session_timeout = 60000

                async with self.client:
                    # Проверяем, что сервер реально отвечает
                    await self.client.nodes.root.get_children()

                    self.status_changed.emit(True)
                    print(f"OPC UA: Подключено к {self.endpoint}")

                    nodes_cache = {}
                    for tag_name, address in plc_tags.items():
                        try:
                            nodes_cache[tag_name] = self.client.get_node(address)
                        except Exception as e:
                            print(f"Ошибка получения ноды {tag_name}: {e}")

                    while self._running:
                        current_data = {}
                        try:
                            for tag_name, node in nodes_cache.items():
                                val = await node.get_value()
                                current_data[tag_name] = val
                        except Exception as e:
                            # Если связь потеряна во время чтения — выходим на реконнект
                            print(f"OPC UA: Ошибка при чтении тегов (связь разорвана): {e}")
                            break

                        if current_data and self._running:
                            self.data_updated.emit(current_data)

                        await asyncio.sleep(1)

            except (asyncio.TimeoutError, socket.error, Exception) as e:
                self.status_changed.emit(False)
                # Выводим ошибку (включая BadTooManySessions)
                print(f"OPC UA Connection error: {e}")
                print("Чистка клиента и ожидание 15 сек перед реконнектом...")

                try:
                    # Пытаемся закрыть старую сессию, если она еще подает признаки жизни
                    await self.client.disconnect()
                except:
                    pass

                # Принудительно уничтожаем объект клиента
                self.client = None

                if self._running:
                    # Ждем подольше, чтобы ПЛК сбросил старые сессии по таймауту
                    await asyncio.sleep(15)
                    # Создаем новый экземпляр клиента для чистой попытки
                    self.client = Client(url=self.endpoint)

            finally:
                # Если воркер останавливается окончательно
                if not self._running and self.client:
                    try:
                        await self.client.disconnect()
                        print("OPC UA: Сессия закрыта корректно.")
                    except:
                        pass

    def stop(self):
        print("Запрос на остановку OPC UA воркера...")
        self._running = False
        # В Qt6/PySide6 лучше использовать quit() + wait()
        self.quit()
        self.wait()
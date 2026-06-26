import sys
import asyncio
import threading
import os
import re
from PySide6.QtWidgets import (QApplication, QMainWindow, QTreeView, QVBoxLayout,
                               QWidget, QSplitter, QTextEdit, QPushButton,
                               QMenu, QFileDialog)
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtCore import Qt, Signal, QObject, Slot
from asyncua import Client, ua


class Communication(QObject):
    add_node_sig = Signal(object, list)
    details_sig = Signal(str)


class OPCUABrowser(QMainWindow):
    def __init__(self, endpoint="opc.tcp://192.168.102.47:4840"):
        super().__init__()
        self.endpoint = endpoint
        self.comm = Communication()
        self.setWindowTitle(f"OPC UA Browser - {self.endpoint}")
        self.resize(1100, 700)

        # UI setup
        self.tree_view = QTreeView()
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Name", "Node ID", "Class"])
        self.tree_view.setModel(self.model)

        # Включаем контекстное меню для дерева (ПКМ)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self.show_context_menu)

        self.details_panel = QWidget()
        details_layout = QVBoxLayout(self.details_panel)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.copy_btn = QPushButton("Копировать NodeId")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self.copy_to_clipboard)

        details_layout.addWidget(self.log_view)
        details_layout.addWidget(self.copy_btn)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.tree_view)
        splitter.addWidget(self.details_panel)
        self.setCentralWidget(splitter)

        # Signals
        self.comm.add_node_sig.connect(self.add_node_to_ui)
        self.comm.details_sig.connect(self.log_view.setHtml)
        self.tree_view.expanded.connect(self.on_expanded)
        self.tree_view.clicked.connect(self.on_clicked)

        self.current_node_id = ""
        self.client = Client(url=self.endpoint)

        # Async Loop
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, args=(self.loop,), daemon=True)
        self.thread.start()

        asyncio.run_coroutine_threadsafe(self.connect_server(), self.loop)

    def run_async_loop(self, loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()

    async def connect_server(self):
        try:
            self.client.session_timeout = 30000
            await self.client.connect()
            root = self.client.get_root_node()
            name = (await root.read_browse_name()).Name
            self.loop.call_soon_threadsafe(self.safe_append, self.model.invisibleRootItem(),
                                           self.create_row_data(root, name, "Object"))
        except Exception as e:
            self.comm.details_sig.emit(f"<span style='color:red'>Ошибка подключения: {e}</span><br>"
                                       f"<i>Попробуйте подождать 1-2 минуты, пока ПЛК закроет старые сессии.</i>")

    def create_row_data(self, node, name, n_class):
        name_item = QStandardItem(name)
        name_item.setData(node, Qt.UserRole)
        id_item = QStandardItem(str(node.nodeid))
        class_item = QStandardItem(n_class)
        if n_class != "Variable":
            name_item.appendRow(QStandardItem("Loading..."))
        return [name_item, id_item, class_item]

    def safe_append(self, parent, rows):
        parent.appendRow(rows)

    @Slot(object, list)
    def add_node_to_ui(self, parent_item, rows):
        parent_item.appendRow(rows)

    def on_expanded(self, index):
        item = self.model.itemFromIndex(index)
        if item.rowCount() == 1 and item.child(0).text() == "Loading...":
            item.removeRow(0)
            node = item.data(Qt.UserRole)
            asyncio.run_coroutine_threadsafe(self.load_children(item, node), self.loop)

    async def load_children(self, parent_item, node):
        try:
            children = await node.get_children()
            for child in children:
                name = (await child.read_browse_name()).Name
                n_class = (await child.read_node_class()).name
                rows = self.create_row_data(child, name, n_class)
                self.loop.call_soon_threadsafe(self.safe_append, parent_item, rows)
        except:
            pass

    def on_clicked(self, index):
        item = self.model.itemFromIndex(index.siblingAtColumn(0))
        node = item.data(Qt.UserRole)
        self.current_node_id = item.sibling(index.row(), 1).text()
        self.copy_btn.setEnabled(True)
        asyncio.run_coroutine_threadsafe(self.show_details(node), self.loop)

    # --- Контекстное меню и чистый Текстовый Экспорт ---
    def show_context_menu(self, position):
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return

        menu = QMenu()
        export_action = menu.addAction("Экспорт дочерних переменных в CSV")
        action = menu.exec(self.tree_view.viewport().mapToGlobal(position))

        if action == export_action:
            item = self.model.itemFromIndex(index.siblingAtColumn(0))
            node = item.data(Qt.UserRole)
            self.start_csv_export(node)

    def start_csv_export(self, node):
        # Автоматический путь в домашнюю директорию пользователя Astra Linux
        default_dir = os.path.expanduser("~")
        default_path = os.path.join(default_dir, "tags.csv")

        filepath, _ = QFileDialog.getSaveFileName(self, "Сохранить CSV", default_path, "CSV Files (*.csv)")
        if filepath:
            self.comm.details_sig.emit("<b>Начат сбор данных для экспорта, пожалуйста, подождите...</b>")
            asyncio.run_coroutine_threadsafe(self.process_csv_export(node, filepath), self.loop)

    async def process_csv_export(self, node, filepath):
        try:
            children = await node.get_children()
            count = 0

            # Пишем напрямую как текст, чтобы полностью исключить появление кавычек
            with open(filepath, 'w', encoding='utf-8') as f:
                for child in children:
                    n_class = await child.read_node_class()
                    if n_class == ua.NodeClass.Variable:
                        raw_id = str(child.nodeid)

                        # Форматируем ID в требуемый вид ns=X;s=Tag_Name
                        if "NamespaceIndex=" in raw_id:
                            ns_match = re.search(r"NamespaceIndex=(\d+)", raw_id)
                            id_match = re.search(r"Identifier=([^,\s\)]+)", raw_id)
                            if ns_match and id_match:
                                ns = ns_match.group(1)
                                ident = id_match.group(1)
                                prefix = "i" if ident.isdigit() else "s"
                                formatted_id = f"ns={ns};{prefix}={ident}"
                            else:
                                formatted_id = raw_id
                        else:
                            formatted_id = raw_id.replace("NodeId(", "").replace(")", "")

                        # Записываем чистую строку и добавляем перенос строки \n
                        f.write(f"{formatted_id}\n")
                        count += 1

            self.comm.details_sig.emit(
                f"<span style='color:green'><b>Экспорт успешно завершен!</b><br>Сохранено переменных: {count}<br>Файл: {filepath}</span>")
        except Exception as e:
            self.comm.details_sig.emit(f"<span style='color:red'><b>Ошибка экспорта:</b> {e}</span>")

    async def show_details(self, node):
        try:
            n_class = await node.read_node_class()
            val = await node.read_value() if n_class == ua.NodeClass.Variable else "-"
            name = (await node.read_browse_name()).Name
            html = (f"<h3>Детали узла</h3>"
                    f"<b>Имя:</b> {name}<br>"
                    f"<b>ID:</b> {node.nodeid}<br>"
                    f"<b>Класс:</b> {n_class.name}<br>"
                    f"<b>Значение:</b> <span style='color:green'>{val}</span>")
            self.comm.details_sig.emit(html)
        except:
            self.comm.details_sig.emit("Не удалось прочитать данные узла.")

    def copy_to_clipboard(self):
        if self.current_node_id:
            raw = self.current_node_id
            if "NamespaceIndex=" in raw:
                ns_match = re.search(r"NamespaceIndex=(\d+)", raw)
                id_match = re.search(r"Identifier=([^,\s\)]+)", raw)
                if ns_match and id_match:
                    ns = ns_match.group(1)
                    ident = id_match.group(1)
                    prefix = "i" if ident.isdigit() else "s"
                    formatted_id = f"ns={ns};{prefix}={ident}"
                else:
                    formatted_id = raw
            else:
                formatted_id = raw.replace("NodeId(", "").replace(")", "")

            QApplication.clipboard().setText(formatted_id)
            self.copy_btn.setText("Скопировано!")
            threading.Timer(1.5, lambda: self.copy_btn.setText("Копировать NodeId")).start()

    def closeEvent(self, event):
        print("Закрытие сессии OPC UA...")
        asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
        self.loop.call_soon_threadsafe(self.loop.stop)
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OPCUABrowser()
    window.show()
    sys.exit(app.exec())
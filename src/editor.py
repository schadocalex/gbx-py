import datetime
import os
import sys
from collections import OrderedDict
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTextEdit,
    QFileDialog,
)
from PySide6.QtCore import Slot, QSize, Qt
from PySide6.QtGui import QTextCursor

from .gbx_structs import GbxPose3D, GbxStruct, GbxStructWithoutBodyParsed, NodeRef
from construct import (
    Container,
    ListContainer,
    RawCopy,
    Struct,
    Adapter,
    Subconstruct,
)

from .widgets.hex_editor import GbxHexEditor
from .widgets.inspector import Inspector


def container_iter(ctn):
    for key, value in ctn.items():
        if key != "_io":
            yield key, value


class QTreeWidgetItem_WithData(QTreeWidgetItem):
    def __init__(self, data, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.gbx_data = data


def tree_widget_item(key, value):
    if isinstance(value, NodeRef):
        if value._index == -1:
            return QTreeWidgetItem_WithData(
                Container(type=type(value).__name__, value=value),
                [key, "NodeRef", "-1"],
            )

        item = QTreeWidgetItem([key, f"NodeRef"])
        for child in container_iter(value):
            item.addChild(tree_widget_item(*child))

        return item
    if isinstance(value, Container):
        item = QTreeWidgetItem([key])
        for child in container_iter(value):
            item.addChild(tree_widget_item(*child))

        return item
    elif isinstance(value, ListContainer) or isinstance(value, list):
        item = QTreeWidgetItem([key, f"Array({len(value)})"])

        for i, child in enumerate(value):
            item.addChild(tree_widget_item(str(i), child))

        return item
    elif isinstance(value, OrderedDict):  # assume it is body for now
        item = QTreeWidgetItem([key, f"Body({len(value)})"])

        for chunkId, child in value.items():
            item.addChild(tree_widget_item(chunkId if isinstance(chunkId, str) else str(hex(chunkId)), child))

        return item
    elif type(value).__name__ == "bytes":
        return QTreeWidgetItem_WithData(
            Container(type=type(value).__name__, value=value),
            [
                key,
                type(value).__name__,
                str(value[:12]) + ("..." if len(value) > 12 else ""),
            ],
        )
    else:
        return QTreeWidgetItem_WithData(
            Container(type=type(value).__name__, value=value),
            [key, type(value).__name__, str(value)],
        )


def expand_items(top_level_item):
    return


class GbxEditorUiWindow(QMainWindow):
    def __init__(self, callback_file=None, default_directory=None) -> None:
        QMainWindow.__init__(self)

        self.resize(QSize(1600, 1000))

        # widgets

        self.inspector = Inspector()

        self.hex_editor = GbxHexEditor(self._on_select)

        self.tree = QTreeWidget()

        # layout

        layout_v = QVBoxLayout()
        layout_v.addWidget(self.hex_editor)
        layout_v.addWidget(self.inspector)

        layout_h = QHBoxLayout()
        layout_h.addWidget(self.tree)
        layout_h.addLayout(layout_v)

        widget = QWidget()
        widget.setLayout(layout_h)
        self.setCentralWidget(widget)

        # file dialog

        if callback_file is not None:
            self.callback_file = callback_file
            button = QPushButton("Open file", self)
            button.clicked.connect(self.on_file_clicked)
            layout_v.addWidget(button)
            self.dialog = QFileDialog(self)
            self.dialog.setNameFilter("Gbx Files (*.gbx *.Gbx)")
            self.dialog.fileSelected.connect(self.on_file_selected)
            if default_directory is not None:
                self.dialog.setDirectory(default_directory)

        self.show()

    def set_data(self, parsed_data):
        self._setDataOnTree(parsed_data)

    @Slot()
    def on_file_clicked(self) -> None:
        self.dialog.open()

    @Slot()
    def on_file_selected(self) -> None:
        for path in self.dialog.selectedFiles():
            self.dialog.setDirectory(os.path.dirname(path))
            self.callback_file(path)

    def _on_select(self, raw_bytes, selection):
        self.inspector.inspect(raw_bytes, selection)

    def _on_item_select(self, new_bytes):
        self.hex_editor.set_bytes(new_bytes)
        self.inspector.inspect(new_bytes, [])

    def _setDataOnTree(self, data):
        tree = self.tree
        tree.clear()
        tree.setColumnCount(3)
        tree.setHeaderLabels(["Name", "Type", "Value"])

        for key, value in container_iter(data):
            top_level_item = tree_widget_item(key, value)
            tree.addTopLevelItem(top_level_item)
            # expand_items(top_level_item)

        tree.expandToDepth(3)
        tree.resizeColumnToContents(0)
        tree.resizeColumnToContents(1)
        tree.resizeColumnToContents(2)

        @Slot()
        def on_item_double_clicked(item: QTreeWidgetItem, col):
            if isinstance(item, QTreeWidgetItem_WithData):
                if item.gbx_data.type == "bytes":
                    self._on_item_select(item.gbx_data.value)

        tree.itemDoubleClicked.connect(on_item_double_clicked)


def GbxEditorUi(parsed_data):
    win = GbxEditorUiWindow()
    win.set_data(parsed_data)

    return win

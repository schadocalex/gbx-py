import datetime
import os
import sys
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
)
from PySide6.QtCore import Slot, QSize, Qt
from PySide6.QtGui import QTextCursor

from src.gbx_structs import GbxPose3D, GbxStruct, GbxStructWithoutBodyParsed
from construct import (
    Container,
    ListContainer,
    RawCopy,
    Struct,
    Adapter,
    Subconstruct,
)

from src.widgets.hex_editor import GbxHexEditor
from src.widgets.inspector import Inspector


def container_iter(ctn):
    for key, value in ctn.items():
        if key != "_io":
            yield key, value


class QTreeWidgetItem_WithData(QTreeWidgetItem):
    def __init__(self, data, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.gbx_data = data


def tree_widget_item(key, value):
    if isinstance(value, Container):
        item = QTreeWidgetItem([key])
        for child in container_iter(value):
            item.addChild(tree_widget_item(*child))

        return item
    elif isinstance(value, ListContainer):
        item = QTreeWidgetItem([key, f"Array({len(value)})"])

        for i, child in enumerate(value):
            item.addChild(tree_widget_item(str(i), child))

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


def GbxDataViewer(data, on_item_select):
    tree = QTreeWidget()
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
                on_item_select(item.gbx_data.value)

    tree.itemDoubleClicked.connect(on_item_double_clicked)

    return tree


def GbxEditorUi(raw_bytes, parsed_data):
    # window

    app = QApplication.instance() or QApplication(sys.argv)

    window = QMainWindow()
    window.resize(QSize(1600, 1000))

    # widgets

    inspector = Inspector()

    def on_select(raw_bytes, selection):
        inspector.inspect(raw_bytes, selection)

    hex_editor = GbxHexEditor(on_select)
    hex_editor.set_bytes(raw_bytes)

    def on_item_select(new_bytes):
        hex_editor.set_bytes(new_bytes)
        inspector.inspect(new_bytes, [])

    tree = GbxDataViewer(parsed_data, on_item_select)

    # layout

    layout_v = QVBoxLayout()
    layout_v.addWidget(hex_editor)
    layout_v.addWidget(inspector)

    layout_h = QHBoxLayout()
    layout_h.addWidget(tree)
    layout_h.addLayout(layout_v)

    widget = QWidget()
    widget.setLayout(layout_h)
    window.setCentralWidget(widget)
    window.show()
    # app.exec()

    return window


def wrapStruct(struct):
    if isinstance(struct, Struct):
        return RawCopy(Struct(*[wrapStruct(s) for s in struct.subcons]))
    else:
        return RawCopy(struct)


def generate_node(data, remove_external=True, editor=True):
    gbx_data = {}
    nodes = data.nodes[:]

    # compression
    data.header.body_compression = "compressed"

    # remove external nodes because we merge them
    if remove_external:
        data.reference_table.num_external_nodes = 0
        data.reference_table.external_folders = None
        data.reference_table.external_nodes = []

    new_bytes = GbxStruct.build(data, gbx_data=gbx_data, nodes=nodes)
    if not editor:
        return new_bytes, None

    # for n in nodes:
    #     if n is not None and type(n) is not str:
    #             print(f"node not referenced {n.path}")

    # check built node
    gbx_data = {}
    nodes = []
    new_data = GbxStruct.parse(new_bytes, gbx_data=gbx_data, nodes=nodes)
    new_data.nodes = ListContainer(nodes)

    # data2 = GbxStructWithoutBodyParsed.parse(new_bytes, gbx_data={}, nodes=[])
    # data2.header.body_compression = "uncompressed"
    # new_bytes_uncompressed = GbxStructWithoutBodyParsed.build(
    #     data2, gbx_data={}, nodes=[]
    # )

    return new_bytes, GbxEditorUi(new_bytes, new_data)

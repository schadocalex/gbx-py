import os
import sys

from PySide6.QtWidgets import QApplication, QFileDialog

from construct import Container, ListContainer

from src.parser import parse_node, generate_node, parse_node_recursive
from src.editor import GbxEditorUiWindow


def on_new_file(file):
    win.setWindowTitle(file)
    data, nb_nodes, raw_bytes = parse_node(file)
    win.set_data(raw_bytes, data)

    # Modify it

    # Write the new file

    # bytes3 = generate_node(data)
    # win3 = GbxEditorUi(bytes3, data)

    # with open(
    #     get_ud_tm2020_path(r"C:\Users\schad\Documents\Trackmania\Items\NewItem.Item.Gbx"),
    #     "wb",
    # ) as f:
    #     f.write(bytes3)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)

    win = GbxEditorUiWindow(on_new_file, default_directory=r"C:\Users\schad\Documents\Trackmania\Items")

    app.exec()

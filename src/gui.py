import os
import sys

from PySide6.QtWidgets import QApplication, QFileDialog
from construct import Container, ListContainer

from .parser import parse_file, generate_node
from .editor import GbxEditorUi, GbxEditorUiWindow


def on_new_file(win, file):
    win.setWindowTitle(file)

    data = parse_file(file)
    win.set_data(data)

    # Modify it

    # Write the new file

    # bytes3 = generate_node(data)

    # file3 = r"C:\Users\schad\Documents\Trackmania\Items\test.Item.Gbx"
    # with open(file3, "wb") as f:
    #     f.write(bytes3)
    # data3, nb_node3s, raw_bytes3 = parse_file(file3)
    # win3 = GbxEditorUi(bytes3, data3)


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    win = GbxEditorUiWindow(
        lambda file: on_new_file(win, file),
        default_directory=r"C:\Users\schad\Documents\Trackmania\Items",
    )

    app.exec()

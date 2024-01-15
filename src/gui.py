import os
import sys

from PySide6.QtWidgets import QApplication, QFileDialog
from construct import Container, ListContainer

from .parser import parse_file, generate_file
from .editor import GbxEditorUi, GbxEditorUiWindow


def on_new_file(win, file):
    win.setWindowTitle(file)

    data = parse_file(file)
    win.set_data(data)

    # Modify it

    # Write the new file

    # bytes2 = generate_file(data)

    # file2 = r"C:\Users\schad\Documents\Trackmania\Items\test.Item.Gbx"
    # with open(file2, "wb") as f:
    #     f.write(bytes2)

    # verify the new file by opening it in a new window
    # data2 = parse_file(file2)
    # win2 = GbxEditorUi(data2)
    # win2.setWindowTitle(file2)


def main():
    app = QApplication.instance() or QApplication(sys.argv)

    win = GbxEditorUiWindow(
        lambda file: on_new_file(win, file),
        default_directory=r"C:\Users\schad\Documents\Trackmania\Items",
    )

    app.exec()

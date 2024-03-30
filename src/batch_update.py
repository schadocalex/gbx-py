import os
import sys
from glob import glob

from PySide6.QtWidgets import QApplication, QFileDialog

from .parser import parse_file, generate_file
from .editor import GbxEditorUi, GbxEditorUiWindow

CHECK_GUI = True
GLOB = r"./items/**/*.Item.Gbx"


def update(data):
    chunk = data.body[0x2E00201C].defaultPlacement.body[0x2E020000]
    chunk.gridSnap_VStep = 2.0
    chunk.flyStep = 2.0


def main():
    # loop over all items
    for file in glob(GLOB, recursive=True):
        print(file)
        data = parse_file(file)

        if CHECK_GUI:
            app = QApplication.instance() or QApplication(sys.argv)
            win = GbxEditorUiWindow()
            win.setWindowTitle("Before")
            win2 = GbxEditorUiWindow()
            win2.setWindowTitle("After")
            win.set_data(data)

        update(data)

        if CHECK_GUI:
            win2.set_data(data)
            app.exec()

            # only show GUI for the first file
            return
        else:
            # Generate the new file and overwrite it
            with open(file, "wb") as f:
                f.write(generate_file(data))

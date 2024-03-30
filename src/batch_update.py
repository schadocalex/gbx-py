import os
import sys
from glob import glob

from PySide6.QtWidgets import QApplication, QFileDialog

from .parser import parse_file, generate_file
from .editor import GbxEditorUi, GbxEditorUiWindow

# glob with the /**/ recursive wildcard. Can be absolute path f.e. in the Document folder
GLOB = r"./items/**/*.Item.Gbx"

# Set to True to debug what is Before and After (with a GUI)
# Set this to False to run the batch update, make a copy in case something's wrong
CHECK_GUI = True


# Change this function to change the file data.
# It is recommended to look at the GUI to analyze the data.
# You might put a breakpoint here too
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

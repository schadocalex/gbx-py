import os
import sys

from PySide6.QtWidgets import QApplication, QFileDialog

from construct import Container, ListContainer

from src.parser import parse_node, generate_node, parse_node_recursive
from src.editor import GbxEditorUi, GbxEditorUiWindow

from src.utils_bloc import extract_block_meshes


def on_new_file(file):
    win.setWindowTitle(file)
    data, nb_nodes, raw_bytes = parse_node(file)
    win.set_data(raw_bytes, data)

    # Modify it

    # Write the new file

    # bytes3 = generate_node(data)

    # file3 = r"C:\Users\schad\Documents\Trackmania\Items\test.Item.Gbx"
    # with open(file3, "wb") as f:
    #     f.write(bytes3)
    # data3, nb_node3s, raw_bytes3 = parse_node(file3)
    # win3 = GbxEditorUi(bytes3, data3)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)

    win = GbxEditorUiWindow(on_new_file, default_directory=r"C:\Users\schad\Documents\Trackmania\Items")

    app.exec()

# block extraction

# if __name__ == "__main__":
#     file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClassic\RoadTechStraight.EDClassic.Gbx"
#     data, nb_nodes, raw_bytes = parse_node_recursive(file)
#     win.set_data(raw_bytes, data)

#     extract_block_meshes(os.path.basename(file), data)

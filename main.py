import os
import sys

from PySide6.QtWidgets import QApplication, QFileDialog

from construct import Container, ListContainer

from src.parser import parse_node, generate_node, parse_node_recursive
from src.editor import GbxEditorUi, GbxEditorUiWindow

from export_obj import extract_solid2model, export_meshes


def on_new_file(file):
    win.setWindowTitle(file)
    data, nb_nodes, raw_bytes = parse_node(file)
    win.set_data(raw_bytes, data)

    # Modify it

    # Write the new file

    # bytes3 = generate_node(data)

    # file3 = r"C:\Users\schad\Documents\Trackmania\Items\20_HexHo6th_Height16_3_2.Mesh.gbx"
    # with open(file3, "wb") as f:
    #     f.write(bytes3)
    # data3, nb_node3s, raw_bytes3 = parse_node(file3)
    # win3 = GbxEditorUi(bytes3, data3)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)

    win = GbxEditorUiWindow(on_new_file, default_directory=r"C:\Users\schad\Documents\Trackmania\Items")

    # file = r"C:\Users\schad\Documents\Trackmania\Items\20_HexHo6th_Height16_3.Mesh.gbx"
    # data, nb_nodes, raw_bytes = parse_node(file)
    # win.set_data(raw_bytes, data)

    # meshes = extract_solid2model(data, data)
    # export_meshes("ExportObj/20_HexHo6th_Height16_3/", "20_HexHo6th_Height16_3", meshes)

    app.exec()

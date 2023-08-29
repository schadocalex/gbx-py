from PySide6.QtWidgets import QApplication

from construct import Container, ListContainer

from src.parser import parse_node, generate_node, parse_node_recursive
from src.editor import GbxEditorUi

if __name__ == "__main__":
    # Read the file

    file = r"C:\Users\schad\Documents\Trackmania\Items\Collection.Item.Gbx"

    data, nb_nodes, raw_bytes = parse_node(file)
    win = GbxEditorUi(raw_bytes, data)

    # Modify it

    # Write the new file

    # bytes3 = generate_node(data, remove_external=False)
    # win3 = GbxEditorUi(bytes3, data)

    # with open(
    #     get_ud_tm2020_path(r"C:\Users\schad\Documents\Trackmania\Blocks\WaterGrassBaseCorner3.Block.Gbx"),
    #     "wb",
    # ) as f:
    #     f.write(bytes3)

    app = QApplication.instance() or QApplication(sys.argv)
    app.exec()

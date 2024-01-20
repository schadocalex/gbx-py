from src.nice.api import *
from src.parser import parse_file, generate_file


def generate_item():
    files_parsed = {}

    mesh1 = get_noderef(files_parsed, r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Mesh.Gbx")

    item = new_advanced_item(
        "schadocalex",
        "MyItem",
        [
            new_ent_mesh(
                Loc((0, 0, 0), (1, 0, 0, 0)),  # TODO object.location, object.rotation_euler.to_quaternion()
                mesh1,  # visual, not collidable, mandatory
                # shape_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",  # invisible, collidable, optional
            ),
            # Gate(
            #     loc=Loc((0, 0, 0), (1, 0, 0, 0)),
            #     shape_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",  # not collidable, with gameplay
            #     gameplayId="ReactorBoost2",
            # ),
        ],
        waypoint_type="None",
        icon_filepath=None,
    )

    file = r"C:\Users\schad\Documents\Trackmania\Items\nice.Item.Gbx"
    with open(file, "wb") as f:
        f.write(generate_file(item, reindex_nodes=True))

    import sys
    from PySide6.QtWidgets import QApplication
    from src.editor import GbxEditorUi

    data = parse_file(file)

    app = QApplication.instance() or QApplication(sys.argv)
    win = GbxEditorUi(data)
    app.exec()

import sys
import os

sys.path.append(os.path.dirname(__file__))

from src.nice.api import *

bl_info = {
    "name": "Nadeo Importer Community Edition (NICE)",
    "author": "schadocalex",
    "description": "Export custom items to TM2020 with new features",
    "blender": (3, 4, 0),
    "version": (1, 0, 0),
    "location": "View3D",
    "warning": "",
    "category": "Generic",
}


def register():
    pass


def unregister():
    pass


def generate_node():
    item = AdvancedItem(
        author="schadocalex",
        name="MyItem",
        waypoint_type="None",
        icon_filepath=None,
        entities=[
            Mesh(
                loc=Loc((0, 0, 0), (1, 0, 0, 0)),  # object.location, object.rotation_euler.to_quaternion()
                mesh_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Mesh.Gbx",  # visual, not collidable, mandatory
                # r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",  # invisible, collidable, optional
            ),
            Gate(
                loc=Loc((0, 0, 0), (1, 0, 0, 0)),
                shape_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",  # notcollidable, with gameplay
                gameplayId="ReactorBoost2",
            ),
        ],
    )

    with open(r"C:\Users\schad\Documents\Trackmania\Items\nice.Item.Gbx", "wb") as f:
        f.write(item.generate())

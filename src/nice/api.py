from collections import namedtuple

from src.nice.utils import *
from src.parser import generate_file

EGameplayProps = namedtuple("EGameplayProps", ["label", "nice_id", "as_gate"])

EPhysics = {"Concrete": "Concrete"}

EGameplay = {
    "No": EGameplayProps("None", "No", False),
    "Turbo": EGameplayProps("Turbo", "Turbo", True),
    "Turbo2": EGameplayProps("Turbo2", "Turbo2", True),
    "TurboRoulette": EGameplayProps("TurboRoulette", "TurboRoulette", True),
    "FreeWheeling": EGameplayProps("FreeWheel", "FreeWheeling", True),
    "NoGrip": EGameplayProps("NoGrip", "NoGrip", False),
    "NoSteering": EGameplayProps("NoSteering", "NoSteering", True),
    "ForceAcceleration": EGameplayProps("ForceAcceleration", "ForceAcceleration", False),
    "Reset": EGameplayProps("Reset", "Reset", True),
    "SlowMotion": EGameplayProps("SlowMotion", "SlowMotion", True),
    "Bumper": EGameplayProps("Bumper", "Bumper", False),
    "Bumper2": EGameplayProps("Bumper2", "Bumper2", False),
    "Fragile": EGameplayProps("Fragile", "Fragile", True),
    "NoBrakes": EGameplayProps("NoBrakes", "NoBrakes", True),
    "Cruise": EGameplayProps("Cruise", "Cruise", True),
    "ReactorBoost": EGameplayProps("ReactorBoost", "ReactorBoost_Oriented", True),
    "ReactorBoost2": EGameplayProps("ReactorBoost2", "ReactorBoost2_Oriented", True),
}

EWaypoint = {
    "None": "No",
    "Start": "Start",
    "Finish": "Finish",
    "Checkpoint": "Checkpoint",
    "NoRespawn Checkpoint": "Checkpoint",
    "Multilap": "StartFinish",
}


class Loc:
    def __init__(self, pos, rot=(0, 0, 0)):
        self.pos = pos
        self.rot = rot

    def to_bytes():
        # TODO euler angles
        return Ctn(
            XX=1,
            XY=0,
            XZ=0,
            YX=0,
            YY=1,
            YZ=0,
            ZX=0,
            ZY=0,
            ZZ=1,
            TX=self.pos.x,
            TY=self.pos.y,
            TZ=self.pos.z,
        )


class StaticObject:
    """unused"""

    def __init__(self, mesh_filepath, is_mesh_collidable=True, shape_filepath=""):
        self.mesh_filepath = mesh_filepath
        self.is_mesh_collidable = is_mesh_collidable
        self.shape_filepath = shape_filepath


class DynaObject:
    """unused"""

    def __init__(self, mesh_filepath, shape_filepath):
        self.mesh_filepath = mesh_filepath
        self.shape_filepath = shape_filepath


class Gate:
    """Invisible shape without collision that has a gameplay id"""

    def __init__(self, shape_filepath, gameplayId="Turbo"):
        self.shape_filepath = shape_filepath
        self.gameplayId = EGameplay[gameplayId].nice_id


class Shape:
    """Invisible shape with collision that has physics and gameplay ids"""

    def __init__(self, shape_filepath, physicsId="Concrete", gameplayId="None"):
        self.shape_filepath = shape_filepath
        self.physicsId = EPhysics[gameplayId]
        self.gameplayId = EGameplay[gameplayId].nice_id

    def get_entities(self, refidx):
        return [
            Ctn(
                model=refidx,
                rot=Ctn(x=0, y=0, z=0, w=1),
                pos=Ctn(x=0, y=0, z=0),
                params=Ctn(chunkId=-1, chunk=None),
                u01=b"",
            )
        ]


class Mesh:
    """Visible but NOT collidable mesh"""

    def __init__(self, mesh_filepath, shape_filepath=None):
        self.mesh_filepath = mesh_filepath
        self.shape_filepath = shape_filepath

    def get_entities(self, nodes, files_refidx):
        refidx = len(nodes)
        static_object = new_struct(
            0x09159000,
            Ctn(
                version=3,
                Mesh=-1,
                isMeshCollidable=False,
                Shape=-1,
            ),
        )
        nodes.append(static_object)

        static_object.body.Mesh = get_refidx(nodes, files_refidx, self.mesh_filepath, extract_file, 0x090BB000)
        if self.shape_filepath is not None:
            static_object.body.Shape = get_refidx(nodes, files_refidx, self.shape_filepath, extract_shape)
        else:
            static_object.body.Shape = -1

        return [
            Ctn(
                model=refidx,
                rot=Ctn(x=0, y=0, z=0, w=1),
                pos=Ctn(x=0, y=0, z=0),
                params=Ctn(chunkId=-1, chunk=None),
                u01=b"",
            )
        ]


class Waypoint:
    """Invisible shape without collision that triggers Checkpoint/Finish/StartFinish
    no_respawn attribute is only for Checkpoint"""

    def __init__(self, shape_filepath, no_respawn=False):
        self.shape_filepath = shape_filepath
        self.no_respawn = no_respawn


class Spawn(Loc):
    """3D position for Start/Checkpoint/StartFinish
    If not present, will default to (0,0,0)"""

    pass


class AdvancedItem:
    def __init__(self, author="", name="", waypoint_type="None", icon_filepath=None, entities=None):
        self.author = author
        self.name = name
        self.waypoint_type = EWaypoint[waypoint_type]
        self.icon_filepath = icon_filepath
        self.entities = entities

    def generate(self):
        nodes = [None, None]
        files_refidx = {}
        entities = []
        for entity in self.entities:
            entities += entity.get_entities(nodes, files_refidx)

        nodes[1] = new_composed_model(entities)

        placement_refidx = new_placement_nodes(nodes)

        data = new_file(
            self.author,
            self.name,
            self.icon_filepath,
            new_item_body(
                self.author,
                self.name,
                self.waypoint_type,
                1,
                placement_refidx,
            ),
            List(nodes),
        )

        # import sys
        # from PySide6.QtWidgets import QApplication
        # from src.editor import GbxEditorUi

        # app = QApplication.instance() or QApplication(sys.argv)
        # win = GbxEditorUi(b"", data)
        # app.exec()

        return generate_file(data)

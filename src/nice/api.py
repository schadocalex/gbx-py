from collections import namedtuple

from .utils import *
from ..parser import generate_file
from ..utils.misc import update_surf
from ..gbx_structs import NodeRef

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
    "VehicleCarSnow": EGameplayProps("VehicleCarSnow", "VehicleTransform_CarSnow", True),
    "VehicleReset": EGameplayProps("VehicleReset", "VehicleTransform_Reset", True),
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
    def __init__(self, pos, quat):
        self.pos = pos
        self.quat = quat

    def as_matrix(self):
        x, y, z = self.pos
        # TODO rot
        return Ctn(XX=1, XY=0, XZ=0, YX=0, YY=1, YZ=0, ZX=0, ZY=0, ZZ=1, TX=x, TY=y, TZ=z)

    def as_quat(self):
        w, x, y, z = self.quat
        return Ctn(x=x, y=z, z=-y, w=w)

    def as_pos(self):
        x, y, z = self.pos
        return Ctn(x=x, y=z, z=-y)


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

    def __init__(self, loc, shape_filepath, gameplay_id="Turbo"):
        self.loc = loc
        self.shape_filepath = shape_filepath
        self.gameplay_id = EGameplay[gameplay_id].nice_id

    def get_entities(self, files_parsed):
        gate = new_struct(
            0x09179000,
            Ctn(
                version=1,
                surf=get_noderef(nodes, files_parsed, self.shape_filepath, extract_shape),
            ),
        )

        utils.update_surf(
            gate.body.surf,
            physics_id="Concrete",
            gameplay_id=self.gameplay_id,
            gameplay_main_dir=None,  # TODO
        )

        return [
            Ctn(
                model=gate_index,
                rot=self.loc.as_quat(),
                pos=self.loc.as_pos(),
                params=Ctn(chunkId=-1, chunk=None),
                u01=b"",
            )
        ]


class Shape:
    """Invisible shape with collision that has physics and gameplay ids"""

    def __init__(self, shape_filepath, physics_id="Concrete", gameplay_id="None"):
        self.shape_filepath = shape_filepath
        self.physics_id = EPhysics[physics_id]
        self.gameplay_id = EGameplay[gameplay_id].nice_id


def new_ent_mesh(loc, mesh, shape=None):
    """Visible but NOT collidable mesh with optionnal collision shape"""

    return new_ent(
        loc,
        new_struct(
            0x09159000,
            Ctn(
                version=3,
                Mesh=mesh,
                isMeshCollidable=False,
                Shape=shape if shape is not None else NodeRef(),
            ),
        ),
    )


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


def new_advanced_item(author, name, entities=None, waypoint_type="None", icon_filepath=None):
    assert isinstance(entities, list)

    return new_file(
        author,
        name,
        icon_filepath,
        new_item_body(
            author,
            name,
            waypoint_type,
            new_entities(entities),
            new_placement_node(),
        ),
    )

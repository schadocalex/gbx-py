# pyinstaller.exe --onefile --paths=./ --add-data "assets/all_signs_24.png;assets/" custom_gates.py

import sys
import os
import datetime
from pathlib import Path
from copy import deepcopy
from src.parser import parse_node, generate_node
from src.utils import update_surf

from construct import Container, ListContainer

from PIL import Image, ImageDraw


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


BASE_GATE = "Turbo"
GATES = [
    "Turbo",
    "Turbo2",
    "SlowMotion",
    "Reset",
    "NoSteering",
    "NoEngine",
    "NoBrake",
    "Fragile",
    "Cruise",
    "Boost",
    "Boost2",
]
GATES_TO_GAMEPLAYID = {
    "Turbo": "Turbo",
    "Turbo2": "Turbo2",
    "SlowMotion": "SlowMotion",
    "Reset": "Reset",
    "NoSteering": "NoSteering",
    "NoEngine": "FreeWheeling",
    "NoBrake": "NoBrakes",
    "Fragile": "Fragile",
    "Cruise": "Cruise",
    "Boost": "ReactorBoost_Oriented",
    "Boost2": "ReactorBoost2_Oriented",
}
TEXTURES_LINK_REMAPPING = {
    "TriggerFXTurbo": lambda gate: "Stadium\\Media\\Modifier\\" + gate + "\\TriggerFX",
    "SpecialFXTurbo": lambda gate: "Stadium\\Media\\Modifier\\" + gate + "\\SpecialFX",
    "SpecialSignTurbo": lambda gate: "Stadium\\Media\\Modifier\\" + gate + "\\Sign",
    "SpecialSignOff": lambda gate: "Stadium\\Media\\Modifier\\"
    + gate
    + "\\Sign"
    + ("Off" if gate in ["Turbo", "Turbo2", "Boost", "Boost2"] else ""),
    "DecalSpecialTurbo": lambda gate: "Stadium\\Media\\Modifier\\" + gate + "\\Decal",
}
TEXTURES_NAME_REMAPPING = {
    "TriggerFXTurbo": lambda gate: gate + "_TriggerFX",
    "SpecialFXTurbo": lambda gate: gate + "_SpecialFX",
    "SpecialSignTurbo": lambda gate: gate + "_Sign",
    "SpecialSignOff": lambda gate: gate + "_SignOff",
    "DecalSpecialTurbo": lambda gate: gate + "_Decal",
}


def add_gate_from_trigger(data):
    entity_model_idx = data.body[12].chunk.EntityModel
    static_object_idx = data.nodes[entity_model_idx].body[0].chunk.staticObject
    trigger_idx = data.nodes[entity_model_idx].body[0].chunk.props.triggerArea

    # Create the gate
    gate_index = len(data.nodes)
    data.nodes.append(
        Container(
            header=Container(class_id=0x09179000),
            body=Container(
                version=1,
                surf=trigger_idx,
            ),
        )
    )

    # Replace the static object
    data.nodes[entity_model_idx] = Container(
        header=Container(class_id=0x09145000),
        body=Container(
            version=11,
            updatedTime=datetime.datetime.now(),
            url="",
            u01=b"\x00\x00\x00\x00",
            u02=b"\x00\x00\x00\x00",
            Ents=ListContainer(
                [
                    Container(
                        model=static_object_idx,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        LodGroupId=-1,
                        name="",
                    ),
                    Container(
                        model=gate_index,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        LodGroupId=-1,
                        name="",
                    ),
                ]
            ),
        ),
    )

    return data


def change_textures(data, gate):
    for node in data.nodes:
        if type(node) == Container:
            if node.header.class_id == 0x090FD000:
                for key in TEXTURES_LINK_REMAPPING:
                    if key in node.body[0].chunk.link:
                        node.body[0].chunk.isUsingGameMaterial = True
                        node.body[0].chunk.materialName = TEXTURES_NAME_REMAPPING[key](
                            gate
                        )
                        node.body[0].chunk.link = TEXTURES_LINK_REMAPPING[key](gate)


if __name__ == "__main__":
    file = sys.argv[1]

    data, nb_nodes, raw_bytes = parse_node(file)
    data.body[16].chunk.u08 = 0

    export_dir = Path(os.path.dirname(os.path.abspath(file)))

    data = add_gate_from_trigger(data)

    entity_model_idx = data.body[12].chunk.EntityModel
    gate_idx = data.nodes[entity_model_idx].body.Ents[1].model
    surf_idx = data.nodes[gate_idx].body.surf

    with Image.open(resource_path("assets/all_signs_24.png")) as im_signs:
        for gate_idx, gate in enumerate(GATES):
            data_gate = deepcopy(data)

            # modify item name

            file_name_suffix = "_" + gate

            data_gate.header.chunks.data[0].file_name += file_name_suffix
            data_gate.body[2].chunk.name += file_name_suffix

            # update the gameplay

            update_surf(
                data_gate.nodes[surf_idx], "NotCollidable", GATES_TO_GAMEPLAYID[gate]
            )

            # update the textures

            if gate != BASE_GATE:
                change_textures(data_gate, gate)

            # update the icon

            icon_chunk = data_gate.header.chunks.data[1]
            if not icon_chunk.webp:
                for y in range(24):
                    for x in range(24):
                        dest_idx = (24 - y) * 64 + (40 + x)
                        px = im_signs.getpixel((gate_idx * 24 + x, y))
                        icon_chunk.data[dest_idx] = Container(
                            r=px[0], g=px[1], b=px[2], a=255
                        )

            # save the new item

            new_bytes = generate_node(data_gate, True)

            new_file_name = os.path.basename(file).split(".")
            new_file_name[-3] += file_name_suffix
            new_file_name = ".".join(new_file_name)
            export_file_name = export_dir / new_file_name
            with open(export_file_name, "wb") as f:
                f.write(new_bytes)
            print(export_file_name)

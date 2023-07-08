# pyinstaller.exe --onefile --paths=./ custom_gate.py

import sys
import os
import datetime
from headless_parser import parse_node, generate_node
from utils import update_surf

from construct import Container, ListContainer

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
    "TriggerFX": lambda gate: "Stadium\\Media\\Modifier\\" + gate + "\\TriggerFX",
    "SpecialFX": lambda gate: "Stadium\\Media\\Modifier\\" + gate + "\\SpecialFX",
    "Sign": lambda gate: "Stadium\\Media\\Modifier\\" + gate + "\\Sign",
    "SignOff": lambda gate: "Stadium\\Media\\Modifier\\" + gate + "\\SignOff",
    "Decal": lambda gate: "Stadium\\Media\\Modifier\\" + gate + "\\Decal",
}
TEXTURES_NAME_REMAPPING = {
    "TriggerFX": lambda gate: gate + "_TriggerFX",
    "SpecialFX": lambda gate: gate + "_SpecialFX",
    "Sign": lambda gate: gate + "_Sign",
    "SignOff": lambda gate: gate + "_SignOff",
    "Decal": lambda gate: gate + "_Decal",
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

    # data.nodes[2].body.isMeshCollidable = False
    # data.nodes[2].body.collidableShape = -1

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

    data, nb_nodes = parse_node(file)
    data.body[16].chunk.u08 = 0

    export_dir = os.path.dirname(file) + "\\ExportGates\\"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    data = add_gate_from_trigger(data)

    entity_model_idx = data.body[12].chunk.EntityModel
    gate_idx = data.nodes[entity_model_idx].body.Ents[1].model
    surf_idx = data.nodes[gate_idx].body.surf

    ori_file_name = data.header.chunks.data[0].file_name
    ori_item_name = data.body[2].chunk.string

    for gate in GATES:
        data.header.chunks.data[0].file_name = ori_file_name.replace(BASE_GATE, gate)
        data.body[2].chunk.string = ori_item_name.replace(BASE_GATE, gate)

        update_surf(data.nodes[surf_idx], "NotCollidable", GATES_TO_GAMEPLAYID[gate])

        if gate != BASE_GATE:
            change_textures(data, gate)

        new_bytes = generate_node(data, True)

        export_file_name = export_dir + os.path.basename(file).replace(BASE_GATE, gate)
        with open(export_file_name, "wb") as f:
            f.write(new_bytes)
        print(export_file_name)

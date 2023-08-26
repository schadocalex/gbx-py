# pyinstaller.exe --onefile --paths=./ norespawn_cp.py

import sys
import os
import datetime
from pathlib import Path

from src.parser import parse_node, generate_node

from construct import Container, ListContainer


def add_cp_from_trigger(data):
    entity_model_idx = data.body[12].chunk.EntityModel
    static_object_idx = data.nodes[entity_model_idx].body[0].chunk.staticObject
    trigger_idx = data.nodes[entity_model_idx].body[0].chunk.props.triggerArea

    # Create the cp
    cp_index = len(data.nodes)
    data.nodes.append(
        Container(
            header=Container(class_id=0x09178000),
            body=Container(
                version=1,
                Type="Checkpoint",
                TriggerShape=trigger_idx,
                NoRespawn=True,
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
                        model=cp_index,
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


if __name__ == "__main__":
    file = sys.argv[1]

    export_dir = Path(os.path.dirname(os.path.abspath(file)))
    data, nb_nodes, raw_bytes = parse_node(file)

    add_cp_from_trigger(data)
    data.body[16].chunk.waypointType = "Checkpoint"
    data.body[16].chunk.u08 = 0

    new_bytes = generate_node(data)

    new_file_name = os.path.basename(file).split(".")
    new_file_name[-3] += "_NoRespawn"
    new_file_name = ".".join(new_file_name)
    export_file_name = export_dir / new_file_name
    with open(export_file_name, "wb") as f:
        f.write(new_bytes)
    print(export_file_name)

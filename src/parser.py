import os
from pathlib import Path
from functools import partial
from collections import OrderedDict

from construct import Container

from .gbx_structs import GbxStruct, GbxStructWithoutBodyParsed


def parse_bytes(raw_bytes):
    """Use this for in-memory reading"""
    return GbxStruct.parse(
        raw_bytes,
        gbx_data={},
        nodes=[],
        load_external_file=lambda _: Container(),
    )


def parse_file(file_path, with_nodes=False, recursive=True, log=False):
    file_path = os.path.abspath(file_path)
    file_dir = os.path.dirname(file_path)

    if not os.path.exists(file_path):
        error = f"[FILE NOT FOUND] {file_path}"
        print(error)
        return Container(_error=error)

    if log:
        print(file_path)

    with open(file_path, "rb") as f:
        gbx_data = {}
        nodes = []
        data = GbxStruct.parse(
            f.read(),
            gbx_data=gbx_data,
            nodes=nodes,
            filename=file_path,
            load_external_file=partial(_load_external_file, {}, log, file_dir, with_nodes, recursive),
        )
        data.filepath = file_path
        if with_nodes:
            data.nodes = nodes
        data.node_offset = 0
        nb_nodes = len(nodes) - 1

        return data


def _load_external_file(files_cache, log, root_path, with_nodes, recursive, relative_path):
    file_path = os.path.normpath(root_path + os.path.sep + relative_path)

    if file_path in files_cache:
        if log:
            print("reuse " + file_path)
        return files_cache[file_path]

    if file_path.endswith(".Material.Gbx"):
        material_name = os.path.basename(file_path).split(".")[0]
        files_cache[file_path] = create_custom_material(material_name)
    elif (
        not recursive
        or not file_path.lower().endswith(".gbx")
        or file_path.lower().endswith(".texture.gbx")
        or file_path.lower().endswith(".light.gbx")
        or file_path.lower().endswith(".sound.gbx")
        or file_path.lower().endswith(".vegettreemodel.gbx")
        or "vegetation" in file_path.lower()
    ):
        files_cache[file_path] = Container()
    else:
        if log:
            print("load external: " + file_path)

        try:
            files_cache[file_path] = parse_file(file_path, with_nodes=with_nodes, recursive=True)
        except Exception as e:
            print(e)
            files_cache[file_path] = Container(_error="Unable to load file: " + file_path, _message=str(e))

    return files_cache[file_path]


def generate_file(data, remove_external=True, reindex_nodes=True):
    # force compression
    data.header.body_compression = "compressed"

    # remove external nodes because we merge them
    if remove_external:
        data.referenceTable.numExternalNodes = 0
        data.referenceTable.externalFolders = None
        data.referenceTable.externalNodes = []

    nodes = data.nodes if "nodes" in data else None
    new_bytes = GbxStruct.build(data, gbx_data={}, nodes=nodes, reindex_nodes=reindex_nodes)

    return new_bytes


def create_custom_material(material_name):
    return Container(
        classId=0x090FD000,
        body=OrderedDict(
            [
                (
                    0x090FD000,
                    Container(
                        version=11,
                        isUsingGameMaterial=False,
                        # materialName="TM_" + material_name + "_asset",
                        materialName=material_name,
                        model="",
                        baseTexture="",
                        surfacePhysicId=6,
                        surfaceGameplayId=0,
                        link=material_name,
                        csts=[],
                        color=[],
                        uvAnim=[],
                        u07=[],
                        userTextures=[],
                        hidingGroup="",
                    ),
                ),
                (
                    0x090FD001,
                    Container(
                        version=5,
                        u01=-1,
                        tilingU=0,
                        tilingV=0,
                        textureSize=1.0,
                        u02=0,
                        isNatural=False,
                    ),
                ),
                (0x090FD002, Container(version=0, u01=0)),
                (0xFACADE01, None),
            ]
        ),
    )

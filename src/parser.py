import os
from pathlib import Path
from functools import partial
from collections import OrderedDict

from construct import Container

from .gbx_structs import GbxStruct, GbxStructWithoutBodyParsed


def parse_bytes(raw_bytes, filepath="", /, log=False, recursive=False, files_cache=None):
    """Use this for in-memory reading"""
    if files_cache is None:
        files_cache = {}

    file_dir = os.path.dirname(filepath)

    gbx_data = {}
    nodes = []
    errors = []
    warns = []
    data = GbxStruct.parse(
        raw_bytes,
        gbx_data=gbx_data,
        nodes=nodes,
        filename=filepath,
        load_external_file=partial(_load_external_file, files_cache, log, file_dir, recursive),
        errors=errors,
        warns=warns,
    )
    data.filepath = filepath
    data.node_offset = 0
    data._errors = list(set(errors))
    data._warns = list(set(warns))

    return data


def parse_file(file_path, /, recursive=True, log=False, files_cache=None):
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        error = f"[FILE NOT FOUND] {file_path}"
        print(error)
        return Container(_error=error)

    if log:
        print(file_path)

    with open(file_path, "rb") as f:
        return parse_bytes(f.read(), file_path, recursive=recursive, log=log, files_cache=files_cache)


def _load_external_file(files_cache, log, root_path, recursive, relative_path):
    file_path = os.path.normpath(root_path + os.path.sep + relative_path)

    if file_path in files_cache:
        if log:
            print("reuse " + file_path)
        return files_cache[file_path]

    force_recursive = (
        file_path.lower().endswith(".terrainmodifier.gbx")
        or file_path.lower().endswith(".kinematicconstraint.gbx")
        or file_path.lower().endswith(".gameskin.gbx")
    )

    if file_path.endswith(".Material.Gbx"):
        material_name = os.path.basename(file_path).split(".")[0]

        # Add modifier
        folders = file_path.replace("\\", "/").split("/")
        if len(folders) >= 3 and folders[-3].lower() == "modifier":
            material_name = folders[-2] + "_" + material_name

        files_cache[file_path] = create_custom_material(material_name)
        files_cache[file_path]._fakeMaterial = True
    elif not force_recursive and (
        not recursive
        or not file_path.lower().endswith(".gbx")
        or file_path.lower().endswith(".texture.gbx")
        or file_path.lower().endswith(".light.gbx")
        or file_path.lower().endswith(".sound.gbx")
    ):
        files_cache[file_path] = Container()
    else:
        if log:
            print("load external: " + file_path)

        try:
            files_cache[file_path] = parse_file(file_path, recursive=True)
        except Exception as e:
            print(e)
            files_cache[file_path] = Container(_error="Unable to load file: " + file_path, _message=repr(e))
            files_cache[file_path]._errors = [f"{repr(e)} in {file_path}"]

    return files_cache[file_path]


def generate_file(data, remove_external=True, reindex_nodes=False):
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

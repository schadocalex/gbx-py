import os
from pathlib import Path
from functools import partial
from collections import OrderedDict

from construct import Container, ListContainer

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
            data.nodes = ListContainer(nodes)
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


def construct_all_folders(all_folders, parent_folder_path, current_folder):
    for folder in current_folder.folders:
        all_folders.append(os.path.normpath(parent_folder_path + folder.name) + os.path.sep)
        construct_all_folders(all_folders, all_folders[-1], folder)


def parse_node_recursive(file_path: Path, node_offset=0, path=None, flatten_nodes=False):
    if file_path in all_file_paths:
        print("reuse " + file_path)
        return all_file_paths[file_path]

    file_path = os.path.abspath(file_path)
    if path is None:
        path = []
    depth = len(path)
    file_name = os.path.basename(file_path)
    path.append(file_name)
    nf = "NOT FOUND" if not os.path.exists(file_path) else ""
    print("  " * depth + f"- {file_path} {nf}")
    if nf:
        return (
            f"NOT FOUND {file_path}",
            0,
            b"",
        )

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

        gbx_data = {}
        nodes = []
        data = GbxStruct.parse(raw_bytes, gbx_data=gbx_data, nodes=nodes, filename=file_path)
        # for i, n in enumerate(nodes):
        #     if type(n) is Container:
        #         n.root_node = data

        data.nodes = ListContainer(nodes)
        data.node_offset = node_offset
        data.path = path
        nb_nodes = len(data.nodes) - 1
        node_offset += len(data.nodes) - 1

        # get all folders
        external_folders = data.referenceTable.externalFolders
        root_folder_name = os.path.dirname(file_path) + os.path.sep
        all_folders = [root_folder_name]
        if external_folders is not None:
            root_folder_name += (".." + os.path.sep) * external_folders.ancestorLevel
            construct_all_folders(all_folders, root_folder_name, external_folders)

        # parse external nodes
        for external_node in data.referenceTable.externalNodes:
            if not external_node.ref.endswith(".gbx") and not external_node.ref.endswith(".Gbx"):
                continue
            elif external_node.ref.endswith(".Texture.gbx"):
                continue
            elif external_node.ref.endswith(".Light.Gbx"):
                continue
            elif external_node.ref.endswith(".Sound.Gbx"):
                continue
            elif external_node.ref.endswith("VegetTreeModel.Gbx"):
                continue
            elif "Vegetation" in external_node.ref:
                continue
            elif external_node.ref.endswith(".Material.Gbx"):
                material_name = external_node.ref.split(".")[0]
                data.nodes[external_node.nodeIndex] = create_custom_material(material_name)
                # print(
                #     "  " * (depth + 1) + f"- {material_name} Material (1 custom node)"
                # )
            # elif external_node.ref in path:
            #     print(
            #         "  " * (depth + 1)
            #         + f"- {external_node.ref} (Cyclic dependency detected?)"
            #     )
            else:
                # print(external_node.ref + " " + str(node_offset))
                ext_node_filepath = all_folders[external_node.folderIndex] + external_node.ref
                if not os.path.exists(ext_node_filepath):
                    data.nodes[external_node.nodeIndex] = "[NOT FOUND] " + ext_node_filepath
                    print("[NOT FOUND] " + ext_node_filepath)
                else:
                    ext_node_data, nb_sub_nodes, sub_raw_bytes = parse_node_recursive(
                        all_folders[external_node.folderIndex] + external_node.ref,
                        node_offset,
                        path[:],
                        flatten_nodes,
                    )
                    nb_nodes += nb_sub_nodes
                    node_offset += nb_sub_nodes
                    data.nodes[external_node.nodeIndex] = ext_node_data
                    ext_node_data.filepath = ext_node_filepath
                    if flatten_nodes:
                        data.nodes.extend(ext_node_data.nodes[1:])

        for i, n in enumerate(data.nodes):
            if n is not None and not "path" in n and type(n) is not str:
                n.path = f"{path} [node={i}]"

        all_file_paths[file_path] = (data, nb_nodes, raw_bytes)
        return all_file_paths[file_path]


def generate_node(data, remove_external=True):
    # compression
    data.header.body_compression = "compressed"

    # remove external nodes because we merge them
    if remove_external:
        data.referenceTable.numExternalNodes = 0
        data.referenceTable.externalFolders = None
        data.referenceTable.externalNodes = []

    gbx_data = {}
    nodes = data.nodes[:]
    new_bytes = GbxStruct.build(data, gbx_data=gbx_data, nodes=nodes)

    return new_bytes


def generate_file(data):
    gbx_data = {}
    nodes = data.nodes[:]
    new_bytes = GbxStruct.build(data, gbx_data=gbx_data, nodes=nodes)

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

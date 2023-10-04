import os
from pathlib import Path

from construct import Container, ListContainer

from src.gbx_structs import GbxStruct


def parse_node(file_path):
    file_path = os.path.abspath(file_path)

    if not os.path.exists(file_path):
        print(f"[NOT FOUND] {file_path}")
        return (
            Container(file=f"[NOT FOUND] {file_path}" if not os.path.exists(file_path) else ""),
            0,
            b"",
        )

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

        gbx_data = {}
        nodes = []
        data = GbxStruct.parse(raw_bytes, gbx_data=gbx_data, nodes=nodes, filename=file_path)
        data.nodes = ListContainer(nodes)
        data.node_offset = 0
        nb_nodes = len(data.nodes) - 1

        return data, nb_nodes, raw_bytes


parse_file = parse_node


def construct_all_folders(all_folders, parent_folder_path, current_folder):
    for folder in current_folder.folders:
        all_folders.append(parent_folder_path + folder.name + "/")
        construct_all_folders(all_folders, all_folders[-1], folder)


def parse_node_recursive(file_path: Path, node_offset=0, path=None):
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
        root_folder_name = os.path.dirname(file_path) + "/"
        all_folders = [root_folder_name]
        if external_folders is not None:
            root_folder_name += "../" * external_folders.ancestorLevel
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
            # elif external_node.ref.endswith(".PlaceParam.Gbx"):
            #     continue
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
                    )
                    nb_nodes += nb_sub_nodes
                    node_offset += nb_sub_nodes
                    data.nodes[external_node.nodeIndex] = ext_node_data
                    data.nodes.extend(ext_node_data.nodes[1:])

        for i, n in enumerate(data.nodes):
            if n is not None and not "path" in n and type(n) is not str:
                n.path = f"{path} [node={i}]"

        return (data, nb_nodes, raw_bytes)


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
        body=ListContainer(
            [
                Container(
                    chunkId=0x090FD000,
                    chunk=Container(
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
                Container(
                    chunkId=0x090FD001,
                    chunk=Container(
                        version=5,
                        u01=-1,
                        tiling_u=0,
                        tiling_v=0,
                        texture_size=1.0,
                        u02=0,
                        is_natural=False,
                    ),
                ),
                Container(chunkId=0x090FD002, chunk=Container(version=0, u01=0)),
                Container(
                    chunkId=0xFACADE01,
                ),
            ]
        ),
    )

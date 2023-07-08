import os
from construct import Container, ListContainer

from gbx_parser import GbxStruct


def parse_node(file_path, parse_deps=True, node_offset=0, path=None):
    file_path = os.path.abspath(file_path)
    file_path2 = file_path.replace(
        "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\", ""
    )
    if path is None:
        path = []
    depth = len(path)
    file_name = os.path.basename(file_path)
    path.append(file_name)
    nf = "NOT FOUND" if not os.path.exists(file_path) else ""
    print("  " * depth + f"- {file_path2} {nf}")
    # if nf:
    #     return (
    #         Container(header=Container()),
    #         0,
    #         None,
    #     )

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

        gbx_data = {}
        nodes = []
        data = GbxStruct.parse(
            raw_bytes, gbx_data=gbx_data, nodes=nodes, filename=file_path2
        )
        # for i, n in enumerate(nodes):
        #     if type(n) is Container:
        #         n.root_node = data

        data.nodes = ListContainer(nodes)
        data.node_offset = node_offset
        data.path = path
        nb_nodes = len(data.nodes) - 1
        node_offset += len(data.nodes) - 1
        # print("  " * depth + f"- {file_path2} ({len(data.nodes) - 1} nodes)")

        # get all folders
        external_folders = data.reference_table.external_folders
        root_folder_name = os.path.dirname(file_path) + "\\"
        all_folders = [root_folder_name]
        if external_folders is not None:
            root_folder_name += "..\\" * external_folders.ancestor_level
            construct_all_folders(all_folders, root_folder_name, external_folders)

        # parse external nodes
        for external_node in data.reference_table.external_nodes:
            if not external_node.ref.endswith(
                ".gbx"
            ) and not external_node.ref.endswith(".Gbx"):
                continue
            elif external_node.ref.endswith(".Texture.gbx"):
                continue
            elif external_node.ref.endswith(".Light.gbx"):
                continue
            elif external_node.ref.endswith("VegetTreeModel.Gbx"):
                continue
            elif "Vegetation" in external_node.ref:
                continue
            elif external_node.ref.endswith(".Material.Gbx"):
                material_name = external_node.ref.split(".")[0]
                data.nodes[external_node.node_index] = create_custom_material2(
                    material_name
                )
                # print(
                #     "  " * (depth + 1) + f"- {material_name} Material (1 custom node)"
                # )
            elif external_node.ref in path:
                print(
                    "  " * (depth + 1)
                    + f"- {external_node.ref} (Cyclic dependency detected?)"
                )
            elif parse_deps:
                # print(external_node.ref + " " + str(node_offset))
                ext_node_filepath = (
                    all_folders[external_node.folder_index] + external_node.ref
                )
                if not os.path.exists(ext_node_filepath):
                    data.nodes[external_node.node_index] = (
                        "[NOT FOUND] " + ext_node_filepath
                    )
                else:
                    ext_node_data, nb_sub_nodes, win = parse_node(
                        all_folders[external_node.folder_index] + external_node.ref,
                        parse_deps,
                        node_offset,
                        path[:],
                        False,
                    )
                    nb_nodes += nb_sub_nodes
                    node_offset += nb_sub_nodes
                    data.nodes[external_node.node_index] = ext_node_data
                    data.nodes.extend(ext_node_data.nodes[1:])

        for i, n in enumerate(data.nodes):
            if n is not None and not "path" in n and type(n) is not str:
                n.path = f"{path} [node={i}]"

        # data2 = GbxStructWithoutBodyParsed.parse(raw_bytes, gbx_data={}, nodes=[])
        # data2.header.body_compression = "uncompressed"
        # raw_bytes_uncompressed = GbxStructWithoutBodyParsed.build(
        #     data2, gbx_data={}, nodes=[]
        # )

        return (data, nb_nodes)


def generate_node(data, remove_external=True, editor=True):
    gbx_data = {}
    nodes = data.nodes[:]

    # compression
    data.header.body_compression = "compressed"

    # remove external nodes because we merge them
    if remove_external:
        data.reference_table.num_external_nodes = 0
        data.reference_table.external_folders = None
        data.reference_table.external_nodes = []

    new_bytes = GbxStruct.build(data, gbx_data=gbx_data, nodes=nodes)

    return new_bytes

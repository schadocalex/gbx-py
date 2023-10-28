# pyinstaller.exe --onefile --paths=./ export_obj_script.py

import sys
import os
from gbx_editor import parse_node
from export_obj import export_obj

from construct import Container

if __name__ == "__main__":
    file = sys.argv[1]

    data, nb_nodes, win = parse_node(file, True, need_ui=False)
    print(f"total nodes: {nb_nodes}")

    export_dir = os.path.dirname(file) + "\\ExportObj\\"
    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    # export obj
    for node_index, node in enumerate(data.nodes):
        # offset = 0
        if type(node) == Container and node.header.class_id == 0x090BB000:
            obj_chunk = node.body[0].chunk
            for i, geom in enumerate(obj_chunk.shaded_geoms):
                idx = obj_chunk.visuals[geom.visual_index]

                root_node = data  # node if "nodes" in node else node.root_node

                vertices = root_node.nodes[idx + 1].body[0].chunk.vertices_coords
                normals = root_node.nodes[idx + 1].body[0].chunk.normals
                uv0 = root_node.nodes[idx + 1].body[0].chunk.others.uv0
                indices = root_node.nodes[idx].body[8].chunk.index_buffer[0].chunk.indices
                obj_filepath = (
                    export_dir + os.path.basename(file).split(".")[0] + f"_{node_index}_lod{geom.lod}_{idx}.obj"
                )
                mat_idx = obj_chunk.custom_materials[geom.material_index].material_user_inst
                mat = root_node.nodes[mat_idx].body[0].chunk.link
                print(obj_filepath)
                export_obj(obj_filepath, vertices, normals, uv0, indices, mat, False)

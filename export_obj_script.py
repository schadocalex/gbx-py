# pyinstaller.exe --onefile --paths=./ export_obj_script.py

import sys
import os
from src.parser import parse_node
from src.utils_bloc import extract_meshes
from export_obj import export_obj

from construct import Container

if __name__ == "__main__":
    export_folder = "export_obj"
    blender_space = False

    item_data, nb_nodes, win = parse_node(sys.argv[1])
    print(f"total nodes: {nb_nodes}")

    item_data.filepath = item_data.body[2].chunk.name

    entity_model = item_data.nodes[item_data.body[12].chunk.EntityModel]
    all_meshes = extract_meshes(item_data, entity_model)
    for filepath, meshes, all_pos, all_rot in all_meshes:
        export_folder_file = export_folder + os.sep + filepath + os.sep
        for idx, obj_params in enumerate(meshes):
            if not os.path.exists(export_folder_file):
                os.makedirs(export_folder_file)
            obj_filepath = export_folder_file + f"mesh{idx}_lod{obj_params[-1]}.obj"
            export_obj(
                obj_filepath,
                *obj_params,
                pos=all_pos,
                rot=all_rot,
                blender_space=blender_space,
            )

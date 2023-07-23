import os
import glob

from multiprocessing import Pool

from runtime_params import get_extract_tm2020_path
from items_list import items_filepaths
from gbx_parser import GbxStructWithoutBodyParsed


def construct_all_folders(all_folders, parent_folder_path, current_folder):
    for folder in current_folder.folders:
        all_folders.append(parent_folder_path + folder.name + "/")
        construct_all_folders(all_folders, all_folders[-1], folder)


def get_external_folders(data, filepath):
    external_folders = data.reference_table.external_folders
    root_folder_name = os.path.dirname(filepath) + "/"
    all_folders = [root_folder_name]
    if external_folders is not None:
        root_folder_name += "../" * external_folders.ancestor_level
        construct_all_folders(all_folders, root_folder_name, external_folders)

    return all_folders


def get_missing_files(filepath):
    if not os.path.exists(filepath):
        return [filepath]

    with open(filepath, "rb") as f:
        raw_bytes = f.read()

        gbx_data = {}
        nodes = []
        try:
            data = GbxStructWithoutBodyParsed.parse(
                raw_bytes, gbx_data=gbx_data, nodes=nodes, filename=filepath
            )
        except:
            return [filepath]

        all_sub_missing_files = []

        external_folders = get_external_folders(data, filepath)
        for external_node in data.reference_table.external_nodes:
            if not external_node.ref.endswith(
                ".gbx"
            ) and not external_node.ref.endswith(".Gbx"):
                continue
            else:
                ext_node_filepath = os.path.normpath(
                    external_folders[external_node.folder_index] + external_node.ref
                )
                all_sub_missing_files += get_missing_files(ext_node_filepath)

        return all_sub_missing_files


if __name__ == "__main__":
    all_missing_files = []

    all_filepaths = (
        glob.glob(
            "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\GameCtnBlockInfo\\GameCtnBlockInfoClassic\\*.EDClassic.Gbx",
        )
        + items_filepaths
    )
    all_filepaths = items_filepaths

    with Pool(20) as p:
        res = p.map(get_missing_files, all_filepaths)
        all_missing_files = set()
        for root_files in res:
            for file in root_files:
                all_missing_files.add(file)

    with open("missing_files.txt", "w") as f:
        for missing_file in all_missing_files:
            f.write(missing_file + "\n")

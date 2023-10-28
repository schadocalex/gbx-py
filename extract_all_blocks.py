import os
import sys
import datetime
import json
from glob import glob

from construct import Container, ListContainer
from PySide6.QtWidgets import QApplication
from PIL import Image, ImageDraw

from src.parser import parse_node, generate_node, parse_node_recursive
from src.editor import GbxEditorUi
from src.utils_bloc import extract_block_meshes2
from export_obj import export_ents, extract_solid2model, export_meshes

if __name__ == "__main__2":
    idx = 0
    for file in glob(
        r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClassic\*"
    ):
        idx += 1
        data, nb_nodes, raw_bytes = parse_node_recursive(file)
        extract_block_meshes(os.path.basename(file), data)
    # win = GbxEditorUi(raw_bytes, data)

    # app = QApplication.instance() or QApplication(sys.argv)
    # app.exec()

if __name__ == "__main__1":
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\TreeGen\\FinishTechnics.Prefab.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Static\Deco\SpeedometerLight.StaticObject.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Items\GateMultilapLeft8m.Item.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Prefab\Items\Gate\MultilapLeft8m.Prefab.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Items\GateCheckpointLeft8m.Item.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Prefab\Items\Gate\Checkpoint_Helper.Prefab.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Prefab\Items\Gate\CheckpointLeft8m.Prefab.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Items\ShowFogger8m.Item.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Prefab\RoadBump\BranchStraightX4Left_Air.Prefab.Gbx"

    data, nb_nodes, raw_bytes = parse_node_recursive(file)
    export_ents(
        "./ExportObj/BranchStraightX4Left_Air/", "BranchStraightX4Left_Air", data
    )
    win = GbxEditorUi(raw_bytes, data)
    app = QApplication.instance() or QApplication(sys.argv)
    app.exec()

if __name__ == "__main__2":
    app = QApplication.instance() or QApplication(sys.argv)

    file = r"C:\Users\schad\Documents\Trackmania\Items\Stade1536.Mesh.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClip\RoadBumpFC.EDClip.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Prefab\TrackWall\BranchCross_FCB.Prefab.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClassic\RoadBumpBranchCross.EDClassic.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClassic\RoadBumpBranchStraightX4Left.EDClassic.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClassic\RoadBumpCheckpoint.EDClassic.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClassic\RoadBumpChicaneX2Left.EDClassic.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Prefab\TrackBorders\SpecialStraight.Prefab.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClassic\RoadBumpSpecialBoost.EDClassic.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Prefab\RoadTech\Checkpoint_DiagRight_Trigger.Shape.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Modifier\TurboRoulette.TerrainModifier.Gbx"
    file = r"C:\Users\schad\Documents\Trackmania\Scripts\gbx-py\export\Users\schad\Documents\Trackmania\Items\Z45_LoopStartCakeOut32_7.Item.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClip\TrackWallVFCTiltRight.EDVerticalClip.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\GameCtnBlockInfo\GameCtnBlockInfoClassic\RoadBumpBranchStraightX4Left.EDClassic.Gbx"
    file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Media\Prefab\RoadBump\BranchStraightX4Left_Air.Prefab.Gbx"

    data, nb_nodes, raw_bytes = parse_node_recursive(file)

    # meshes = extract_solid2model(data, data.nodes[3])
    # export_meshes("./ExportObj/", os.path.basename(file), meshes)

    # extract_block_meshes(os.path.basename(file), data)

    win = GbxEditorUi(raw_bytes, data)
    app.exec()

if __name__ == "__main__2":
    base_folder = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\"
    export_folder = ".\\blocksExport\\"
    print(base_folder)
    all_blocks = glob(
        base_folder
        + r"Stadium\GameCtnBlockInfo\GameCtnBlockInfoClassic\RoadBumpBranchStraightX4Left*.EDClassic.Gbx"
    )
    print(len(all_blocks))

    files = glob(export_folder + "**", recursive=True)
    files = [f.replace(export_folder, base_folder) for f in files if f.endswith("bx")]

    result = {
        "base_folder": base_folder,
        "export_folder": export_folder,
        "extracted_files": set(files),
    }
    blocks = []
    clips_to_extract = set()

    for i, blockfile in enumerate(all_blocks):
        print(str(i + 1) + "/" + str(len(all_blocks)))
        data, nb_nodes, raw_bytes = parse_node_recursive(blockfile)
        block = extract_block_meshes2(result, os.path.basename(blockfile), data)
        blocks.append(block)
        for variant in block["variants"].values():
            for block_unit in variant["blocks_units"]:
                for prop in (
                    "clipsNorth",
                    "clipsEast",
                    "clipsSouth",
                    "clipsWest",
                    "clipsTop",
                    "clipsBottom",
                ):
                    for clipfile in block_unit[prop]:
                        clips_to_extract.add(clipfile)

    clips = []
    for clipfile in clips_to_extract:
        data, nb_nodes, raw_bytes = parse_node_recursive(base_folder + clipfile)
        clips.append(extract_block_meshes2(result, os.path.basename(clipfile), data))

    tm_json = {
        "blocks": sorted(blocks, key=lambda b: b["id"]),
        "clips": sorted(clips, key=lambda b: b["id"]),
    }
    with open(export_folder + "tm2.json", "w") as fp:
        json.dump(tm_json, fp)

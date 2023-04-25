import os
import sys
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QTextEdit,
)
from PySide6.QtCore import Slot, QSize, Qt
from PySide6.QtGui import QTextCursor

from gbx_parser import GbxPose3D, GbxStruct, GbxStructWithoutBodyParsed
from construct import Container, ListContainer, RawCopy, Struct, Adapter, Subconstruct

from widgets.hex_editor import GbxHexEditor
from widgets.inspector import Inspector

from export_obj import export_obj, export_obj2


def container_iter(ctn):
    for key, value in ctn.items():
        if key != "_io":
            yield key, value


class QTreeWidgetItem_WithData(QTreeWidgetItem):
    def __init__(self, data, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.gbx_data = data


def tree_widget_item(key, value):
    if isinstance(value, Container):
        item = QTreeWidgetItem([key])
        for child in container_iter(value):
            item.addChild(tree_widget_item(*child))

        return item
    elif isinstance(value, ListContainer):
        item = QTreeWidgetItem([key, f"Array({len(value)})"])

        for i, child in enumerate(value):
            item.addChild(tree_widget_item(str(i), child))

        return item
    else:
        if type(value).__name__ == "bytes":
            return QTreeWidgetItem_WithData(
                Container(type=type(value).__name__, value=value),
                [
                    key,
                    type(value).__name__,
                    str(value[:12]) + ("..." if len(value) > 12 else ""),
                ],
            )
        return QTreeWidgetItem_WithData(
            Container(type=type(value).__name__, value=value),
            [key, type(value).__name__, str(value)],
        )


def GbxDataViewer(data, on_item_select):
    tree = QTreeWidget()
    tree.setColumnCount(3)
    tree.setHeaderLabels(["Name", "Type", "Value"])

    for key, value in container_iter(data):
        tree.addTopLevelItem(tree_widget_item(key, value))

    tree.expandToDepth(3)
    tree.resizeColumnToContents(0)
    tree.resizeColumnToContents(1)
    tree.resizeColumnToContents(2)

    @Slot()
    def on_item_double_clicked(item: QTreeWidgetItem, col):
        if isinstance(item, QTreeWidgetItem_WithData):
            if item.gbx_data.type == "bytes":
                on_item_select(item.gbx_data.value)

    tree.itemDoubleClicked.connect(on_item_double_clicked)

    return tree


def GbxEditorUi(raw_bytes, parsed_data):
    # window

    app = QApplication.instance() or QApplication(sys.argv)

    window = QMainWindow()
    window.resize(QSize(1600, 1000))

    # widgets

    inspector = Inspector()

    def on_select(raw_bytes, selection):
        inspector.inspect(raw_bytes, selection)

    hex_editor = GbxHexEditor(on_select)
    hex_editor.set_bytes(raw_bytes)

    def on_item_select(new_bytes):
        hex_editor.set_bytes(new_bytes)
        inspector.inspect(new_bytes, [])

    tree = GbxDataViewer(parsed_data, on_item_select)

    # layout

    layout_v = QVBoxLayout()
    layout_v.addWidget(hex_editor)
    layout_v.addWidget(inspector)

    layout_h = QHBoxLayout()
    layout_h.addWidget(tree)
    layout_h.addLayout(layout_v)

    widget = QWidget()
    widget.setLayout(layout_h)
    window.setCentralWidget(widget)
    window.show()
    # app.exec()

    return window


def wrapStruct(struct):
    if isinstance(struct, Struct):
        return RawCopy(Struct(*[wrapStruct(s) for s in struct.subcons]))
    else:
        return RawCopy(struct)


def construct_all_folders(all_folders, parent_folder_path, current_folder):
    for folder in current_folder.folders:
        all_folders.append(parent_folder_path + folder.name + "\\")
        construct_all_folders(all_folders, all_folders[-1], folder)


def create_custom_material(material_name):
    return Container(
        header=(Container(class_id=0x090FD000)),
        body=ListContainer(
            [
                Container(
                    chunk_id=0x090FD000,
                    chunk=Container(
                        version=11,
                        is_using_game_material=True,
                        material_name="",
                        model="",
                        base_texture="",
                        surface_physic_id=16,
                        surface_gameplay_id=0,
                        link="Stadium\\Media\\Material\\" + material_name,
                        csts=[],
                        color=[],
                        uv_anim=[],
                        u07=[],
                        user_textures=[],
                        hiding_group="",
                    ),
                ),
                Container(
                    chunk_id=0x090FD001,
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
                Container(chunk_id=0x090FD002, chunk=Container(version=0, u01=0)),
                Container(
                    chunk_id=0xFACADE01,
                ),
            ]
        ),
    )


def create_custom_material2(material_name):
    return Container(
        header=(Container(class_id=0x090FD000)),
        body=ListContainer(
            [
                Container(
                    chunk_id=0x090FD000,
                    chunk=Container(
                        version=11,
                        isUsingGameMaterial=False,
                        materialName="TM_" + material_name + "_asset",
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
                    chunk_id=0x090FD001,
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
                Container(chunk_id=0x090FD002, chunk=Container(version=0, u01=0)),
                Container(
                    chunk_id=0xFACADE01,
                ),
            ]
        ),
    )


def parse_node(file_path, parse_deps=True, node_offset=0, path=None, need_ui=True):
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

        return (
            data,
            nb_nodes,
            GbxEditorUi(raw_bytes, data) if need_ui else None,
        )


def generate_node(data):
    gbx_data = {}
    nodes = data.nodes[:]

    # compression
    data.header.body_compression = "compressed"

    # remove external nodes because we merge them
    data.reference_table.num_external_nodes = 0
    data.reference_table.external_folders = None
    data.reference_table.external_nodes = []

    new_bytes = GbxStruct.build(data, gbx_data=gbx_data, nodes=nodes)
    for n in nodes:
        if n is not None and type(n) is not str:
            print(f"node not referenced {n.path}")

    # check built node
    gbx_data = {}
    nodes = []
    new_data = GbxStruct.parse(new_bytes, gbx_data=gbx_data, nodes=nodes)
    new_data.nodes = ListContainer(nodes)

    # data2 = GbxStructWithoutBodyParsed.parse(new_bytes, gbx_data={}, nodes=[])
    # data2.header.body_compression = "uncompressed"
    # new_bytes_uncompressed = GbxStructWithoutBodyParsed.build(
    #     data2, gbx_data={}, nodes=[]
    # )

    return new_bytes, GbxEditorUi(new_bytes, new_data)


def cactus(data):
    # author
    data.header.chunks.data[0].meta.id = ""
    data.header.chunks.data[0].meta.author = "schadocalex"
    data.header.chunks.data[0].catalog_position = 1
    data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])
    data.body[1].chunk.meta.id = ""
    data.body[1].chunk.meta.author = "schadocalex"
    data.body[5].chunk.catalogPosition = 1

    # dont use hit shape, else won't load (maybe due to materials, todo explore)
    # data.nodes[2] = data2.nodes[2]
    # data.nodes[2].body.mesh = 5
    # data.nodes[2].body.collidable = True
    # data.nodes[2].body.collidableRef = None

    # change material to custom materials (for now)
    data.nodes[5].body[0].chunk.material_count = 2
    data.nodes[5].body[0].chunk.list_version_02 = None
    data.nodes[5].body[0].chunk.materialFolderName = "Stadium\\Media\\Material\\"
    data.nodes[5].body[0].chunk.custom_materials = ListContainer(
        [
            Container(
                material_name="",
                material_user_inst=data.nodes[5].body[0].chunk.materials[0],
            ),
            Container(
                material_name="",
                material_user_inst=data.nodes[5].body[0].chunk.materials[1],
            ),
        ]
    )
    data.nodes[5].body[0].chunk.materials = None

    # change surf mats
    # data.nodes[6].body[0].chunk.materials[0].hasMaterial = True
    # data.nodes[6].body[0].chunk.materials[0].materialsId = (
    #     data.nodes[6].body[0].chunk.materialsIds[0]
    # )
    # data.nodes[6].body[0].chunk.materials[1].hasMaterial = True
    # data.nodes[6].body[0].chunk.materials[1].materialsId = (
    #     data.nodes[6].body[0].chunk.materialsIds[1]
    # )
    data.nodes[6].body[0].chunk.materials = ListContainer([])

    # bypass variants
    data.nodes[1].header.class_id = 0x2E027000
    data.nodes[1].body = ListContainer(
        [
            Container(
                chunk_id=0x2E027000,
                chunk=Container(
                    version=4,
                    static_object=2,
                ),
            ),
            Container(chunk_id=0xFACADE01),
        ]
    )

    # snap positions
    # data.nodes[4].body[1].chunk.content.flags = 32 + 1
    data.nodes[4].body[1].chunk.content.pivotPositions = ListContainer(
        [Container(x=0, y=0, z=0), Container(x=0, y=7, z=0)]
    )
    data.nodes[4].body[2].chunk.content.magnetLocs = ListContainer(
        [Container(x=0, y=7, z=0, yaw=0, pitch=-90, roll=0)]
    )

    return generate_node(data)


def rotator(data):
    for node in data.nodes:
        if node and node.header.class_id == 0x090BB000:
            update_090BB000(node)

    # author
    # data.header.chunks.data[0].meta.id = ""
    # data.header.chunks.data[0].meta.author = "schadocalex"
    # data.header.chunks.data[0].catalog_position = 1
    # data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    if data.header.class_id == 0x2E002000:
        data.body[1].chunk.meta.id = ""
        data.body[1].chunk.meta.author = "schadocalex"
        data.body[5].chunk.catalogPosition = 1

    # remove modifier?
    data.body[12].chunk.modifier = -1

    # # dont use hit shape, else won't load (maybe due to materials, todo explore)
    # # data.nodes[2] = data2.nodes[2]
    # # data.nodes[2].body.mesh = 5
    # # data.nodes[2].body.collidable = True
    # # data.nodes[2].body.collidableRef = None

    # # change material to custom materials (for now)

    # # change surf mats
    # # data.nodes[6].body[0].chunk.materials[0].hasMaterial = True
    # # data.nodes[6].body[0].chunk.materials[0].materialsId = (
    # #     data.nodes[6].body[0].chunk.materialsIds[0]
    # # )
    # # data.nodes[6].body[0].chunk.materials[1].hasMaterial = True
    # # data.nodes[6].body[0].chunk.materials[1].materialsId = (
    # #     data.nodes[6].body[0].chunk.materialsIds[1]
    # # )
    # data.nodes[6].body[0].chunk.materials = ListContainer([])

    # # bypass variants
    # data.nodes[1].header.class_id = 0x2E027000
    # data.nodes[1].body = ListContainer(
    #     [
    #         Container(
    #             chunk_id=0x2E027000,
    #             chunk=Container(
    #                 version=4,
    #                 static_object=2,
    #             ),
    #         ),
    #         Container(chunk_id=0xFACADE01),
    #     ]
    # )

    # # snap positions
    # # data.nodes[4].body[1].chunk.content.flags = 32 + 1
    # data.nodes[4].body[1].chunk.content.pivotPositions = ListContainer(
    #     [Container(x=0, y=0, z=0), Container(x=0, y=7, z=0)]
    # )
    # data.nodes[4].body[2].chunk.content.magnetLocs = ListContainer(
    #     [Container(x=0, y=7, z=0, yaw=0, pitch=-90, roll=0)]
    # )

    return generate_node(data)


def update_090BB000(node):
    # change material to custom materials

    node.body[0].chunk.list_version_02 = None
    node.body[0].chunk.materialFolderName = "Stadium\\Media\\Material\\"

    custom_materials = []
    for mat in node.body[0].chunk.materials:
        custom_materials.append(
            Container(
                material_name="",
                material_user_inst=mat,
            )
        )

    node.body[0].chunk.material_count = len(custom_materials)
    node.body[0].chunk.custom_materials = ListContainer(custom_materials)
    node.body[0].chunk.materials = None

    # remove lights
    node.body[0].chunk.lights = ListContainer([])


def update_0900C000(node):
    # remove native materials from surf
    node.body[0].chunk.materials = ListContainer([])


def trigger(data, data2):
    for node in data.nodes:
        if type(node) == Container:
            if node.header.class_id == 0x090BB000:
                update_090BB000(node)
            if node.header.class_id == 0x0900C000:
                update_0900C000(node)

    # author
    data.header.chunks.data[0].meta.id = ""
    data.header.chunks.data[0].meta.author = "schadocalex"
    data.header.chunks.data[0].catalog_position = 1
    data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    if data.header.class_id == 0x2E002000:
        data.body[1].chunk.meta.id = ""
        data.body[1].chunk.meta.author = "schadocalex"
        data.body[5].chunk.catalogPosition = 1

    # replace static model
    # data.nodes[1].header.class_id = 0x2E027000
    # data.nodes[1].body = ListContainer(
    #     [
    #         Container(
    #             chunk_id=0x2E027000,
    #             chunk=Container(
    #                 version=4,
    #                 staticObject=1,
    #             ),
    #         ),
    #         Container(chunk_id=0xFACADE01),
    #     ]
    # )
    # change surf mats
    # data.nodes[6].body[0].chunk.materials[0].hasMaterial = True
    # data.nodes[6].body[0].chunk.materials[0].materialsId = (
    #     data.nodes[6].body[0].chunk.materialsIds[0]
    # )
    # data.nodes[6].body[0].chunk.materials[1].hasMaterial = True
    # data.nodes[6].body[0].chunk.materials[1].materialsId = (
    #     data.nodes[6].body[0].chunk.materialsIds[1]
    # )
    # data.nodes[1].body.url = ""

    # data.nodes[1].body.subEntityModelsCount = 1
    # data.nodes[1].body.subEntityModels = ListContainer(
    #     [data.nodes[1].body.subEntityModels[0]]
    # )

    # data.nodes[1].body.subEntityModels[1].model = 1
    # data.nodes[1].body.subEntityModels[1].pos.x = 16

    # remove modifier?
    # data.body[12].chunk.modifier = -1

    # # dont use hit shape, else won't load (maybe due to materials, todo explore)
    # data.nodes[4].update(data2.nodes[2])
    # data.nodes[4].body.mesh = 2

    # data.nodes[4].body.collidable = False
    # data.nodes[4].body.collidableRef = None
    # data.nodes[4].body.uRest = data2.nodes[2].body.uRest
    # data.nodes[56] = data2.nodes[13]

    return generate_node(data)


if __name__ == "__main__":
    file = "20_RectG_L32W32H05_#3.Item.Gbx"

    file = "Fall.Item.Gbx"
    file = "GateCheckpointCenter8mv2.Item.Gbx"
    file = "RampMedv2.Item.Gbx"
    file = "Z47_LoopStartCakeOut16_#7.Item.Gbx"
    file = "test_circle.Item.Gbx"
    file = "TunnelSupportPillarLarge16m.Item.Gbx"

    file = "Cactus.StaticObject.Gbx"
    file = "CactusMedium.Item.Gbx"
    file = "CactusB.StaticObject.Gbx"
    file = "Cactus.Mesh.Gbx"

    file = "C:\\Users\\schad\\Documents\\Trackmania\\Scripts\\test.Item.Gbx"
    file = "C:\\Users\\schad\\Documents\\Trackmania\\Scripts\\test_boost2.Item.Gbx"

    # file = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\RTCP.Item.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\CactusMedium.Item.Gbx"
    file = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\test_gbx2.Item.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\PlaceParam\\RoadSign.PlaceParam.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\PlaceParam\\TunnelSupport.PlaceParam.Gbx"
    file = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\test_circle.Item.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\CactusVerySmall.Item.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Static\\Vegetation\\CactusE.Mesh.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Dyna\\ObstaclePusher\\ObstaclePusher8mPiston.Mesh.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Dyna\\ObstaclePusher\\ObstaclePusher8mPiston.DynaObject.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Dyna\\Flag\\Flag.DynaObject.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Dyna\\Flag\\Flag.Mesh.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\Flag16m.Item.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Items\\Flag\\Flag16m.Prefab.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\FallTreeSmall.Item.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\VegetTreeModel\\FallTreeVerySmall.VegetTreeModel.Gbx"

    file = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\Straight_Air.Prefab.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Water\\Base_Air.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Water\\WallCross_Air.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Water\\WallVFCMiddle_Air.Prefab.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\TrackToGrass\\Straight.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\GameCtnBlockInfo\\GameCtnBlockInfoClassic\\RoadTechStraight.EDClassic.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\RoadTech\\Straight_Air.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\GameCtnBlockInfo\\GameCtnBlockInfoClassic\\StructureSupportCross.EDClassic.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Structure\\Pillar_FCBGround.Prefab.Gbx"

    file = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\Clouds\\Media\\Solid\\Cloudy\\Cloudy01.Solid.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\ShowFogger16M.Item.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Static\\Vegetation\\CactusB.Mesh.Gbx"
    file = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\test_circle.Item.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\Winter.Item.Gbx"

    file = "C:\\Users\\schad\\Openplanet4\\Extract\\GameData\\Items\\Valley\\Trains\\Loco.Item.Gbx"
    file = "C:\\Users\\schad\\Openplanet4\\Extract\\GameData\\Valley\\Media\\Mesh\\Loco.Mesh.gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\ObstaclePusher4m.Item.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Items\\ObstaclePusher\\ObstaclePusher4m.Prefab.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\SupportTubeStraightX1.Item.Gbx"
    file = "C:\\Users\\schad\\Documents\\Trackmania\\Materials\\test.Mat.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Material\\ItemCactus.Material.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\CactusMedium.Item.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\ObstacleTube6m.Item.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Items\\ObstacleTube\\ObstacleTube6m.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\ObstacleTube6mRotateLevel1.Item.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\InflatableMat4mCurve3.Item.Gbx"

    file = "C:\\Users\\schad\\Documents\\Maniaplanet\\Items\\test.Mesh.Gbx"
    file = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\test.Item.Gbx"

    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Items\\Gate\\Special4m.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Items\\InflatableMat\\InflatableMat4mCurve3.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Items\\InflatableTube\\InflatableTubeStraight.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Items\\InflatableMat\\InflatableMat4mCurve3OutFC.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Items\\InflatableMat\\InflatableMat4mCurve3.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Prefab\\Items\\InflatableMat\\InflatableMat1mFC.Prefab.Gbx"
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\GateSpecial4mTurbo.Item.Gbx"

    data, nb_nodes, win = parse_node(file, True, need_ui=True)
    print(f"total nodes: {nb_nodes}")

    # file2 = "C:\\Users\\schad\\Documents\\Trackmania\\Materials\\wall2.Mat.Gbx"
    # # file2 = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Media\\Material_BlockCustom\\CustomBricks.Material.Gbx"
    # # file2 = "C:\\Users\\schad\\Documents\\Maniaplanet\\Materials\\wall.Mat.Gbx"
    # file2 = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\test_circle.Item.Gbx"
    # data2, nb_nodes2, win2 = parse_node(file2, False, need_ui=True)

    # with open("result.csv", "w") as f:
    #     import glob

    #     for filename in glob.glob(
    #         "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\*.Item.Gbx"
    #     ):
    #         data, nb_nodes, win2 = parse_node(filename, False, need_ui=False)
    #         for ext in data.reference_table.external_nodes:
    #             f.write(f"\t{ext.node_index}\t{ext.ref}")
    #         f.write(f"\n")

    # for chunk in data.body:
    #     if chunk is not None and chunk.chunk_id == 0x2E00201E:
    #         f.write(
    #             f"{chunk.chunk.u01} \t {chunk.chunk.u02} \t {chunk.chunk.u03} "
    #         )
    #     if chunk is not None and chunk.chunk_id == 0x2E00201F:
    #         f.write(
    #             f"\t {chunk.chunk.u01} \t {chunk.chunk.u02} \t {chunk.chunk.u03} \t {chunk.chunk.u04}\n"
    #         )

    # Export obj
    # for node in data.nodes:
    #     if type(node) == Container and node.header.class_id == 0x090BB000:
    #         obj_chunk = node.body[0].chunk
    #         for i, geom in enumerate(obj_chunk.shaded_geoms):
    #             export_dir = (
    #                 "C:\\Users\\schad\\Documents\\Trackmania\\Items\\ExportObj\\"
    #             )
    #             idx = obj_chunk.visuals[geom.visual_index]
    #             vertices = data.nodes[idx + 1].body[0].chunk.vertices_coords
    #             normals = data.nodes[idx + 1].body[0].chunk.normals
    #             uv0 = data.nodes[idx + 1].body[0].chunk.others.uv0
    #             indices = data.nodes[idx].body[8].chunk.index_buffer[0].chunk.indices
    #             obj_filepath = (
    #                 export_dir
    #                 + os.path.basename(file).split(".")[0]
    #                 + f"_lod{geom.lod}_{idx}.obj"
    #             )
    #             mat_idx = obj_chunk.materials[geom.material_index]
    #             mat = data.nodes[mat_idx].body[0].chunk.material_name
    #             print(obj_filepath)
    #             export_obj(obj_filepath, vertices, normals, uv0, indices, mat)

    # for node in data.nodes:
    #     if node and node.header.class_id == 0x09145000:
    #         obj_chunk = node.nodes[node.nodes[node.body.u02].body.mesh].body[0].chunk
    #         for i, geom in enumerate(obj_chunk.shaded_geoms):
    #             export_dir = (
    #                 "C:\\Users\\schad\\Documents\\Trackmania\\Items\\ExportObj\\"
    #             )
    #             idx = obj_chunk.visuals[geom.visual_index]
    #             vertices = node.nodes[idx + 1].body[0].chunk.vertices_coords
    #             normals = node.nodes[idx + 1].body[0].chunk.normals
    #             uv0 = node.nodes[idx + 1].body[0].chunk.others.uv0
    #             indices = node.nodes[idx].body[8].chunk.index_buffer[0].chunk.indices
    #             obj_filepath = (
    #                 export_dir
    #                 + os.path.basename(file).split(".")[0]
    #                 + f"_lod{geom.lod}_{node.node_offset}_{idx}.obj"
    #             )
    #             mat_idx = obj_chunk.materials[geom.material_index]
    #             mat = node.nodes[mat_idx].body[0].chunk.material_name
    #             print(obj_filepath)
    #             export_obj(obj_filepath, vertices, normals, uv0, indices, mat)

    # Export surf
    # export_dir = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\"
    # surf_class = data.nodes[6]
    # surf_chunk = surf_class.body[0].chunk
    # vertices = surf_chunk.surf.data.vertices
    # mats = [
    #     surf_class.nodes[m.material].body[0].chunk.material_name
    #     for m in surf_chunk.materials
    # ]
    # faces = []
    # for tri in surf_chunk.surf.data.triangles:
    #     assert tri.materialIndex >= 0
    #     while tri.materialIndex >= len(faces):
    #         faces.append([])
    #     faces[tri.materialIndex].append(tri.face)
    # start_index = 0
    # for i in range(len(faces)):
    #     obj_filepath = export_dir + os.path.basename(file).split(".")[0] + f"_{i}.obj"
    #     export_obj2(
    #         obj_filepath,
    #         vertices,
    #         faces[i],
    #         mats[i],
    #     )
    #     start_index += len(faces[i])

    # Export obj animation (flag)
    # export_dir = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\"
    # vertices = [v.pos for v in data.nodes[3].body[7].chunk.vertices]
    # normals = [v.vert_u02 for v in data.nodes[3].body[7].chunk.vertices]
    # uv0 = [v.uv for v in data.nodes[3].body[4].chunk.tex_coord_sets[0].tex_coords]
    # indices = data.nodes[3].body[8].chunk.index_buffer[0].chunk.indices
    # sub_visuals = data.nodes[3].body[1].chunk.sub_visuals
    # for i, vis in enumerate(sub_visuals):
    #     start_index = vis.x
    #     if i == len(sub_visuals) - 1:
    #         end_index = len(vertices)
    #     else:
    #         end_index = sub_visuals[i + 1].x
    #     obj_filepath = (
    #         export_dir + os.path.basename(file).split(".")[0] + f"_lod4_{i}.obj"
    #     )
    #     export_obj(
    #         obj_filepath,
    #         vertices[start_index:end_index],
    #         normals[start_index:end_index],
    #         uv0[start_index:end_index],
    #         indices,
    #         "ItemFlag",
    #     )

    # MODIFICATIONS

    # data.nodes[3].body[0].chunk.materialFolderName = ""

    # data.nodes[6].body = data2.body
    # data.nodes[6].body[0].chunk.userTextures[
    #     0
    # ].texture = ":user:\\Materials\\RoadTech_D.dds"
    # # TODO test basetexture without .dds
    # bytes3, win3 = generate_node(data)

    # bytes3, win3 = cactus(data)
    # bytes3, win3 = rotator(data)
    # bytes3, win3 = trigger(data, data2)

    # with open(
    #     "C:\\Users\\schad\\Documents\\Trackmania\\Items\\Export\\"
    #     + os.path.basename(file).replace(".Item", ".Item"),
    #     "wb",
    # ) as f:
    #     f.write(bytes3)

    app = QApplication.instance() or QApplication(sys.argv)
    app.exec()

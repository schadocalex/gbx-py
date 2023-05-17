import datetime
import os
from pathlib import Path
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
from construct import (
    Container,
    Int32ul,
    ListContainer,
    RawCopy,
    Struct,
    Adapter,
    Subconstruct,
)

from widgets.hex_editor import GbxHexEditor
from widgets.inspector import Inspector

from export_obj import export_obj, export_obj2
from runtime_params import *

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
        all_folders.append(parent_folder_path + folder.name + "/")
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
                        link="Stadium/Media/Material/" + material_name,
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


def parse_node(file_path: Path, parse_deps=True, node_offset=0, path=None, need_ui=True):
    file_path = os.path.abspath(file_path)
    file_path2 = Path(str(file_path).replace(str(openplanet_tm2020_extract_base.absolute()), ""))
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

    with open(Path(file_path), "rb") as f:
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
        root_folder_name = os.path.dirname(file_path) + "/"
        all_folders = [root_folder_name]
        if external_folders is not None:
            root_folder_name += "../" * external_folders.ancestor_level
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
    data.header.chunks.data[0].meta.author = get_author_name()
    data.header.chunks.data[0].catalog_position = 1
    data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])
    data.body[1].chunk.meta.id = ""
    data.body[1].chunk.meta.author = get_author_name()
    data.body[5].chunk.catalogPosition = 1

    # dont use hit shape, else won't load (maybe due to materials, todo explore)
    # data.nodes[2] = data2.nodes[2]
    # data.nodes[2].body.mesh = 5
    # data.nodes[2].body.collidable = True
    # data.nodes[2].body.collidableRef = None

    # change material to custom materials (for now)
    data.nodes[5].body[0].chunk.material_count = 2
    data.nodes[5].body[0].chunk.list_version_02 = None
    data.nodes[5].body[0].chunk.materialFolderName = "Stadium/Media/Material/"
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
    # data.header.chunks.data[0].meta.author = get_author_name()
    # data.header.chunks.data[0].catalog_position = 1
    # data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    if data.header.class_id == 0x2E002000:
        data.body[1].chunk.meta.id = ""
        data.body[1].chunk.meta.author = get_author_name()
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
    node.body[0].chunk.materialFolderName = "Stadium/Media/Material/"

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

    # for materialId in node.body[0].chunk.materialsIds:
    #     materialId.gameplayId = "ReactorBoost2_Oriented"

    # for tri in node.body[0].chunk.surf.data.triangles:
    #     tri.materialId.gameplayId = "ReactorBoost2_Oriented"


def trigger(data, data2):
    for node in data.nodes:
        if type(node) == Container:
            if node.header.class_id == 0x090BB000:
                update_090BB000(node)
            if node.header.class_id == 0x0900C000:
                update_0900C000(node)

    # author
    data.header.chunks.data[0].meta.id = ""
    data.header.chunks.data[0].meta.author = get_author_name()
    data.header.chunks.data[0].catalog_position = 1
    data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    if data.header.class_id == 0x2E002000:
        data.body[1].chunk.meta.id = ""
        data.body[1].chunk.meta.author = get_author_name()
        data.body[5].chunk.catalogPosition = 1

    return generate_node(data)


def trigger2(data):
    for node in data.nodes:
        if type(node) == Container:
            # if node.header.class_id == 0x090BB000:
            #     update_090BB000(node)
            if node.header.class_id == 0x0900C000:
                update_0900C000(node)

    # author
    # data.header.chunks.data[0].meta.id = ""
    # data.header.chunks.data[0].meta.author = get_author_name()
    # data.header.chunks.data[0].catalog_position = 1
    # data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    # if data.header.class_id == 0x2E002000:
    #     data.body[1].chunk.meta.id = ""
    #     data.body[1].chunk.meta.author = get_author_name()
    #     data.body[5].chunk.catalogPosition = 1

    new_node_index = len(data.nodes)
    # data.nodes.append(data.nodes[7])
    data.nodes.append(
        Container(
            header=Container(class_id=0x09179000),
            body=Container(
                version=1,
                surf=7,
            ),
        )
    )

    data.nodes[1] = Container(
        header=Container(class_id=0x09145000),
        body=Container(
            version=11,
            creationTime=datetime.datetime.now(),
            url="",
            u01=b"\x00\x00\x00\x00",
            subEntityModelsCount=2,
            u02=b"\x00\x00\x00\x00",
            subEntityModels=ListContainer(
                [
                    Container(
                        model=2,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        params=None,
                        u01=b"\xff\xff\xff\xff\x00\x00\x00\x00",
                    ),
                    Container(
                        model=new_node_index,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        params=None,
                        u01=b"\xff\xff\xff\xff\x00\x00\x00\x00",
                    ),
                ]
            ),
        ),
    )

    data.nodes[2].body.isMeshCollidable = False
    data.nodes[2].body.collidableShape = -1

    data.body[16].chunk.u08 = 0

    return generate_node(data)


def rotator2(data):
    for node in data.nodes:
        if type(node) == Container:
            if node.header.class_id == 0x090BB000:
                update_090BB000(node)
            if node.header.class_id == 0x0900C000:
                update_0900C000(node)

    # author
    # data.header.chunks.data[0].meta.id = ""
    # data.header.chunks.data[0].meta.author = get_author_name()
    # data.header.chunks.data[0].catalog_position = 1
    # data.header.chunks.data[2] = bytes([0, 0, 0, 0, 0, 0, 0, 0])

    # if data.header.class_id == 0x2E002000:
    #     data.body[1].chunk.meta.id = ""
    #     data.body[1].chunk.meta.author = get_author_name()
    #     data.body[5].chunk.catalogPosition = 1

    data.body[15].chunk.baseItem = -1
    # data.body[12].chunk.MaterialModifier = -1
    data.nodes = data.nodes[:54]

    # data.nodes[6].body.rest = data2.body.rest

    return generate_node(data)


def rotator3(data):
    for node in data.nodes:
        if type(node) == Container:
            # if node.header.class_id == 0x090BB000:
            #     update_090BB000(node)
            if node.header.class_id == 0x0900C000:
                update_0900C000(node)

    data.nodes[2] = Container(
        header=Container(class_id=0x09144000),
        body=Container(
            version=13,
            isStatic=False,
            dynamizeOnSpawn=False,
            mesh=3,
            staticShape=data.nodes[1].body[0].chunk.props.triggerArea,
            dynaShape=data.nodes[1].body[0].chunk.props.triggerArea,
            breakSpeedKmh=100.0,
            mass=100.0,
            lightAliveDurationSc_Min=5.0,
            lightAliveDurationSc_Max=7.0,
            rest=b"\x01\x00\x00\x00\x01\x00\x00\x00\x04\x00\x01\x00\x00\x00\x0A\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00\xFF\xFF\xFF\xFF",
        ),
    )

    kinematic_node_index = len(data.nodes)
    data.nodes.append(
        Container(
            header=Container(class_id=0x2F0CA000),
            body=Container(
                version=0,
                subVersion=3,
                TransAnimFunc=Container(
                    TimeIsDuration=True,
                    SubFuncs=ListContainer(
                        [
                            Container(ease="Linear", reverse=False, duration=3000),
                            Container(ease="Linear", reverse=True, duration=3000),
                        ]
                    ),
                ),
                RotAnimFunc=Container(
                    TimeIsDuration=True,
                    SubFuncs=ListContainer(
                        [
                            Container(ease="Linear", reverse=False, duration=3000),
                            Container(ease="Linear", reverse=True, duration=3000),
                        ]
                    ),
                ),
                ShaderTcType="No",
                ShaderTcVersion=0,
                ShaderTcAnimFunc=ListContainer(
                    []
                    # [Container(duration=1000, u01=0), Container(duration=1000, u01=1)]
                ),
                ShaderTcData_TransSub=None,
                # Container(
                #     NbSubTexture=5,
                #     NbSubTexturePerLine=1,
                #     NbSubTexturePerColumn=8,
                #     TopToBottom=False,
                # ),
                transAxis="X",
                TransMin=-0.0,
                TransMax=0.0,
                rotAxis="Y",
                AngleMinDeg=-180.0,
                AngleMaxDeg=180.0,
            ),
        ),
    )

    data.nodes[1] = Container(
        header=Container(class_id=0x09145000),
        body=Container(
            version=11,
            creationTime=datetime.datetime.now(),
            url="",
            u01=b"\x00\x00\x00\x00",
            subEntityModelsCount=2,  # todo auto recompute
            u02=b"\x00\x00\x00\x00",
            subEntityModels=ListContainer(
                [
                    Container(
                        model=2,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        dynaParams=Container(
                            chunkId=0x2F0B6000,
                            textureId=2,
                            u01=1,
                            CastStaticShadow=False,
                            isKinematic=True,
                            u04=-1,
                            u05=-1,
                            u06=-1,
                        ),
                        u01=b"\xff\xff\xff\xff\x00\x00\x00\x00",
                    ),
                    Container(
                        model=kinematic_node_index,
                        rot=Container(x=0, y=0, z=0, w=1),
                        pos=Container(x=0, y=0, z=0),
                        constraintParams=Container(
                            chunkId=0x2F0C8000,
                            Ent1=0,
                            Ent2=-1,
                            Pos1=Container(x=0, y=0, z=0),
                            Pos2=Container(x=0, y=0, z=0),
                        ),
                        u01=b"\x00\x00\x00\x00\x00\x00\x00\x00",
                    ),
                ]
            ),
        ),
    )

    data.nodes[2].body.isMeshCollidable = False
    data.nodes[2].body.collidableShape = -1

    data.body[16].chunk.u08 = 0

    return generate_node(data)


if __name__ == "__main__":
    file = get_extract_mp4_path("GameData/Items/Valley/Trains/Loco.Item.Gbx")
    file = get_extract_mp4_path("GameData/Valley/Media/Mesh/Loco.Mesh.gbx")

    file = get_ud_tm2020_path("Items/CustomRotatingTube.Item.Gbx")
    file = get_ud_tm2020_path("Items/BigWheel.Item.Gbx")
    file = get_ud_tm2020_path("Items/RotatingLight.Item.Gbx")
    file = get_ud_tm2020_path("Items/BigCircleRotate.Item.Gbx")
    file = get_ud_tm2020_path("Items/CustomTransCube.Item.Gbx")
    file = get_extract_tm2020_path("GameData/Stadium/Items/ObstacleTube6mRotateLevel1.Item.Gbx")
    # file = get_extract_tm2020_path("GameData/Stadium/Items/Screen1x1.Item.Gbx")

    data, nb_nodes, win = parse_node(file, True, need_ui=True)
    print(f"total nodes: {nb_nodes}")

    # file2 = get_ud_tm2020_path("Materials/wall2.Mat.Gbx")
    # # file2 = get_extract_tm2020_path("GameData/Stadium/Media/Material_BlockCustom/CustomBricks.Material.Gbx")
    # # file2 = get_ud_mp4_path("Materials/wall.Mat.Gbx")
    # file2 = get_ud_tm2020_path("Items/test_circle.Item.Gbx")
    # file2 = (
    #     get_ud_tm2020_path("Items/GateSpecial4mTurbo.Item.Gbx")
    # )

    if False:
        file2 = get_extract_tm2020_path("GameData/Stadium/Items/ObstacleTurnstile4mSimpleOscillateLevel0.Item.Gbx")
        file2 = get_extract_tm2020_path("GameData/Stadium/Media/Modifier/ItemObstacleDiscontinuous/AnimTurnstileLevel0.KinematicConstraint.Gbx")
        file2 = get_extract_tm2020_path("GameData/Stadium/Media/Modifier/ItemObstacle/AnimPusher4mLevel2.KinematicConstraint.Gbx")
        file2 = get_extract_tm2020_path("GameData/Stadium/Items/ObstaclePusher4mLevel0.Item.Gbx")

        data2, nb_nodes2, win2 = parse_node(file2, True, need_ui=True)

    # bytes3, win3 = cactus(data)
    # bytes3, win3 = rotator(data)
    # bytes3, win3 = trigger(data, data2)
    # bytes3, win3 = trigger2(data)
    # bytes3, win3 = rotator2(data)
    # bytes3, win3 = rotator3(data)

    # with open(
    #     get_ud_tm2020_path("Items/Export/")
    #     + os.path.basename(file).replace(".Item", ".Item"),
    #     "wb",
    # ) as f:
    #     f.write(bytes3)

    # with open("result2.csv", "w") as f:
    #     import glob

    #     already_written = set()

    #     for filename in glob.glob(
    #         # get_extract_tm2020_path("GameData/Stadium/Items/*.Item.Gbx",)
    #         get_ud_tm2020_path("Items/**/*.Item.Gbx",)
    #         recursive=True,
    #     ):
    #         try:
    #             data, nb_nodes, win2 = parse_node(filename, True, need_ui=False)
    #         except:
    #             continue

    #         # f.write(f"{data.body[16].chunk.u02}\n")
    #         # f.flush()

    #         #         # for ext in data.reference_table.external_nodes:
    #         #         #     f.write(f"\t{ext.node_index}\t{ext.ref}")
    #         for node in data.nodes:
    #             if type(node) == Container and node.header.class_id == 0x090BB000:
    #                 # if node.path[-1] in already_written:
    #                 #     continue
    #                 # already_written.add(node.path[-1])

    #                 if "chunk_parse_failed" not in node.body[0].chunk:
    #                     f.write(
    #                         f"{os.path.basename(filename)}\t{node.body[0].chunk.u14}\n"
    #                     )
    #                     f.flush()

    #                 text = ""
    #                 for b in node.body.u01[::-1]:
    #                     text += format(b, "02X")
    #                 x = Int32ul.parse(node.body.u01)

    #                 # text2 = ""
    #                 # for model in node.body.subEntityModels:
    #                 #     if 0 < model.model < len(node.nodes):
    #                 #         mesh = node.nodes[model.model]
    #                 #         if (
    #                 #             type(mesh) == Container
    #                 #             and mesh.header.class_id == 0x09159000
    #                 #         ):
    #                 #             mesh = node.nodes[mesh.body.mesh]
    #                 #             if (
    #                 #                 type(mesh) == Container
    #                 #                 and mesh.header.class_id == 0x090BB000
    #                 #             ):
    #                 #                 for lod in mesh.body[0].chunk.lodDistances:
    #                 #                     text2 += str(lod) + "\t"
    #                 #     text2 += str(model.LodGroupId) + "\t"

    #                 f.write(
    #                     f"{node.path[-1]}\t{text}\t{x}\t{node.body.subEntityModelsCount}\t{node.body.creationTime}\n"
    #                 )
    #                 f.flush()

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
    # for offset, node in enumerate(data.nodes):
    #     offset = 0
    #     if type(node) == Container and node.header.class_id == 0x090BB000:
    #         obj_chunk = node.body[0].chunk
    #         for i, geom in enumerate(obj_chunk.shaded_geoms):
    #             export_dir = (
    #                 get_ud_tm2020_path("Items/ExportObj/")
    #             )
    #             idx = obj_chunk.visuals[geom.visual_index]
    #             vertices = data.nodes[offset + idx + 1].body[0].chunk.vertices_coords
    #             normals = data.nodes[offset + idx + 1].body[0].chunk.normals
    #             uv0 = data.nodes[offset + idx + 1].body[0].chunk.others.uv0
    #             indices = (
    #                 data.nodes[offset + idx].body[8].chunk.index_buffer[0].chunk.indices
    #             )
    #             obj_filepath = (
    #                 export_dir
    #                 + os.path.basename(file).split(".")[0]
    #                 + f"_lod{geom.lod}_{idx}.obj"
    #             )
    #             mat_idx = obj_chunk.materials[geom.material_index]
    #             mat = data.nodes[offset + mat_idx].body[0].chunk.materialName
    #             print(obj_filepath)
    #             export_obj(obj_filepath, vertices, normals, uv0, indices, mat)

    # for node in data.nodes:
    #     if node and node.header.class_id == 0x09145000:
    #         obj_chunk = node.nodes[node.nodes[node.body.u02].body.mesh].body[0].chunk
    #         for i, geom in enumerate(obj_chunk.shaded_geoms):
    #             export_dir = (
    #                 get_ud_tm2020_path("Items/ExportObj/")
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
    # export_dir = get_ud_tm2020_path("Items/")
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
    # export_dir = get_ud_tm2020_path("Items/")
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

    app = QApplication.instance() or QApplication(sys.argv)
    app.exec()

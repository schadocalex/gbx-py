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

from gbx_parser import GbxStruct, GbxStructWithoutBodyParsed
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
                        is_using_game_material=False,
                        material_name="TM_" + material_name + "_asset",
                        model="",
                        base_texture="",
                        surface_physic_id=6,
                        surface_gameplay_id=0,
                        link=material_name,
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

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

        gbx_data = {}
        nodes = []
        print("  " * depth + f"- {file_path2}")
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
            if external_node.ref.endswith(".dds"):
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
                # continue
                # print(external_node)
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
    # data.header.body_compression = "uncompressed"
    new_bytes = GbxStruct.build(data, gbx_data=gbx_data, nodes=nodes)
    for n in nodes:
        if n is not None:
            print(f"node not referenced {n.path}")

    # check built node
    gbx_data = {}
    nodes = []
    new_data = GbxStruct.parse(new_bytes, gbx_data=gbx_data, nodes=nodes)
    new_data.nodes = ListContainer(nodes)

    data2 = GbxStructWithoutBodyParsed.parse(new_bytes, gbx_data={}, nodes=[])
    data2.header.body_compression = "uncompressed"
    new_bytes_uncompressed = GbxStructWithoutBodyParsed.build(
        data2, gbx_data={}, nodes=[]
    )

    return new_bytes, GbxEditorUi(new_bytes_uncompressed, new_data)


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
    file = "C:\\Users\\schad\\OpenplanetNext\\Extract\\GameData\\Stadium\\Items\\CactusMedium.Item.Gbx"

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

    data, nb_nodes, win = parse_node(file, False, need_ui=True)
    print(f"total nodes: {nb_nodes}")

    # Export obj better
    # obj_chunk = data.nodes[2].body[0].chunk
    # for i, geom in enumerate(obj_chunk.shaded_geoms):
    #     export_dir = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\"
    #     idx = obj_chunk.visuals[geom.visual_index]
    #     vertices = data.nodes[idx + 1].body[0].chunk.vertices_coords
    #     normals = data.nodes[idx + 1].body[0].chunk.normals
    #     uv0 = data.nodes[idx + 1].body[0].chunk.others.uv0
    #     indices = data.nodes[idx].body[8].chunk.index_buffer[0].chunk.indices
    #     obj_filepath = (
    #         export_dir
    #         + os.path.basename(file).split(".")[0]
    #         + f"_lod{geom.lod}_{idx}.obj"
    #     )
    #     mat_idx = obj_chunk.materials[geom.material_index]
    #     mat = data.nodes[mat_idx].body[0].chunk.material_name
    #     print(obj_filepath)
    #     export_obj(obj_filepath, vertices, normals, uv0, indices, mat)

    # Export surf
    # export_dir = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\"
    # surf_chunk = data.nodes[17].body[0].chunk
    # vertices = surf_chunk.surf.data.vertices
    # mats = [
    #     data.nodes[m.material].body[0].chunk.material_name for m in surf_chunk.materials
    # ]
    # faces = []
    # for tri in surf_chunk.surf.data.triangles:
    #     assert tri.material_index >= 0
    #     while tri.material_index >= len(faces):
    #         faces.append([])
    #     faces[tri.material_index].append(tri.face)
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

    # file2 = "C:\\Users\\schad\\Documents\\Trackmania\\Items\\test_gbx1.Item.Gbx"
    # data2, nb_nodes2, win2 = parse_node(file2)

    # MODIFICATIONS

    # compression
    # data.header.body_compression = "compressed"

    # author
    # data.header.chunks.data[0].meta.id = ""
    # data.header.chunks.data[0].meta.author = "schadocalex"
    # data.header.chunks.data[0].catalog_position = 1

    # merge external nodes
    # data.header.num_nodes = nb_nodes + 1
    # data.reference_table.num_external_nodes = 0
    # data.reference_table.external_folders = None
    # data.reference_table.external_nodes = []

    # bypass variants?
    # data.body[12].chunk.entity_model = 2

    # lightmap
    # data.body[16].chunk.disable_lightmap = True

    # make mesh not collidable
    # data.nodes[2].body.collidable = False
    # data.nodes[2].body.collidable_ref = -1

    # bytes3, win3 = generate_node(data)
    # with open(
    #     "C:\\Users\\schad\\Documents\\Trackmania\\Items\\Export\\"
    #     + os.path.basename(file).replace(".Item", ".Item"),
    #     "wb",
    # ) as f:
    #     f.write(bytes3)

    app = QApplication.instance() or QApplication(sys.argv)
    app.exec()

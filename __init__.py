import sys
import os

sys.path.append(os.path.dirname(__file__))

import bpy
import bmesh
from mathutils import Vector

# from src.nice.api import *
from src.parser import parse_file, generate_node
from src.utils.content import extract_content, RawMesh, Entities, RawMaterial

bl_info = {
    "name": "Nadeo Importer Community Edition (NICE)",
    "author": "schadocalex",
    "description": "Export custom items to TM2020 with new features",
    "blender": (3, 4, 0),
    "version": (1, 0, 0),
    "location": "View3D",
    "warning": "",
    "category": "Generic",
}


def create_raw_mesh(obj_name, raw_mesh):
    # create the mesh data
    mesh_data = bpy.data.meshes.new(f"{obj_name}_data")

    # create the mesh object using the mesh data
    mesh_obj = bpy.data.objects.new(f"{raw_mesh.label}{obj_name}", mesh_data)

    # materials
    for material in raw_mesh.materials:
        if isinstance(material, RawMaterial):
            material_name = material.link
            if raw_mesh.label != "_notcollidable_":
                if material.physicId is not None:
                    material_name += "_" + str(material.physicId)
                if material.gameplayId is not None:
                    material_name += "_" + str(material.gameplayId)
            if material.color is not None:
                material_name += "_".join(map(str, material.color))
        else:
            material_name = material

        # search in bpy.data.libraries["Trackmania2020_assets.blend"]
        if material_name in mesh_obj.data.materials:
            continue
        new_mat = bpy.data.materials.new(material_name)
        mesh_obj.data.materials.append(new_mat)

    # create a new bmesh
    bm = bmesh.new()

    # vertices
    for coord in raw_mesh.vertices:
        bm.verts.new((coord.x, -coord.z, coord.y))

    bm.verts.ensure_lookup_table()

    # normals, does that work?
    if raw_mesh.normals is not None:
        for vidx, normal in enumerate(raw_mesh.normals):
            bm.verts[vidx].normal = Vector((normal.x, -normal.z, normal.y))

    # faces
    for i, vert_indices in enumerate(raw_mesh.faces):
        try:
            face = bm.faces.new([bm.verts[vidx] for vidx in vert_indices])
        except:
            # faces can share the same vertices in solids
            # we need to duplicate vertices, as blender doesn't allow it
            new_vidx = len(raw_mesh.vertices)
            for vidx in vert_indices:
                raw_mesh.vertices.append(raw_mesh.vertices[vidx])
                coord = raw_mesh.vertices[-1]
                bm.verts.new((coord.x, -coord.z, coord.y))
            bm.verts.ensure_lookup_table()
            raw_mesh.faces[i] = (new_vidx, new_vidx + 1, new_vidx + 2)
            raw_mesh.facesMaterials.append(raw_mesh.facesMaterials[i])
            face = bm.faces.new([bm.verts[new_vidx], bm.verts[new_vidx + 1], bm.verts[new_vidx + 2]])

        face.material_index = raw_mesh.facesMaterials[i] if raw_mesh.facesMaterials is not None else 0

    # writes the bmesh data into the mesh data
    bm.to_mesh(mesh_data)

    # Add uvs
    if raw_mesh.uv0 is not None:
        uv0 = mesh_data.uv_layers.new(name="BaseMaterial", do_init=False)
        uv0.active = True
        uv0.active_render = True
        for idx, coord in uv0.uv.items():
            vt_idx = raw_mesh.faces[idx // 3][idx % 3]
            pt = raw_mesh.uv0[vt_idx]
            coord.vector = Vector((pt.x, pt.y))
    if raw_mesh.uv1 is not None:
        uv1 = mesh_data.uv_layers.new(name="Lightmap", do_init=False)
        for idx, coord in uv1.uv.items():
            vt_idx = raw_mesh.faces[idx // 3][idx % 3]
            if vt_idx < len(raw_mesh.uv1):
                pt = raw_mesh.uv1[vt_idx]
                coord.vector = Vector((pt.x, pt.y))

    # [Optional] update the mesh data (helps with redrawing the mesh in the viewport)
    mesh_data.update()

    # clean up/free memory that was allocated for the bmesh
    bm.free()

    return mesh_obj


def import_content_to_blender(collection, name, content):
    for idx, obj in enumerate(content):
        child_name = f"{name}_{idx}"
        if isinstance(obj, Entities):
            for i, model in obj.models.items():
                import_content_to_blender(collection, f"{child_name}_ent{i}", model)
        elif isinstance(obj, RawMesh):  # add the mesh object into the collection
            lod = f"_lod{obj.lod}" if obj.lod > 0 else ""
            collection.objects.link(create_raw_mesh(f"{child_name}{lod}", obj))
        else:
            print("Unknown: " + str(obj))


class TM_OT_NICE_Item_Import_Test(bpy.types.Operator):
    bl_idname = "view3d.import_item_test"
    bl_description = "Item_Import_Test"
    bl_label = "Item Import Test"

    def execute(self, context):
        file = r"C:\Users\schad\OpenplanetNext\Extract\GameData\Stadium\Items\Theme\SnowTempleDeadEnd.Item.Gbx"
        data = parse_file(file)

        content = extract_content(data)
        name = os.path.basename(file).split(".")[0]

        collection = bpy.data.collections.new("_nice_" + name)
        bpy.context.scene.collection.children.link(collection)

        import_content_to_blender(collection, "obj", content)
        return {"FINISHED"}


class TM_PT_NICE(bpy.types.Panel):
    bl_label = "NICE"
    bl_idname = "TM_PT_NICE"
    bl_context = "objectmode"
    # bl_parent_id = "TM_PT_Map_Manipulate"
    bl_category = "Blendermania"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon="SEQUENCE_COLOR_03")

    def draw_header_preset(self, context):
        layout = self.layout
        # tm_props = get_global_props()
        row = layout.row(align=True)

        col = row.column(align=True)
        op = col.operator("view3d.tm_open_messagebox", text="", icon="QUESTION")
        op.link = ""
        op.title = "Editor Trails Infos"
        # op.infos = TM_OT_Settings_OpenMessageBox.get_text(
        #     "Here you can configure editor trails settings",
        #     "-> Data will be received from http://localhost:42069/trails ",
        #     # "----> ",
        # )

    def draw(self, context):
        layout = self.layout
        scale_box = layout.box()

        row = scale_box.row()
        row.alert = True
        row.label(text="Blendermania dotnet installation required")

        row = scale_box.row()
        row.scale_y = 1.5
        text = f"Import item test"
        row.operator("view3d.import_item_test", text=text)


def register():
    bpy.utils.register_class(TM_OT_NICE_Item_Import_Test)
    bpy.utils.register_class(TM_PT_NICE)


def unregister():
    pass


def generate_node():
    item = AdvancedItem(
        author="schadocalex",
        name="MyItem",
        waypoint_type="None",
        icon_filepath=None,
        entities=[
            Mesh(
                loc=Loc((0, 0, 0), (1, 0, 0, 0)),  # object.location, object.rotation_euler.to_quaternion()
                mesh_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Mesh.Gbx",  # visual, not collidable, mandatory
                # shape_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",  # invisible, collidable, optional
            ),
            Gate(
                loc=Loc((0, 0, 0), (1, 0, 0, 0)),
                shape_filepath=r"C:\Users\schad\Documents\Trackmania\Items\NICE\Part1.Shape.Gbx",  # not collidable, with gameplay
                gameplayId="ReactorBoost2",
            ),
        ],
    )

    with open(r"C:\Users\schad\Documents\Trackmania\Items\nice.Item.Gbx", "wb") as f:
        f.write(item.generate())

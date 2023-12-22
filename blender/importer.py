import os
import bpy
import bpy_extras
import bmesh
from mathutils import Vector

# from src.nice.api import *
from ..src.parser import parse_file, generate_node
from ..src.utils.content import extract_content, RawMesh, Entities, RawMaterial, RawInvisibleMaterial

from ...operators.OT_Settings import TM_OT_Settings_OpenMessageBox
from ...utils.ItemsImport import _get_material_name, _load_asset_mats


def create_raw_mesh(obj_name, raw_mesh):
    # create the mesh data
    mesh_data = bpy.data.meshes.new(f"{obj_name}_data")

    # create the mesh object using the mesh data
    mesh_obj = bpy.data.objects.new(f"{raw_mesh.label}{obj_name}", mesh_data)

    # materials
    all_material_names = []
    all_material_names_to_load = []
    for material in raw_mesh.materials:
        if isinstance(material, RawMaterial):
            material_name = material.link
            material_name, _link = _get_material_name(material_name)
            if material_name + "_asset" not in bpy.data.materials:
                all_material_names_to_load.append(material_name)
        elif isinstance(material, RawInvisibleMaterial):
            material_name = f"TM_invisible_{material.physicsId}"
            if material.gameplayId != "No":
                material_name += "_" + material.gameplayId

        all_material_names.append(material_name)

    if all_material_names_to_load:
        _load_asset_mats(all_material_names_to_load)

    for material_name in all_material_names:
        material_name_asset = material_name + "_asset"
        if material_name_asset in bpy.data.materials:
            new_mat = bpy.data.materials[material_name_asset]
        else:
            new_mat = bpy.data.materials.new(material_name_asset)
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
    # TODO check if uv0 is BaseMaterial (depeding on the material)
    if raw_mesh.uv0:
        uv0 = mesh_data.uv_layers.new(name="BaseMaterial", do_init=False)
        uv0.active = True
        uv0.active_render = True
        for idx, coord in uv0.uv.items():
            pt = raw_mesh.uv0[idx]
            coord.vector = Vector((pt.x, pt.y))
    if raw_mesh.uv1:
        uv1 = mesh_data.uv_layers.new(name="Lightmap", do_init=False)
        for idx, coord in uv1.uv.items():
            pt = raw_mesh.uv1[idx]
            coord.vector = Vector((pt.x, pt.y))

    # update the mesh data (helps with redrawing the mesh in the viewport)
    mesh_data.update()

    # clean up/free memory that was allocated for the bmesh
    bm.free()

    return mesh_obj


def import_content_to_blender(root_collection, name, content, options):
    for idx, obj in enumerate(content):
        child_name = f"{name}_{idx}"
        if isinstance(obj, Entities):
            models = {}
            models_used = {}
            for i, model in obj.models.items():
                model_collection = bpy.data.collections.new(f"model{i}")
                import_content_to_blender(model_collection, "obj", model, options)
                models[i] = model_collection
                models_used[i] = False
                root_collection.children.link(model_collection)

            for i, ent in enumerate(obj.ents):
                ent_pos = (ent.pos.x, -ent.pos.z, ent.pos.y)
                ent_rot = (ent.rot.w, ent.rot.x, -ent.rot.z, ent.rot.y)
                if ent_pos == (0, 0, 0) and ent_rot == (1, 0, 0, 0):
                    # Use the model directly if at origin
                    models_used[ent.model_idx] = True
                    continue

                ent_obj = bpy.data.objects.new(f"ent{i}", None)
                ent_obj.instance_type = "COLLECTION"
                ent_obj.instance_collection = models[ent.model_idx]
                ent_obj.location = ent_pos
                ent_obj.rotation_quaternion = ent_rot
                root_collection.objects.link(ent_obj)

            for idx, model in models.items():
                if not models_used[idx]:
                    model.name = "_ignore_" + model.name
                    # TODO: layer_collection.exclude = True
                    model.hide_render = True

        elif isinstance(obj, RawMesh):  # add the mesh object into the collection
            lod_suffix = ""
            if obj.lod > 0 and obj.lod & 1 != 1:
                lod_suffix = f"_lod{obj.lod}" if obj.lod > 0 else ""

                if options.get("highest_lod_only", True):
                    continue

            mesh = create_raw_mesh(f"{child_name}{lod_suffix}", obj)
            root_collection.objects.link(mesh)
        else:
            print("Unknown: " + str(obj))


class TM_OT_NICE_Item_Import(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = "view3d.tm_nice_import_item"
    bl_description = "Support custom items and natives items. Mesh Modeler items and blocks coming."
    bl_label = "Import Item.Gbx"

    filter_glob: bpy.props.StringProperty(
        default="*.gbx",
        options={"HIDDEN"},
    )

    highest_lod_only: bpy.props.BoolProperty(
        name="Highest LOD only",
        description="Import only the highest LOD. If disable, will import all LODs.",
        default=True,
    )

    # TODO remove nonvisible boolean?

    def execute(self, context):
        data = parse_file(self.filepath)

        content = extract_content(data)
        name = os.path.basename(self.filepath).split(".")[0]

        collection = bpy.data.collections.new("_nice_" + name)
        bpy.context.scene.collection.children.link(collection)

        import_content_to_blender(
            collection,
            "obj",
            content,
            {
                "highest_lod_only": self.highest_lod_only,
            },
        )

        return {"FINISHED"}


class TM_PT_NICE(bpy.types.Panel):
    bl_label = "NICE v0.1"
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
        op.title = self.bl_label
        op.infos = TM_OT_Settings_OpenMessageBox.get_text(
            "Import Item.Gbx",
            "--> Support custom and native items. Mesh Modeler items, blocks and custom blocks coming.",
            "",
            "The exporter will be available in next version, sorry.",
        )

    def draw(self, context):
        layout = self.layout
        scale_box = layout.box()

        row = scale_box.row()
        # row.alert = True
        row.label(text="Importer")

        row = scale_box.row()
        row.scale_y = 1.5
        row.operator("view3d.tm_nice_import_item", text="Import Item.Gbx")

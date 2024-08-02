import os
import bpy
import bpy_extras
import bmesh
from mathutils import Vector, Quaternion

# from src.nice.api import *
from ..src.parser import parse_file, generate_file
from ..src.utils.content import (
    extract_content,
    RawMesh,
    Entities,
    RawMaterial,
    RawInvisibleMaterial,
    BlockVariant,
    SpawnLoc,
    Loc,
    MeshTree,
)

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
    if raw_mesh.materials:
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
        except ValueError:
            # faces can share the same vertices in solids
            # we need to duplicate vertices, as blender doesn't allow it
            new_vidx = len(raw_mesh.vertices)
            for vidx in vert_indices:
                raw_mesh.vertices.append(raw_mesh.vertices[vidx])
                coord = raw_mesh.vertices[-1]
                bm.verts.new((coord.x, -coord.z, coord.y))
            bm.verts.ensure_lookup_table()
            raw_mesh.faces[i] = (new_vidx, new_vidx + 1, new_vidx + 2)
            if raw_mesh.facesMaterials:
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


def loc_to_blender(loc):
    return (Vector((loc.pos.x, -loc.pos.z, loc.pos.y)), Quaternion((loc.rot.w, loc.rot.x, -loc.rot.z, loc.rot.y)))


def create_and_place_empty(obj, name):
    pos, rot = loc_to_blender(obj)

    empty_obj = bpy.data.objects.new(name, None)
    empty_obj.location = pos
    empty_obj.rotation_mode = "QUATERNION"
    empty_obj.rotation_quaternion = rot

    return empty_obj


def import_content_to_blender(root_collection, content, options):
    res = []

    for idx, obj in enumerate(content):
        if isinstance(obj, Entities):
            models = {}
            models_used = {}
            for i, model in obj.models.items():
                model_collection = bpy.data.collections.new(f"model{i}")
                import_content_to_blender(model_collection, model, options)
                models[i] = model_collection
                models_used[i] = False
                root_collection.children.link(model_collection)

            for i, ent in enumerate(obj.ents):
                if ent.model_idx == -1:
                    # empty object, TODO add metadata?
                    ent_obj = create_and_place_empty(ent, f"empty{i}")
                    root_collection.objects.link(ent_obj)
                    res.append(ent_obj)
                else:
                    model_collection = models[ent.model_idx]
                    ent_pos, ent_rot = loc_to_blender(ent)

                    for j, (obj_name, obj) in enumerate(model_collection.all_objects.items()):
                        new_obj = obj.copy()
                        new_obj.name = f"{obj_name}_e{i}m{ent.model_idx}"

                        # new_obj.data = new_obj.data.copy() # TODO param? avoid meshes to be linked

                        new_obj.location = ent_pos + (ent_rot @ new_obj.location)
                        new_obj.rotation_mode = "QUATERNION"
                        new_obj.rotation_quaternion = ent_rot.cross(new_obj.rotation_quaternion)

                        root_collection.objects.link(new_obj)
                        res.append(new_obj)

            for idx, model in models.items():
                # TODO find a way to not add them so we don't have to remove them after the copies?
                for obj in model.all_objects.values():
                    model.objects.unlink(obj)
                root_collection.children.unlink(model)

        elif isinstance(obj, MeshTree):
            obj_pos, obj_rot = loc_to_blender(obj.loc)

            for child in obj.children:
                for new_obj in import_content_to_blender(root_collection, child, options):
                    res.append(new_obj)
                    new_obj.location = obj_pos + (obj_rot @ new_obj.location)
                    new_obj.rotation_mode = "QUATERNION"
                    new_obj.rotation_quaternion = obj_rot.cross(new_obj.rotation_quaternion)

            if obj.mesh:
                assert len(obj.mesh) == 1
                mesh = create_raw_mesh(obj.name, obj.mesh[0])
                mesh.location = obj_pos
                mesh.rotation_mode = "QUATERNION"
                mesh.rotation_quaternion = obj_rot
                root_collection.objects.link(mesh)
                res.append(mesh)

        elif isinstance(obj, RawMesh):
            lod_suffix = ""
            if options.get("highest_lod_only", True):
                if obj.lod > 0 and obj.lod & 1 != 1:
                    continue
            else:
                lod_suffix = f"_lod{obj.lod}" if obj.lod > 0 else ""

            mesh = create_raw_mesh(f"obj_{idx}{lod_suffix}", obj)

            root_collection.objects.link(mesh)
            res.append(mesh)

        elif isinstance(obj, BlockVariant):
            variant_collection = bpy.data.collections.new(f"_variant_{obj.name}")
            root_collection.children.link(variant_collection)

            for mobil_name, mobil in obj.mobils.items():
                mobil_collection = bpy.data.collections.new(mobil_name)
                res += import_content_to_blender(mobil_collection, mobil, options)
                variant_collection.children.link(mobil_collection)

            if obj.content:
                res += import_content_to_blender(variant_collection, obj.content, options)

        elif isinstance(obj, SpawnLoc):
            ent_obj = create_and_place_empty(obj, f"_socket_spawnloc")
            root_collection.objects.link(ent_obj)

            res.append(ent_obj)
        else:
            print("Unknown: " + str(obj))

    return res


class TM_OT_NICE_Item_Import(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = "view3d.tm_nice_import_gbx"
    bl_description = "Support all types of items and native blocks. Custom blocks and clips are coming."
    bl_label = "Import Gbx"

    filter_glob: bpy.props.StringProperty(
        default="*.gbx",
        options={"HIDDEN"},
    )

    highest_lod_only: bpy.props.BoolProperty(
        name="Highest LOD only",
        description="Import only the highest LOD. If disable, will import all LODs.",
        default=True,
    )

    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    # TODO "remove nonvisible" boolean?

    def execute(self, context):
        dirname = os.path.dirname(self.filepath) + os.path.sep
        for file in self.files:
            filepath = dirname + file.name
            data = parse_file(filepath)

            try:
                content = extract_content(data)
            except Exception as e:
                self.report({"ERROR"}, str(e))
                return {"CANCELLED"}

            name = os.path.basename(filepath).split(".")[0]

            collection = bpy.data.collections.new(name)  # TODO add _nice_ if exportable by NICE, else keep as this
            bpy.context.scene.collection.children.link(collection)

            import_content_to_blender(
                collection,
                content,
                {
                    "highest_lod_only": self.highest_lod_only,
                },
            )

        return {"FINISHED"}


class TM_PT_NICE(bpy.types.Panel):
    bl_label = "NICE v0.2"
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
            "Import Gbx",
            "--> Support all types of items and native blocks. Custom blocks and clips are coming.",
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
        row.operator("view3d.tm_nice_import_gbx", text="Import Gbx")

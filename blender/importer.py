import os
import re
import bpy
import bpy_extras
import bmesh
from mathutils import Vector, Quaternion
import traceback
from hashlib import sha256
from time import process_time_ns

# from src.nice.api import *
from ..src.parser import parse_file, parse_bytes
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
    FileRef,
    Metadata,
    NewOptions,
)

from ...operators.OT_Settings import TM_OT_Settings_OpenMessageBox
from ...utils.ItemsImport import _get_material_name, _load_asset_mats

GAMEDATA_FOLDER = "D:\\GameData\\"
MAP_SCENE_NAME = "Map"
GAMEDATA_SCENE_NAME = "zzz_GameData"

REGEXP_ID = re.compile(r"\.\d{3}$")
REGEXP_GBX = re.compile(r"\.gbx$", re.I)

times_profiler = {}
times_state = None
TIMES_BLENDER = "import"
TIMES_PARSE = "parse"


def reset_times():
    global times_profiler
    global times_state
    times_profiler = {}
    times_state = None


def change_times(new_state):
    global times_profiler
    global times_state
    now = process_time_ns()
    if times_state is not None:
        old, old_state = times_state
        if old_state not in times_profiler:
            times_profiler[old_state] = 0
        times_profiler[old_state] += now - old
    times_state = now, new_state


def start_times():
    reset_times()
    change_times(TIMES_BLENDER)


def show_times():
    for k, v in times_profiler.items():
        print(f"{k} time: {v // 1_000_000}ms")


def get_gamedata_collection():
    game_data_scene = bpy.data.scenes.get(GAMEDATA_SCENE_NAME)
    if game_data_scene is None:
        current_scene = bpy.context.scene
        bpy.ops.scene.new(type="EMPTY")
        game_data_scene = bpy.context.scene
        game_data_scene.name = GAMEDATA_SCENE_NAME
        bpy.context.window.scene = current_scene
    return game_data_scene.collection


def delete_collection(collection):
    for child in collection.children:
        delete_collection(child)
        bpy.data.collections.remove(child)

    for obj in collection.objects:
        if obj.type == "MESH":
            mesh = obj.data
            bpy.data.objects.remove(obj)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        elif obj.type == "EMPTY":
            bpy.data.objects.remove(obj)


def delete_scene(scene_name):
    scene = bpy.data.scenes.get(scene_name)
    if scene is None:
        return

    delete_collection(scene.collection)
    bpy.data.scenes.remove(scene)


def pos_to_blender(pos):
    return Vector((pos.x, -pos.z, pos.y))


def loc_to_blender(loc):
    return (
        Vector((loc.pos.x, -loc.pos.z, loc.pos.y)),
        Quaternion((loc.rot.w, loc.rot.x, -loc.rot.z, loc.rot.y)),
    )


def load_asset_mats(all_mats):
    _load_asset_mats([mat for mat in all_mats if mat + "_asset" not in bpy.data.materials])
    result = []
    for mat in all_mats:
        material_name_asset = mat + "_asset"
        if material_name_asset not in bpy.data.materials:
            result.append(bpy.data.materials.new(material_name_asset))
        else:
            result.append(bpy.data.materials[material_name_asset])

    return result


def remap_object_materials(obj, remap):
    for i, slot in enumerate(obj.material_slots):
        if slot.material.link in remap:
            new_mat_name, _ = _get_material_name(remap[slot.material.link])
            [new_mat] = load_asset_mats([new_mat_name])

            obj.material_slots[i].link = "OBJECT"
            obj.material_slots[i].material = new_mat


def create_raw_mesh(obj_name, raw_mesh):
    # create the mesh data
    mesh_data = bpy.data.meshes.new(f"{obj_name}_data")

    # create the mesh object using the mesh data
    mesh_obj = bpy.data.objects.new(f"{raw_mesh.label}{obj_name}", mesh_data)

    # materials
    all_material_names = []
    if raw_mesh.materials:
        for material in raw_mesh.materials:
            if isinstance(material, RawInvisibleMaterial) or (isinstance(material, RawMaterial) and material.invisible):
                material_name = f"TM_Invisible_{material.physicId}"
                if material.gameplayId != "No":
                    material_name += f"_{material.gameplayId}"
            elif isinstance(material, RawMaterial):
                material_name = material.link
                material_name, _link = _get_material_name(material_name)

            all_material_names.append(material_name)

    for mat in load_asset_mats(all_material_names):
        mesh_obj.data.materials.append(mat)

    # create a new bmesh
    bm = bmesh.new()

    # vertices
    for coord in raw_mesh.vertices:
        bm.verts.new((coord.x, -coord.z, coord.y))

    bm.verts.ensure_lookup_table()

    # faces
    normals = None
    if raw_mesh.normals:
        normals = []
    for i, vert_indices in enumerate(raw_mesh.faces):
        try:
            face = bm.faces.new([bm.verts[vidx] for vidx in vert_indices])
            if normals is not None:
                for vidx in vert_indices:
                    normal = raw_mesh.normals[vidx]
                    normals.append((normal.x, -normal.z, normal.y))
        except ValueError:
            # faces can share the same vertices in solids
            # we need to duplicate vertices, as blender doesn't allow it
            new_vidx = len(raw_mesh.vertices)
            for vidx in vert_indices:
                raw_mesh.vertices.append(raw_mesh.vertices[vidx])
                if normals is not None:
                    normals.append(normals[vidx])
                coord = raw_mesh.vertices[-1]
                bm.verts.new((coord.x, -coord.z, coord.y))
            bm.verts.ensure_lookup_table()
            raw_mesh.faces[i] = range(new_vidx, new_vidx + len(vert_indices))
            if raw_mesh.facesMaterials:
                raw_mesh.facesMaterials.append(raw_mesh.facesMaterials[i])
            face = bm.faces.new([bm.verts[i] for i in raw_mesh.faces[i]])

        face.material_index = raw_mesh.facesMaterials[i] if raw_mesh.facesMaterials is not None else 0

    # writes the bmesh data into the mesh data
    bm.to_mesh(mesh_data)

    # apply normals
    if raw_mesh.normals is not None:
        mesh_data.normals_split_custom_set(normals)

    # Add uvs
    if raw_mesh.uvs:
        for i, mesh_uv in enumerate(raw_mesh.uvs):
            name = f"uv{i + 1}"
            # TODO check if uv0 is BaseMaterial (depending on the material)
            if i == 0:
                name = "BaseMaterial"
            elif i == 1:
                name = "Lightmap"
            uv0 = mesh_data.uv_layers.new(name=name, do_init=False)
            if i == 0:
                uv0.active = True
                uv0.active_render = True

            for idx, coord in uv0.uv.items():
                coord.vector = Vector((mesh_uv[idx].x, mesh_uv[idx].y))

    # Add vertex color
    if raw_mesh.colors:
        for i, vcolors in enumerate(raw_mesh.colors):
            color_layer = mesh_data.color_attributes.new(name=f"color{i}", type="BYTE_COLOR", domain="POINT")
            for i, col in enumerate(vcolors):
                color_layer.data[i].color = (col.r / 255.0, col.g / 255.0, col.b / 255.0, col.a / 255.0)

    # update the mesh data (helps with redrawing the mesh in the viewport)
    mesh_data.update()

    # clean up/free memory that was allocated for the bmesh
    bm.free()

    return mesh_obj


def create_and_place_empty(obj, name):
    pos, rot = loc_to_blender(obj)

    empty_obj = bpy.data.objects.new(name, None)
    empty_obj.location = pos
    empty_obj.rotation_mode = "QUATERNION"
    empty_obj.rotation_quaternion = rot

    return empty_obj


def show_errors(data, options):
    report = options.get("report")
    if not report:
        return
    for err in data.get("_errors", []):
        report({"ERROR"}, str(err))
    for err in data.get("_warns", []):
        report({"WARNING"}, str(err))
    data._errors = []
    data._warns = []


def get_content(filepath, options, is_map_import, filebytes=None):  # TODO is_map_import
    options["dirname"] = os.path.dirname(filepath) + os.path.sep
    options["filepath"] = filepath
    options["level"] = options.get("level", 0)

    try:
        change_times(TIMES_PARSE)
        if filebytes is not None:
            data = parse_bytes(filebytes, filepath, recursive=False)
        else:
            data = parse_file(filepath, recursive=False)
        change_times(TIMES_BLENDER)
        show_errors(data, options)
        change_times(TIMES_PARSE)
        content = extract_content(data, None, options)
        change_times(TIMES_BLENDER)
        show_errors(data, options)
    except Exception as e:
        change_times(TIMES_BLENDER)
        tb = traceback.format_exception(e)
        report = options.get("report")
        if report:
            report({"ERROR"}, f"error while extracting {filepath}:\n{repr(e)}\n{''.join(tb)}")

        return None

    return content


def get_collection_without_id(collection, name):
    for child in collection.children:
        if re.sub(REGEXP_ID, "", child.name).lower() == name.lower():
            return child
    return None


def get_collection_from_path(collection, path):
    for child_name in path:
        child = get_collection_without_id(collection, child_name)
        if child is None:
            child = bpy.data.collections.new(child_name)
            collection.children.link(child)

        collection = child
    return collection


def fileref_to_path(fileref, opts):
    # max size is 66: 10 (hash) + 42 (name) + 9 (variant) + 1 (lod) + 4 sep
    path = os.path.normpath(fileref.filepath).replace("\\", "/").split("GameData/")[-1].split("/")

    block_name = re.sub(REGEXP_GBX, "", os.path.basename(fileref.filepath))
    if fileref.options and "variant_id" in fileref.options:
        block_name += "_" + fileref.options["variant_id"]

    match opts.get("lod", "all"):
        case "highest":
            block_name += "_h"
        case "lowest":
            block_name += "_l"

    path[-1] = block_name

    return path


def fileref_to_collection_name(fileref, opts):
    # max size is 66: 10 (hash) + 42 (name) + 9 (variant) + 1 (lod) + 4 sep
    gamedata_path = os.path.normpath(fileref.filepath).lower().replace("\\", "/").split("gamedata/")[-1]

    uid = sha256(gamedata_path.encode(), usedforsecurity=False).hexdigest()[:10]
    block_name_cropped = os.path.basename(fileref.filepath).split(".")[0][-44:]
    name = f"{uid}_{block_name_cropped}"
    if fileref.options and "variant_id" in fileref.options:
        name += "_" + fileref.options["variant_id"]

    match opts.get("lod", "all"):
        case "highest":
            name += "_h"
        case "lowest":
            name += "_l"

    return name


def import_fileref(fileref, options):
    use_fileref = options.get("use_fileref", True)

    filepath = fileref.filepath
    if filepath.lower().endswith(".fxsys.gbx"):
        return None

    if fileref.filebytes is None:
        # As collection tree
        # path = fileref_to_path(fileref, options)
        # collection_name = path[-1]
        # gamedata_collection = get_collection_from_path(get_gamedata_collection(), path[:-1])

        # As flat collections
        collection_name = fileref_to_collection_name(fileref, options)
        gamedata_collection = get_gamedata_collection()
    else:
        path = filepath.replace("\\", "/").split("/")
        collection_name = path[-1]
        gamedata_collection = get_collection_from_path(
            options.get("root_collection", bpy.context.scene.collection), path[:-1]
        )

    collection = get_collection_without_id(gamedata_collection, collection_name)

    if collection is None:
        sub_options = {
            **options,
            **(fileref.options or {}),
            "level": options.get("level", 0) + 1,
        }
        content = get_content(filepath, sub_options, False, fileref.filebytes)
        if content is None:
            return None

        collection = bpy.data.collections.new(collection_name)
        gamedata_collection.children.link(collection)

        import_content_to_blender(collection, content, sub_options)

    instances = []
    if options.get("level", 0) >= min(options.get("instance_max_level", 0), 7):  # TODO take from options
        # make linked duplicates
        for source in collection.all_objects:
            instance = bpy.data.objects.new(source.name, source.data)
            instance.location = source.location
            instance.rotation_mode = "QUATERNION"
            instance.rotation_quaternion = source.rotation_quaternion
            materials_remap = options.get("materials_remap")
            if materials_remap:
                remap_object_materials(instance, materials_remap)
            instances.append(instance)
    else:
        # make collection instances
        instance = bpy.data.objects.new("inst_" + collection.name[:56], None)
        instance.instance_type = "COLLECTION"
        instance.instance_collection = collection
        instance.show_instancer_for_viewport = False
        instance.show_instancer_for_render = False
        instances.append(instance)

    return instances


def import_content_to_blender(root_collection, content, options):
    res = []

    for idx, obj in enumerate(content):
        if isinstance(obj, NewOptions):
            options = {**options, **obj.options}
        elif isinstance(obj, Entities):
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
                    continue  # TODO param
                    # empty object, TODO add metadata?
                    ent_obj = create_and_place_empty(ent.loc, f"empty{i}")
                    root_collection.objects.link(ent_obj)
                    res.append(ent_obj)
                else:
                    model_collection = models[ent.model_idx]
                    ent_pos, ent_rot = loc_to_blender(ent.loc)

                    for j, (obj_name, obj) in enumerate(model_collection.all_objects.items()):
                        new_obj = obj.copy()
                        new_obj.name = f"{obj_name}_e{i}m{ent.model_idx}"

                        # new_obj.data = new_obj.data.copy() # TODO param? avoid meshes to be linked

                        pos_offset = Vector((0.0, 0.0, 0.0))
                        if ent.loc.rotate_from_center and "block_size" in new_obj.instance_collection:
                            bs = new_obj.instance_collection["block_size"]
                            rot = ent_rot @ Vector((32.0 * bs[0], -32.0 * bs[2], 0.0))
                            pos_offset = Vector((-rot[0] if rot[0] < 0 else 0, -rot[1] if rot[1] > 0 else 0, 0))

                        if ent.loc.pivot_position is not None:
                            pos_offset = ent_rot @ pos_to_blender(ent.loc.pivot_position)

                        new_obj.location = ent_pos + pos_offset + (ent_rot @ new_obj.location)
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

            prefix = f"z{int(obj.farZ)}_" if obj.farZ is not None else options.get("name_prefix", "")

            for child in obj.children:
                for new_obj in import_content_to_blender(root_collection, child, {**options, "name_prefix": prefix}):
                    res.append(new_obj)
                    new_obj.location = obj_pos + (obj_rot @ new_obj.location)
                    new_obj.rotation_mode = "QUATERNION"
                    new_obj.rotation_quaternion = obj_rot.cross(new_obj.rotation_quaternion)

            if obj.mesh:
                assert len(obj.mesh) == 1
                mesh = create_raw_mesh(f"{prefix}{obj.name}_mesh", obj.mesh[0])
                mesh.location = obj_pos
                mesh.rotation_mode = "QUATERNION"
                mesh.rotation_quaternion = obj_rot
                root_collection.objects.link(mesh)
                bpy.ops.object.shade_auto_smooth()  # TODO check if object is selected?
                res.append(mesh)

            if obj.surface:
                assert len(obj.surface) == 1
                mesh = create_raw_mesh(f"{prefix}{obj.name}_surf", obj.surface[0])
                mesh.location = obj_pos
                mesh.rotation_mode = "QUATERNION"
                mesh.rotation_quaternion = obj_rot
                root_collection.objects.link(mesh)
                res.append(mesh)

        elif isinstance(obj, RawMesh):
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
            ent_obj = create_and_place_empty(obj, "_socket_spawnloc")
            root_collection.objects.link(ent_obj)

            res.append(ent_obj)
        elif isinstance(obj, FileRef):
            instances = import_fileref(obj, options)
            if instances:
                for instance in instances:
                    root_collection.objects.link(instance)
                    if obj.loc is not None:
                        pos, rot = loc_to_blender(obj.loc)
                        instance.location = pos + (rot @ instance.location)
                        instance.rotation_mode = "QUATERNION"
                        instance.rotation_quaternion = rot.cross(instance.rotation_quaternion)
        elif isinstance(obj, Metadata):
            assert obj.name is not None and obj.value is not None
            root_collection[obj.name] = obj.value
        else:
            raise Exception("Unknown: " + str(obj))

    return res


class TM_OT_NICE_Item_Import(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = "view3d.tm_nice_import_gbx"
    bl_description = "Import any type of gbx file except maps / replays."
    bl_label = "Import Gbx"

    filter_glob: bpy.props.StringProperty(
        default="*.gbx",
        options={"HIDDEN"},
    )

    files: bpy.props.CollectionProperty(
        type=bpy.types.OperatorFileListElement,
        options={"HIDDEN", "SKIP_SAVE"},
    )

    visible_only: bpy.props.BoolProperty(
        name="Visible part only",
        description="Import only visible meshes of native items and blocks.",
        default=False,
    )

    lod: bpy.props.EnumProperty(
        name="Level Of Detail",
        description="Choose the LOD of imported meshes.",
        default="highest",
        items=(
            ("highest", "Highest", ""),
            ("lowest", "Lowest", ""),
            ("all", "All", ""),
        ),
    )

    merge_objects: bpy.props.BoolProperty(
        name="Merge objects",
        description="Auto-merge objects of similar properties when possible.",
        default=True,
        options={"HIDDEN"},
    )

    def execute(self, context):
        # delete_scene(GAMEDATA_SCENE_NAME)  # just for dev

        start_times()

        dirname = os.path.dirname(self.filepath) + os.path.sep

        options = {
            "report": self.report,
            "use_fileref": False,
            "visible_only": self.visible_only,
            "lod": self.lod,
            "merge_objects": self.merge_objects,
            "instance_max_level": 0,
        }

        for file in self.files:
            filepath = dirname + file.name

            name = os.path.basename(filepath).split(".")[0]
            collection = bpy.data.collections.new(name)  # TODO add _nice_ if exportable by NICE, else keep as this
            bpy.context.scene.collection.children.link(collection)
            options = {**options, "root_collection": collection}

            content = get_content(filepath, options, False)
            if content is None:
                return {"CANCELLED"}

            import_content_to_blender(collection, content, options)

        show_times()

        if bpy.context.space_data.clip_start < 1:
            bpy.context.space_data.clip_start = 1

        return {"FINISHED"}


class TM_OT_NICE_Map_Import(bpy.types.Operator, bpy_extras.io_utils.ImportHelper):
    bl_idname = "view3d.tm_nice_import_map"
    bl_description = "Import maps and replays."
    bl_label = "Import map"

    filter_glob: bpy.props.StringProperty(default="*.Map.Gbx", options={"HIDDEN"})

    filepath: bpy.props.StringProperty(
        subtype="FILE_PATH",
        options={"SKIP_SAVE"},
    )

    visible_only: bpy.props.BoolProperty(
        name="Visible part only",
        description="Import only visible meshes of native items and blocks.",
        default=True,
    )

    lod: bpy.props.EnumProperty(
        name="Level Of Detail",
        description="Choose the LOD of imported meshes.",
        default="lowest",
        items=(
            ("highest", "Highest", ""),
            ("lowest", "Lowest", ""),
            # ("all", "All", ""),
        ),
    )

    merge_objects: bpy.props.BoolProperty(
        name="Merge objects",
        description="Auto-merge objects of similar properties when possible.",
        default=True,
        options={"HIDDEN"},
    )

    # TODO "remove nonvisible" boolean?

    def execute(self, context):
        # TODO check game folder is accessible and set gamedata_folder

        start_times()

        # delete_scene(GAMEDATA_SCENE_NAME)  # just for DEV
        delete_scene(MAP_SCENE_NAME)
        root_collection = bpy.context.scene.collection

        bpy.ops.scene.new(type="EMPTY")
        bpy.context.scene.name = MAP_SCENE_NAME
        bpy.context.space_data.clip_start = 1
        bpy.context.space_data.clip_end = 10000

        options = {
            "report": self.report,
            "use_fileref": True,
            "root_collection": root_collection,
            "visible_only": self.visible_only,
            "lod": self.lod,
            "merge_objects": self.merge_objects,
            "instance_max_level": 1,
            "filter_grassfence": True,
            "gamedata_folder": GAMEDATA_FOLDER,
        }

        content = get_content(self.filepath, options, True)
        if content is None:
            return {"CANCELLED"}

        import_content_to_blender(bpy.context.scene.collection, content, options)

        show_times()

        return {"FINISHED"}


class TM_PT_NICE(bpy.types.Panel):
    bl_label = "NICE v0.3"
    bl_idname = "TM_PT_NICE"
    bl_context = "objectmode"
    # bl_parent_id = "TM_PT_Map_Manipulate"
    bl_category = "Blendermania"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {"DEFAULT_CLOSED"}

    def draw_header(self, context):
        layout = self.layout
        layout.label(icon="COLLECTION_COLOR_03")

    def draw_header_preset(self, context):
        layout = self.layout
        # tm_props = get_global_props()
        row = layout.row(align=True)

        col = row.column(align=True)
        op = col.operator("view3d.tm_open_messagebox", text="", icon="QUESTION")
        op.link = ""
        op.title = self.bl_label
        op.infos = TM_OT_Settings_OpenMessageBox.get_text(
            "NadeoImporter Community Edition",
            "Import all types of gbx files.",
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

        row = scale_box.row()
        row.scale_y = 1.5
        row.operator("view3d.tm_nice_import_map", text="Import Map")

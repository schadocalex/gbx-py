import os
from math import sqrt
from glob import glob
from construct import Container

from .math import quaternion_from_matrix, quaternion_from_euler, _AXES2TUPLE


class Metadata:
    name = None
    value = None


class NewOptions:
    options = None


class FileRef:
    filepath = None
    filebytes = None
    loc = None
    options = None
    materials_remap = None


class RawMaterial:
    link = ""
    physicId = None
    gameplayId = None
    color = None
    invisible = False


class RawInvisibleMaterial:
    physicId = None
    gameplayId = None


class RawMesh:
    # vertices attributes
    vertices = None
    normals = None
    colors = None

    # faces
    faces = None
    materials = None
    facesMaterials = None  # if len(materials) > 0

    # indexed by face corners
    uvs = None

    # misc
    lod = 0
    label = ""


class Entity:
    loc = None
    model_idx = -1


class Entities:
    models = None
    ents = None
    log = False


class BlockVariant:
    name = ""
    mobils = None
    content = None


class Loc:
    pos = Container(x=0, y=0, z=0)
    rot = Container(x=0, y=0, z=0, w=1)
    pivot_position = None
    rotate_from_center = False  # set pivot_position to center of block


class SpawnLoc(Loc):
    pos = Container(x=0, y=0, z=0)
    rot = Container(x=0, y=0, z=0, w=1)


class MeshTree:
    name = ""
    mesh = None
    surface = None
    loc = None
    children = None
    farZ = None


edir_to_quat = {
    "North": Container(x=0, y=0, z=0, w=1),
    "East": Container(x=0, y=-sqrt(2) / 2, z=0, w=sqrt(2) / 2),
    "South": Container(x=0, y=1, z=0, w=0),
    "West": Container(x=0, y=sqrt(2) / 2, z=0, w=sqrt(2) / 2),
}


def warn(opts, s):
    opts["root"]._warns.append(s)
    print(opts["root"]._warns[-1])


def loop_objects(content):
    if content is None:
        return

    for obj in content:
        if isinstance(obj, Entities):
            for model in obj.models.values():
                yield from loop_objects(model)
        elif isinstance(obj, BlockVariant):
            for mobil in obj.mobils.values():
                yield from loop_objects(mobil)
            yield from loop_objects(obj.content)
        else:
            yield obj


def label_all_meshes(content, label):
    for obj in loop_objects(content):
        if isinstance(obj, RawMesh):
            obj.label = label
    return content


def remap_materials(content, remap):
    for obj in loop_objects(content):
        if isinstance(obj, RawMesh):
            for mat in obj.materials:
                if isinstance(mat, RawMaterial) and mat.link in remap:
                    mat.link = remap[mat.link]
        # if isinstance(obj, FileRef):
        #     obj.materials_remap = remap


def apply_mat_modifier(content, mat_modifier):
    if not mat_modifier or mat_modifier._index < 0 or mat_modifier.get("_errors"):
        return
    assert mat_modifier.classId == 0x0915D000

    if 0x915D001 in mat_modifier.body and mat_modifier.body[0x915D001].get("name") == "Turbo":
        return  # because the Turbo materials variants doesn't exist in blendermania, we need to take default ones. TODO

    chunk = mat_modifier.body[0x915D000]
    remap = {}
    prefix = chunk.RemapFolder.split("\\")[-2] + "_"
    for fid in chunk.Remapping.body[0x90F4005].fids:
        material_link = fid.filePath.split("\\")[-1].replace(".Material.Gbx", "")
        remap[material_link] = prefix + fid.type

    remap_materials(content, remap)


def mat_from_CPlugMaterialUserInst(data):
    mat = RawMaterial()
    mat.link = data.body[0x090FD000].link
    mat.physicId = data.body[0x090FD000].surfacePhysicId
    mat.gameplayId = data.body[0x090FD000].surfaceGameplayId
    mat.color = data.body[0x090FD000].color
    mat.invisible = data.body[0x090FD000].link.startswith("Editors")
    return mat


def iso4_to_loc(loc, mat):
    loc.pos = Container(x=mat.TX, y=mat.TY, z=mat.TZ)
    loc.rot = quaternion_from_matrix(mat)
    return loc


def iso4_to_spawnloc(mat):
    return iso4_to_loc(SpawnLoc(), mat)


def need_spawn(waypointType):
    return waypointType in ("Start", "Checkpoint", "StartFinish")


def compute_block_size(variant):
    block_min = (0, 0, 0)
    block_max = (0, 0, 0)
    for unit in variant[0x0315B008].blockUnitModels:
        off = unit.body[0x03036000].RelativeOffset
        block_min = (min(block_min[0], off.x), min(block_min[1], off.y), min(block_min[2], off.z))
        block_max = (max(block_max[0], off.x), max(block_max[1], off.y), max(block_max[2], off.z))
    return (
        block_max[0] - block_min[0] + 1,
        block_max[1] - block_min[1] + 1,
        block_max[2] - block_min[2] + 1,
    )


def extract_content(data, parent, opts):
    if data is None or data.get("_index") == -1:
        return []
    if "root" not in opts:
        opts["root"] = data

    if "classId" not in data:
        if "_index" in data and "_relativeFilePath" in data:
            assert "dirname" in opts
            filepath = os.path.normpath(opts.get("dirname", "") + data._relativeFilePath)
            if True or opts.get("use_fileref"):
                fileref = FileRef()
                fileref.filepath = filepath
                return [fileref]
            else:
                warn(opts, f"missing file, ignoring: {data._relativeFilePath}")
                return []
        raise Exception(data._error if "_error" in data else data)

    # CGameItemModel
    if data.classId == 0x2E002000:
        chunk = data.body[0x2E002019]

        mat_modifier = extract_content(chunk.MaterialModifier, data, opts)
        model_edition_content = extract_content(chunk.EntityModelEdition, data, opts)
        model_content = extract_content(chunk.EntityModel, data, opts)
        # TODO data.body[0x2E00201F].waypointType
        # add the metadata somewhere? Metadata(key="waypoint", value=waypointType)?

        content = mat_modifier + model_edition_content + model_content

        # remap materials
        # apply_mat_modifier(content, chunk.MaterialModifier)

        return content

    # CGameCommonItemEntityModelEdition
    elif data.classId == 0x2E026000:
        return extract_MeshCrystal(data.body[0x2E026000].meshCrystal, opts)

    # CGameCommonItemEntityModel
    elif data.classId == 0x2E027000:
        chunk = data.body[0x2E027000]

        objects_content = extract_content(chunk.staticObject, data, opts)

        trigger_shape_content = label_all_meshes(extract_content(chunk.props.triggerShape, data, opts), "_trigger_")

        content = objects_content + trigger_shape_content

        if parent is not None and parent.classId == 0x2E002000:
            waypointType = parent.body[0x2E00201F].waypointType
            if need_spawn(waypointType):
                content.append(iso4_to_spawnloc(data.body[0x2E027000].props.spawnLoc))

        return content

    # CPlugStaticObjectModel
    elif data.classId == 0x09159000:
        meshes = extract_content(data.body.Mesh, data, opts)
        if data.body.isMeshCollidable:
            if parent is not None and parent.classId != 0x2E027000:
                label_all_meshes(meshes, "_notcollidable_")
            return meshes
        else:
            label_all_meshes(meshes, "_notcollidable_")
            shapes = extract_content(data.body.Shape, data, opts)
            return meshes + shapes

    # SPlugPrefab
    elif data.classId == 0x09145000:
        ents = Entities()
        ents.models = {}
        ents.ents = []
        for ent_idx, ent in enumerate(data.body.Ents):
            if opts.get("visible_only") and ent.model._index == -1:
                continue
            if ent.model._index >= 0 and ent.model._index not in ents.models:
                ents.models[ent.model._index] = extract_content(ent.model, data, opts)

            new_ent = Entity()
            new_ent.model_idx = ent.model._index
            new_ent.loc = Loc()
            new_ent.loc.pos = ent.pos
            new_ent.loc.rot = ent.rot
            ents.ents.append(new_ent)

        return [ents]

    # CPlugSolid2Model
    elif data.classId == 0x090BB000:
        return extract_CPlugSolid2Model(data, parent, opts)

    # CPlugSurface
    elif data.classId == 0x0900C000:
        return surf_to_content(data.body[0x900C003].surf, opts)

    # CPlugDynaObjectModel
    elif data.classId == 0x09144000:
        content = []

        content += label_all_meshes(extract_content(data.body.Mesh, data, opts), "_notcollidable_")
        if not opts.get("visible_only", False):
            if data.body.DynaShape._index > 0:
                content += label_all_meshes(extract_content(data.body.DynaShape, data, opts), "_dynashape_")
            if data.body.StaticShape._index > 0:
                content += label_all_meshes(extract_content(data.body.StaticShape, data, opts), "_staticshape_")

        return content

    # CGameCtnBlockInfo
    elif (
        data.classId == 0x03051000  # CGameCtnBlockInfoClassic
        or data.classId == 0x0304F000  # CGameCtnBlockInfoFlat
        or data.classId == 0x03053000  # CGameCtnBlockInfoClip
        or data.classId == 0x03340000  # CGameCtnBlockInfoClipVertical
        or data.classId == 0x0335B000  # CGameCtnBlockInfoClipHorizontal
    ):
        content = []

        content += extract_content(data.body[0x0304E031].materialModifier, data, opts)

        # TODO choose variant and mobil
        variant_id = opts.get("variant_id", "a0_-1_-1")
        indexes = [int(x) for x in variant_id[1:].split("_")]
        if variant_id[0] == "g":
            if indexes[0] == 0:
                variant = data.body[0x0304E023].variantBaseGround
            else:
                variant = data.body[0x0304E027].additionalVariantsGround[indexes[0] - 1].body
        else:
            indexes[0] = int(variant_id[1])
            if indexes[0] == 0:
                variant = data.body[0x0304E023].variantBaseAir
            else:
                variant = data.body[0x0304E02C].additionalVariantsAir[indexes[0] - 1].body

        mobil = variant[0x0315B005].mobils[indexes[1]][indexes[2]]

        content += extract_content(mobil, data, opts)

        # waypoint spawn loc
        waypoint_type = data.body[0x0304E026].waypointType
        if need_spawn(waypoint_type):
            assert variant[0x0315B008].version >= 2

            spawn = SpawnLoc()
            content.append(spawn)

            pos3d = variant[0x0315B008].spawn
            spawn.pos.x, spawn.pos.y, spawn.pos.z = pos3d.x, pos3d.y, pos3d.z
            spawn.rot = quaternion_from_euler(pos3d.roll, pos3d.pitch, pos3d.yaw)

        if not opts.get("visible_only"):
            # trigger
            trigger_shape = variant[0x0315B006].waypointTriggerShape
            content += label_all_meshes(extract_content(trigger_shape, data, opts), "_trigger_")

        # TODO do not erase mobils GeomTransformation
        # for c in content:
        #     if hasattr(c, "loc"):
        #         c.loc = Loc()
        #         c.loc.pos = Container(
        #             x=-variant[0x0315B008].spawn.x,
        #             y=-variant[0x0315B008].spawn.y,
        #             z=-variant[0x0315B008].spawn.z,
        #         )

        # remap materials
        # apply_mat_modifier(content, data.body[0x0304E031].materialModifier)

        # block size
        metadata = Metadata()
        metadata.name = "block_size"
        metadata.value = compute_block_size(variant)
        content.append(metadata)

        return content

    # CGameCtnBlockInfoMobil
    elif data.classId == 0x03122000:
        prefab_fid = data.body[0x03122003].prefab_fid
        if prefab_fid._index < 0:
            return []
        content = extract_content(prefab_fid, data, opts)
        if data.body[0x03122003].HasGeomTransformation:
            for c in content:
                if hasattr(c, "loc"):
                    c.loc = Loc()
                    c.loc.pos = data.body[0x03122003].GeomTransformation
                    r = data.body[0x03122003].GeomTransformation
                    c.loc.rot = quaternion_from_euler(r.roll, r.pitch, r.yaw)
        return content

    # NPlugTrigger_SWaypoint
    elif data.classId == 0x09178000:
        return label_all_meshes(extract_content(data.body.TriggerShape, data, opts), "_trigger_")

    # NPlugTrigger_SSpecial
    elif data.classId == 0x09179000:
        return label_all_meshes(extract_content(data.body.surf, data, opts), "_gate_")

    # CPlugSpawnModel
    elif data.classId == 0x0917A000:
        return [iso4_to_spawnloc(data.body[0x0917A000].Loc)]

    # CPlugSolid
    elif data.classId == 0x09005000:
        return extract_content(data.body[0x09005011].tree, data, opts)

    # CPlugTree
    elif data.classId == 0x0904F000 or data.classId == 0x09015000:  # 0x09015000 is with Levels
        tree = MeshTree()
        tree.name = data.body[0x0904F00D].name
        tree.mesh = extract_content(data.body[0x0904F016].visual, data, opts)
        tree.surface = extract_content(data.body[0x0904F016].surface, data, opts)
        tree.loc = Loc()
        if data.body[0x0904F01A].loc is not None:
            iso4_to_loc(tree.loc, data.body[0x0904F01A].loc)
        tree.children = [extract_content(child, data, opts) for child in data.body[0x0904F006].children]
        if 0x09015002 in data.body:
            for level in data.body[0x09015002].Levels:
                tree.children.append(extract_content(level.tree, data, opts))
                tree.children[-1][0].farZ = level.farZ

        # TODO material

        return [tree]

    # CPlugVisualIndexedTriangles
    elif data.classId == 0x0901E000:
        return [extract_mesh_CPlugVisualIndexedTriangles(data)]

    # NPlugItem_SVariantList
    elif data.classId == 0x2F0BC000:
        variant_id = opts.get("variant_id", None)
        if variant_id is None:
            content = []
            for i, variant in enumerate(data.body.variants):
                v = BlockVariant()
                content.append(v)
                v.name = str(i)
                v.mobils = {}
                v.content = extract_content(variant.EntityModel, data, opts)
            return content
        else:
            return extract_content(data.body.variants[int(variant_id)].EntityModel, data, opts)

    # CGameCtnChallenge
    elif data.classId == 0x03043000:
        return extract_map(data, parent, opts)

    # VegetTreeModel
    elif data.classId == 0x2F086000:
        content = []
        match opts.get("lod", "all"):
            case "highest":
                for part in data.body.tree1:
                    content += extract_content(part.mesh, data, opts)
            case "lowest":
                for part in data.body.tree2:  # for now tree2
                    content += extract_content(part.mesh, data, opts)
            case _:
                for suffix, tree in (("_lod1", data.body.tree1), ("_lod2", data.body.tree2)):
                    v = BlockVariant()
                    content.append(v)
                    v.name = "tree" + suffix
                    v.mobils = {}
                    v.content = []
                    for part in tree:
                        v.content += extract_content(part.mesh, data, opts)

                # mesh = RawMesh()
                # mesh.label = "tree_lod3"
                # mesh.vertices = data.body.u11
                # mesh.faces = data.body.u12
                # trees.append(mesh)

        return content

    # CPlugEditorHelper
    elif data.classId == 0x0917B000:
        return extract_content(data.body.helper, data, opts)

    # CPlugGameSkinAndFolder
    elif data.classId == 0x0915D000:
        if 0x915D001 in data.body and data.body[0x915D001].get("name") == "Turbo":
            return []  # because the Turbo materials variants doesn't exist in blendermania, we need to take default ones. TODO

        chunk = data.body[0x915D000]
        remap = {}
        if not chunk.RemapFolder:
            return []  # TODO?
        prefix = chunk.RemapFolder.split("\\")[-2] + "_"
        for fid in chunk.Remapping.body[0x90F4005].fids:
            material_link = fid.filePath.split("\\")[-1].replace(".Material.Gbx", "")
            remap[material_link] = prefix + fid.type

        new_opts = NewOptions()
        new_opts.options = {"materials_remap": remap}
        return [new_opts]

    elif data.classId == 0x2F0CA000:
        return []

    else:
        warn(opts, f"unsupported classId: {hex(data.classId)} in {opts['filepath']}")
        return []


def index_files(dirname):
    allfiles = {}
    for file in glob(
        os.path.join(dirname, "**", "*.Gbx"),
        recursive=True,
    ):  # TODO lower()
        block_name = os.path.basename(file).split(".")[0].lower()
        if block_name in allfiles and "deprecated" in file[len(dirname) :].lower():
            continue
        allfiles[block_name] = file

    return allfiles


def index_embedded_files(data):
    allfiles = {}
    for i, file in enumerate(data.body[0x03043054].embeddedData.filesMeta):
        allfiles[file.id] = i, file
    return allfiles


def match_embedded(data, fileref, allfiles, model):
    if model.author == "Nadeo" or model.id not in allfiles:
        return False

    idx, file_info = allfiles[model.id]
    zip = data.body[0x03043054].embeddedData.zip
    fileref.filepath = zip.namelist()[idx].split(".")[0]
    fileref.filebytes = zip.read(zip.namelist()[idx])

    return True


def extract_map(data, parent, opts):
    map_ents = Entities()
    map_ents.log = True
    map_ents.models = {}
    map_ents.ents = []

    allblocks = index_files(os.path.join(opts.get("gamedata_folder"), "Stadium", "GameCtnBlockInfo"))
    allitems = index_files(os.path.join(opts.get("gamedata_folder"), "Stadium", "Items"))
    all_embedded_items = index_embedded_files(data)
    # TODO index vegets
    height_offset = data.body[0x03043052].DecoBaseHeightOffset * 8

    # TODO parent collection (item, blocks)
    # TODO attach clips inside corresponding block collection

    free_index = 0
    for block in data.body[0x0304301F].Blocks + data.body[0x03043048].BakedBlocks:
        if block.name.lower() not in allblocks:
            continue
        f = block.flags
        variant_id = f"{'g' if f.isGround else 'a'}{f.blockVariantIndex}_{f.mobilIndex}_{f.mobilVariantIndex}"
        model_name = f"B_{block.name}__{variant_id}"
        if model_name not in map_ents.models:
            fileref = FileRef()
            fileref.filepath = allblocks[block.name.lower()]
            fileref.options = {"variant_id": variant_id}
            map_ents.models[model_name] = [fileref]

        new_ent = Entity()
        new_ent.model_idx = model_name
        new_ent.loc = Loc()
        if f.isFree:
            pose = data.body[0x0304305F].freeBlocks[free_index]
            free_index += 1
            new_ent.loc.pos = Container(x=pose.x, y=pose.y + height_offset, z=pose.z)
            new_ent.loc.rot = quaternion_from_euler(pose.roll, pose.pitch, pose.yaw)
        else:
            new_ent.loc.pos = Container(x=block.coords.x * 32, y=block.coords.y * 8, z=block.coords.z * 32)
            new_ent.loc.rot = edir_to_quat[block.dir]
            new_ent.loc.rotate_from_center = True
        map_ents.ents.append(new_ent)

    for obj in data.body[0x3043040].anchoredObjects:
        if obj.classId != 0x03101000:
            warn(opts, "unknown item classId {0x03101000}")
            continue
        item = obj.body[0x03101002]

        variant_id = str((item.flags >> 8) & 0xFF)  # TODO check in Ghidra
        model_name = f"I_{item.itemModel.id}_{variant_id}"
        # TODO variant
        if model_name not in map_ents.models:
            fileref = FileRef()
            # TODO check flags: (item.flags & 1) == 1 when embedded?
            if match_embedded(data, fileref, all_embedded_items, item.itemModel):
                pass
            elif item.itemModel.id.lower() in allitems:
                fileref.filepath = allitems[item.itemModel.id.lower()]
            else:
                continue
            fileref.options = {"variant_id": variant_id}
            map_ents.models[model_name] = [fileref]

        new_ent = Entity()
        new_ent.model_idx = model_name
        new_ent.loc = Loc()
        pos = item.absolutePositionInMap
        new_ent.loc.pos = Container(x=pos.x, y=pos.y + height_offset, z=pos.z)
        new_ent.loc.rot = quaternion_from_euler(item.rot.roll, item.rot.pitch, item.rot.yaw)
        new_ent.loc.pivot_position = item.pivotPosition
        map_ents.ents.append(new_ent)

    return [map_ents]


def extract_MeshCrystal(mesh_crystal, opts):
    assert mesh_crystal.classId == 0x09003000

    materials = []
    for mat in mesh_crystal.body[0x9003003].materials:
        if mat.materialName != "":
            materials.append(mat)
        else:
            materials.append(mat_from_CPlugMaterialUserInst(mat.materialUserInst))

    content = []
    for layer in mesh_crystal.body[0x9003005].layers:
        if opts.get("visible_only") and not layer.content.isVisible:
            continue
        if layer.type == "Geometry" or layer.type == "Trigger":
            assert layer.content.crystal.isEmbeddedCrystal
            crystal = layer.content.crystal.embeddedCrystal

            mesh = RawMesh()
            mesh.vertices = crystal.vertices
            # TODO add unfaced edges?
            mesh.uvs = [[crystal.uvsCoords[idx] for idx in crystal.uvsIndicies]]
            mesh.materials = []
            mesh.faces = []
            mesh.facesMaterials = []
            materials_mapping = {}
            for face in crystal.faces:
                mesh.faces.append(face.inds)
                if face.material_index not in materials_mapping:
                    materials_mapping[face.material_index] = len(mesh.materials)
                    mesh.materials.append(materials[face.material_index])
                mesh.facesMaterials.append(materials_mapping[face.material_index])

            if layer.type == "Geometry":
                if not layer.content.isVisible:
                    mesh.label = "_notvisible_"
                elif not layer.content.isCollidable:
                    mesh.label = "_notcollidable_"
            else:
                mesh.label = "_trigger_"

            content.append(mesh)

        # TODO trigger
        # TODO spawnLoc

    return content


def convert_verts_data_to_face_corners_data(verts_data, faces):
    face_corners_data = []
    for indicies in faces:
        for i in indicies:
            face_corners_data.append(verts_data[i])
    return face_corners_data


def extract_mesh_CPlugVisualIndexedTriangles(data):
    mesh = RawMesh()
    mesh.vertices = []
    mesh.normals = []
    mesh.colors = []
    mesh.faces = []
    mesh.uvs = []

    if 0x0900600F in data.body:
        visual_chunk_id = 0x0900600F
    elif 0x0900600E in data.body:
        visual_chunk_id = 0x0900600E
    elif 0x0900600D in data.body:
        visual_chunk_id = 0x0900600D
    else:
        raise Exception("unknown body")

    # faces
    index_buffer_body = data.body[0x0906A001].indexBuffer
    if 0x09057000 in index_buffer_body:
        index_buffer = index_buffer_body[0x09057000]
        assert index_buffer.flags == 2  # TODO, find another case
        # indexes are absolute so insert them
        for i in range(0, len(index_buffer.indices), 3):
            mesh.faces.append(index_buffer.indices[i : i + 3])

    elif 0x09057001 in index_buffer_body:
        index_buffer = index_buffer_body[0x09057001]
        assert index_buffer.flags & 0xC == 0  # TODO, find another case

        sub_visuals = data.body[0x9006005].sub_visuals
        if not sub_visuals:
            sub_visuals = [Container(x=0, y=0, z=len(index_buffer.indices))]

        for sub_visual in sub_visuals[:1]:  # TODO animate
            # convert to absolute
            current_vertex = sub_visual.x
            for i in range(sub_visual.y, sub_visual.z, 3):
                current_vertex += index_buffer.indices[i]
                x = current_vertex
                current_vertex += index_buffer.indices[i + 1]
                y = current_vertex
                current_vertex += index_buffer.indices[i + 2]
                mesh.faces.append((x, y, current_vertex))
    else:
        raise Exception("unknown case")

    vertex_streams = data.body[visual_chunk_id].vertexStreams

    if len(vertex_streams) == 0:
        # vertices
        if data.body[0x0902C004]._flags.UseVertexColor:
            mesh.colors = [[]]
        for v in data.body[0x0902C004].vertices:
            mesh.vertices.append(v.position)
            if data.body[0x0902C004]._flags.UseVertexNormal:
                mesh.normals.append(v.normal)
            if data.body[0x0902C004]._flags.UseVertexColor:
                mesh.colors[0].append(v.color)
        # uvs
        for i, texCoord in enumerate(data.body[visual_chunk_id].texCoords):
            assert i < 2  # TODO find another case
            uvs_array = []
            for tex in texCoord.tex_coords:
                uvs_array.append(tex.uv)
            mesh.uvs.append(convert_verts_data_to_face_corners_data(uvs_array, mesh.faces))
    else:
        assert len(vertex_streams) == 1  # TODO, find another case
        verts_uvs = []
        vertex_stream = vertex_streams[0].body[0x09056000]
        blend_indicies = None
        for data_idx, data_decl in enumerate(vertex_stream.DataDecl):
            if data_decl.header.Name == "Position":
                mesh.vertices = vertex_stream.Data[data_idx]
            elif data_decl.header.Name == "Normal":
                mesh.normals = vertex_stream.Data[data_idx]
            elif data_decl.header.Name.startswith("TexCoord"):
                verts_uvs.append(vertex_stream.Data[data_idx])
            elif data_decl.header.Name.startswith("Color"):
                mesh.colors.append(vertex_stream.Data[data_idx])
            elif data_decl.header.Name == "BlendIndices":
                blend_indicies = vertex_stream.Data[data_idx]

        for verts_uv in verts_uvs:
            mesh.uvs.append(convert_verts_data_to_face_corners_data(verts_uv, mesh.faces))

    return mesh


def extract_CPlugSolid2Model(data, _parent, opts):
    assert data.classId == 0x090BB000

    obj_chunk = data.body[0x090BB000]

    visuals = []
    for i, geom in enumerate(obj_chunk.shadedGeoms):
        # filter LOD
        match opts.get("lod", "all"):
            case "highest":
                if geom.lod & 1 == 0:
                    continue
            case "lowest":
                if geom.lod & (1 << len(obj_chunk.lodDistances)) == 0:
                    continue
        visual = extract_mesh_CPlugVisualIndexedTriangles(obj_chunk.visuals[geom.visualIndex])
        visual.materials = []
        if opts.get("lod", "all") == "all":
            visual.lod = geom.lod

        # Material

        if len(obj_chunk.materialsNames) > 0:
            mat = RawMaterial()
            mat.link = obj_chunk.materialsNames[geom.materialIndex]
        else:
            if obj_chunk.materialInstsLtV16 is not None and len(obj_chunk.materialInstsLtV16) > 0:
                mat_class = obj_chunk.materialInstsLtV16[geom.materialIndex]
            elif obj_chunk.materials is not None and len(obj_chunk.materials) > 0:
                mat_class = obj_chunk.materials[geom.materialIndex]
            else:
                mat_class = obj_chunk.customMaterials[geom.materialIndex].materialUserInst

            assert type(mat_class) != str
            mat = mat_from_CPlugMaterialUserInst(mat_class)

        # filter GrassFence
        if opts.get("filter_grassfence", False) and mat.link.lower() == "grassfence":
            continue

        visual.materials.append(mat)

        visuals.append(visual)

    return visuals


def extract_meshes2(root_data, data, off_pos=None, off_rot=None, extracted_files=None):
    if off_pos is None:
        off_pos = []
    if off_rot is None:
        off_rot = []

    if "nodes" in data:
        root_data = data

    elif data.classId in (0x9119000, 0x9160000):
        return []
    else:
        print("skip " + hex(data.classId))
        return []


def extract_block_variant(root_data, variant_body, variant_name, opts):
    variant = BlockVariant()
    variant.name = variant_name
    variant.mobils = {}
    variant.content = []

    # print(variant_name)
    for mobil_idx, mobil in enumerate(variant_body[0x0315B005].mobils):
        # print("\tmobil" + str(mobil_idx))
        for sub_mobil_idx, sub_mobil in enumerate(mobil):
            # print("\t\tsub_mobil" + str(sub_mobil_idx))
            mobil_key = f"mobil{mobil_idx}_submobil{sub_mobil_idx}"
            variant.mobils[mobil_key] = extract_content(sub_mobil, root_data, opts)

    # waypoint spawn loc
    waypoint_type = root_data.body[0x0304E026].waypointType
    if need_spawn(waypoint_type):
        assert variant_body[0x0315B008].version >= 2

        spawn = SpawnLoc()
        variant.content.append(spawn)

        pos3d = variant_body[0x0315B008].spawn
        spawn.pos.x, spawn.pos.y, spawn.pos.z = pos3d.x, pos3d.y, pos3d.z
        spawn.rot = quaternion_from_euler(pos3d.roll, pos3d.pitch, pos3d.yaw)

    # trigger
    trigger_shape = variant_body[0x0315B006].waypointTriggerShape
    variant.content += label_all_meshes(extract_content(trigger_shape, root_data, opts), "_trigger_")

    # TODO clips

    return [variant]


def surf_to_content(surf, opts):
    if opts.get("visible_only"):
        return []

    if surf.type == "Mesh":
        mesh = RawMesh()
        mesh.faces = []
        mesh.materials = []
        mats = {}
        mesh.facesMaterials = []
        mesh.label = "_notvisible_"
        mesh.vertices = surf.data.vertices
        for tri in surf.data.triangles:
            mesh.faces.append((tri.face.x, tri.face.y, tri.face.z))

            mat_id = (tri.materialId.physicsId, tri.materialId.gameplayId)
            if mat_id not in mats:
                mat = RawInvisibleMaterial()
                mat.physicsId = tri.materialId.physicsId
                mat.gameplayId = tri.materialId.gameplayId
                mats[mat_id] = len(mesh.materials)
                mesh.materials.append(mat)

            mesh.facesMaterials.append(mats[mat_id])
        return [mesh]
    elif surf.type == "Compound":
        ents = Entities()
        ents.models = {}
        ents.ents = []

        for i, surface in enumerate(surf.data.surfaces):
            ents.models[i] = surf_to_content(surface, opts)
            loc = iso4_to_spawnloc(surf.data.locs[i])

            new_ent = Entity()
            new_ent.model_idx = i
            new_ent.loc = Loc()
            new_ent.loc.pos = loc.pos
            new_ent.loc.rot = loc.rot
            ents.ents.append(new_ent)

        return [ents]
    elif surf.type == "ConvexPolyhedron":
        mesh = RawMesh()
        mesh.faces = []
        mesh.label = "_notvisible_"
        mesh.vertices = surf.data.vertices
        for start, length in surf.data.faces:
            mesh.faces.append(surf.data.facesIndicies[start : start + length])

        return [mesh]
    else:
        warn(opts, "unsupported CPlugSurface: " + surf.type)
        return []

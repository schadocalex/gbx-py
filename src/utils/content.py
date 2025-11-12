from construct import Container

from .math import quaternion_from_matrix, quaternion_from_euler


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
    pos = Container(x=0, y=0, z=0)
    rot = Container(x=0, y=0, z=0, w=1)
    model_idx = -1


class Entities:
    models = None
    ents = None


class BlockVariant:
    name = ""
    mobils = None
    content = None


class Loc:
    pos = Container(x=0, y=0, z=0)
    rot = Container(x=0, y=0, z=0, w=1)


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


def warn(opts, s):
    opts["root"]._warns.append(s)
    print(opts["root"]._warns[-1])


def label_all_meshes(content, label):
    for obj in content:
        if isinstance(obj, RawMesh):
            obj.label = label
    return content


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


def remap_materials(content, remap):
    for obj in loop_objects(content):
        if isinstance(obj, RawMesh):
            for mat in obj.materials:
                if isinstance(mat, RawMaterial) and mat.link in remap:
                    mat.link = remap[mat.link]


def apply_mat_modifier(content, mat_modifier):
    if (
        not mat_modifier.get("MaterialModifier")
        or mat_modifier.MaterialModifier._index < 0
        or mat_modifier.MaterialModifier.get("_errors")
    ):
        return
    assert mat_modifier.classId == 0x0915D000

    if 0x915D001 in mat_modifier.body and mat_modifier.body[0x915D001].get("name") == "Turbo":
        return  # because the Turbo materials variants doesn't exist in blendermania, we need to take defautl ones. TODO

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


def extract_content(data, parent=None, opts=None, root=None):
    if data is None or ("_index" in data and data._index == -1):
        return []
    if opts is None:
        opts = {}
    if "root" not in opts:
        opts["root"] = data

    if "classId" not in data:
        if "_index" in data and "_relativeFilePath" in data:
            warn(opts, f"missing file, ignoring: {data._relativeFilePath}")
            return []
        raise Exception(data._error if "_error" in data else data)

    # CGameItemModel
    if data.classId == 0x2E002000:
        chunk = data.body[0x2E002019]

        model_edition_content = extract_content(chunk.EntityModelEdition, data, opts)
        model_content = extract_content(chunk.EntityModel, data, opts)
        # TODO data.body[0x2E00201F].waypointType
        # add the metadata somewhere? Metadata(key="waypoint", value=waypointType)?

        content = model_edition_content + model_content

        # remap materials
        apply_mat_modifier(content, chunk.MaterialModifier)

        return content

    # CGameCommonItemEntityModelEdition
    elif data.classId == 0x2E026000:
        return extract_MeshCrystal(data.body[0x2E026000].meshCrystal)

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
            if ent.model._index not in ents.models:
                ents.models[ent.model._index] = extract_content(ent.model, data, opts)

            new_ent = Entity()
            new_ent.model_idx = ent.model._index
            new_ent.pos = ent.pos
            new_ent.rot = ent.rot
            ents.ents.append(new_ent)

        return [ents]

    # CPlugSolid2Model
    elif data.classId == 0x090BB000:
        return extract_CPlugSolid2Model(data, parent)

    # CPlugSurface
    elif data.classId == 0x0900C000:
        return surf_to_content(data.body[0x900C003].surf, opts)

    # CPlugDynaObjectModel
    elif data.classId == 0x09144000:
        content = []

        content += label_all_meshes(extract_content(data.body.Mesh, data, opts), "_notcollidable_")
        if data.body.DynaShape._index > 0:
            content += label_all_meshes(extract_content(data.body.DynaShape, data, opts), "_dynashape_")
        if data.body.StaticShape._index > 0:
            content += label_all_meshes(extract_content(data.body.StaticShape, data, opts), "_staticshape_")

        return content

    # CGameCtnBlockInfoClassic
    elif data.classId == 0x03051000:
        content = []
        content += extract_block_variant(data, data.body[0x0304E023].variantBaseGround, "ground0", opts)
        content += extract_block_variant(data, data.body[0x0304E023].variantBaseAir, "air0", opts)
        for idx, variant_ground in enumerate(data.body[0x0304E027].additionalVariantsGround):
            content += extract_block_variant(data, variant_ground.body, f"ground{idx + 1}", opts)
        for idx, variant_air in enumerate(data.body[0x0304E02C].additionalVariantsAir):
            content += extract_block_variant(data, variant_air.body, f"air{idx + 1}", opts)

        # remap materials
        apply_mat_modifier(content, data.body[0x0304E031].materialModifier)

        return content

    # CGameCtnBlockInfoMobil
    elif data.classId == 0x03122000:
        prefab_fid = data.body[0x03122003].prefab_fid
        if prefab_fid._index < 0:
            return []
        return extract_content(prefab_fid, data, opts)

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
        variant = BlockVariant()  # TODO generic variant
        variant.name = "variants"
        variant.mobils = {}
        for i, child in enumerate(data.body.variants):
            variant.mobils["variant" + str(i)] = extract_content(child.EntityModel, data, opts)
        return [variant]

    else:
        warn(opts, f"unsupported classId: {hex(data.classId)}")
        return []


def extract_MeshCrystal(mesh_crystal):
    assert mesh_crystal.classId == 0x09003000

    materials = []
    for mat in mesh_crystal.body[0x9003003].materials:
        if mat.materialName != "":
            materials.append(mat)
        else:
            materials.append(mat_from_CPlugMaterialUserInst(mat.materialUserInst))

    content = []
    for layer in mesh_crystal.body[0x9003005].layers:
        if layer.type == "Geometry" or layer.type == "Trigger":
            assert layer.content.crystal.isEmbeddedCrystal == True
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

        # faces
        index_buffer = data.body[0x0906A001].indexBuffer[0x09057000]
        assert index_buffer.flags == 2  # TODO, find another case
        for i in range(0, len(index_buffer.indices), 3):
            mesh.faces.append((index_buffer.indices[i], index_buffer.indices[i + 1], index_buffer.indices[i + 2]))

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

            # convert to absolute
            current_face = 0
            for i in range(0, len(index_buffer.indices), 3):
                current_face += index_buffer.indices[i]
                x = current_face
                current_face += index_buffer.indices[i + 1]
                y = current_face
                current_face += index_buffer.indices[i + 2]
                mesh.faces.append((x, y, current_face))
        else:
            raise Exception("unknown case")

        for verts_uv in verts_uvs:
            mesh.uvs.append(convert_verts_data_to_face_corners_data(verts_uv, mesh.faces))

    return mesh


def extract_CPlugSolid2Model(data, parent=None):
    assert data.classId == 0x090BB000

    obj_chunk = data.body[0x090BB000]

    visuals = []
    for i, geom in enumerate(obj_chunk.shadedGeoms):
        visual = extract_mesh_CPlugVisualIndexedTriangles(obj_chunk.visuals[geom.visualIndex])
        visual.materials = []
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
            new_ent.pos = loc.pos
            new_ent.rot = loc.rot
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

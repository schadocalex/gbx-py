class RawMaterial:
    link = ""
    physicId = None
    gameplayId = None
    color = None


class RawMesh:
    # vertices attributes
    vertices = None
    normals = None
    uv0 = None
    uv1 = None
    uv2 = None
    colors = None

    # faces
    faces = None
    materials = None
    facesMaterials = None  # if len(materials) > 0

    # misc
    lod = 0
    label = ""


class Entity:
    pos = 0, 0, 0
    rot = 0, 0, 0, 1
    instance_idx = -1


class Entities:
    models = None
    ents = None


def label_all_meshes(content, label):
    for obj in content:
        if isinstance(obj, RawMesh):
            obj.label = label
    return content


def mat_from_CPlugMaterialUserInst(data):
    mat = RawMaterial()
    mat.link = data.body[0x090FD000].link
    mat.physicId = data.body[0x090FD000].surfacePhysicId
    mat.gameplayId = data.body[0x090FD000].surfaceGameplayId
    mat.color = data.body[0x090FD000].color
    return mat


def extract_content(data, parent=None):
    if "_index" in data and data._index == -1:
        return []

    # CGameItemModel
    if data.classId == 0x2E002000:
        model_edition_content = extract_content(data.body[0x2E002019].EntityModelEdition, data)
        model_content = extract_content(data.body[0x2E002019].EntityModel, data)
        # TODO data.body[0x2E00201F].waypointType

        return model_edition_content + model_content

    # CGameCommonItemEntityModel
    elif data.classId == 0x2E027000:
        chunk = data.body[0x2E027000]

        objects_content = extract_content(chunk.staticObject, data)

        trigger_shape_content = label_all_meshes(extract_content(chunk.props.triggerShape, data), "_trigger_")

        # TODO data.body[0x2e027000].props.spawnLoc

        return objects_content + trigger_shape_content

    # CPlugStaticObjectModel
    elif data.classId == 0x09159000:
        meshes = extract_content(data.body.Mesh, data)
        if data.body.isMeshCollidable:
            if parent is not None and parent.classId != 0x2E027000:
                label_all_meshes(meshes, "_notcollidable_")
            return meshes
        else:
            label_all_meshes(meshes, "_notcollidable_")
            shapes = extract_content(data.body.Shape, data)
            return meshes + shapes

    # SPlugPrefab
    elif data.classId == 0x09145000:
        ents = Entities()
        ents.models = {}
        ents.ents = []
        for ent_idx, ent in enumerate(data.body.Ents):
            if ent.model._index not in ents.models:
                ents.models[ent.model._index] = extract_content(ent.model, data)

            new_ent = Entity()
            new_ent.instance_idx = ent.model._index
            new_ent.pos = ent.pos
            new_ent.rot = ent.rot
            ents.ents.append(new_ent)

        return [ents]

    # CPlugSolid2Model
    elif data.classId == 0x090BB000:
        return extract_CPlugSolid2Model(data, parent)

    # CPlugSurface
    elif data.classId == 0x0900C000:
        surf = data.body[0x900C003].surf
        if surf.type == "Mesh":
            mesh = RawMesh()
            mesh.faces = []
            mesh.materials = []
            mesh.facesMaterials = []
            mesh.label = "_notvisible_"
            mesh.vertices = surf.data.vertices
            for tri in surf.data.triangles:
                mesh.faces.append((tri.face.x, tri.face.y, tri.face.z))
                mat = tri.materialId.physicsId + (
                    ("_" + tri.materialId.gameplayId) if tri.materialId.gameplayId != "No" else ""
                )
                if mat in mesh.materials:
                    index = mesh.materials.index(mat)
                else:
                    index = len(mesh.materials)
                    mesh.materials.append(mat)
                mesh.facesMaterials.append(index)
            return [mesh]
        else:
            print("unsupported CPlugSurface: " + surf.type)
            return []
    else:
        print("unsupported classId: " + str(data.classId))
        return []


def extract_CPlugSolid2Model(data, parent=None):
    assert data.classId == 0x090BB000

    obj_chunk = data.body[0x090BB000]

    meshes = []
    for i, geom in enumerate(obj_chunk.shadedGeoms):
        mesh = RawMesh()
        mesh.materials = []
        mesh.uv0 = []
        mesh.uv1 = []
        mesh.vertices = []
        mesh.normals = []
        mesh.faces = []
        mesh.lod = geom.lod
        meshes.append(mesh)

        visual = obj_chunk.visuals[geom.visualIndex]

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
        mesh.materials.append(mat)

        continue_meshes = False
        vertex_streams = visual.body[0x0900600F].vertexStreams
        if len(vertex_streams) == 0:
            for i, texCoord in visual.body[0x0900600F].texCoords:
                for tex in texCoord.tex_coords:
                    if i == 0:
                        mesh.uv0.append(tex.uv)
                    elif i == 1:
                        mesh.uv1.append(tex.uv)
            for v in visual.body[0x0902C004].vertices:
                mesh.vertices.append(v.position)
                mesh.normals.append(v.normal)
            if chunk.chunkId == 0x0906A001:
                index_buffer = visual.body[0x0906A001].indexBuffer[0x09057001]
                assert index_buffer.flags == 2  # TODO, find a case
                mesh.faces = index_buffer.indices
        else:
            assert len(vertex_streams) == 1  # TODO, find a case
            vertex_stream = vertex_streams[0].body[0x09056000]
            for data_idx, data_decl in enumerate(vertex_stream.DataDecl):
                if data_decl.header.Name == "Position":
                    mesh.vertices = vertex_stream.Data[data_idx]
                elif data_decl.header.Name == "Normal":
                    mesh.normals = vertex_stream.Data[data_idx]
                elif data_decl.header.Name == "TexCoord0":
                    mesh.uv0 = vertex_stream.Data[data_idx]
                elif data_decl.header.Name == "TexCoord1":
                    mesh.uv1 = vertex_stream.Data[data_idx]

            index_buffer = visual.body[0x0906A001].indexBuffer[0x09057001]
            assert index_buffer.flags == 2  # TODO, find a case

            # convert to absolute
            current_face = 0
            for i in range(0, len(index_buffer.indices), 3):
                current_face += index_buffer.indices[i]
                x = current_face
                current_face += index_buffer.indices[i + 1]
                y = current_face
                current_face += index_buffer.indices[i + 2]
                mesh.faces.append((x, y, current_face))
            pass
            # TODO check relative/absolute face indexes

    return meshes


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

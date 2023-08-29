import os
from construct import Container, ListContainer


def quaternion_rotation(x, y, z, q):
    q0 = q.w
    q1 = q.x
    q2 = q.y
    q3 = q.z

    # First row of the rotation matrix
    r00 = 2 * (q0 * q0 + q1 * q1) - 1
    r01 = 2 * (q1 * q2 - q0 * q3)
    r02 = 2 * (q1 * q3 + q0 * q2)

    # Second row of the rotation matrix
    r10 = 2 * (q1 * q2 + q0 * q3)
    r11 = 2 * (q0 * q0 + q2 * q2) - 1
    r12 = 2 * (q2 * q3 - q0 * q1)

    # Third row of the rotation matrix
    r20 = 2 * (q1 * q3 - q0 * q2)
    r21 = 2 * (q2 * q3 + q0 * q1)
    r22 = 2 * (q0 * q0 + q3 * q3) - 1

    # 3x3 rotation matrix
    # rot_matrix = np.array([[r00, r01, r02],
    #                        [r10, r11, r12],
    #                        [r20, r21, r22]])

    new_x = r00 * x + r01 * y + r02 * z
    new_y = r10 * x + r11 * y + r12 * z
    new_z = r20 * x + r21 * y + r22 * z

    return new_x, new_y, new_z


def transform_pos(pos, ps, qs):
    x, y, z = pos.x, pos.y, pos.z

    if ps is not None:
        for i in range(len(ps)):
            p, q = ps[i], qs[i]

            x, y, z = quaternion_rotation(x, y, z, q)

            x += p.x
            y += p.y
            z += p.z

    # convert in blender space
    return [x, -z, y]


def export_obj(filename, vertices, normals, uv0, indices, material_name, pos=None, rot=None):
    N = len(vertices)

    # print(f"export_obj {filename} {pos} {rot}")

    with open(filename, "w") as f:
        f.write(f"o {os.path.basename(filename)}\n")
        for v in vertices:
            v2 = transform_pos(v, pos, rot)
            f.write(f"v {v2[0]} {v2[1]} {v2[2]}\n")
        for n in normals:
            n2 = transform_pos(n, pos, rot)
            f.write(f"vn {n2[0]} {n2[1]} {n2[2]}\n")
        for uv in uv0:
            f.write(f"vt {uv.x} {uv.y}\n")
        f.write(f"usemtl {material_name}\n")

        current_indice = 0
        for i, indice in enumerate(indices):
            current_indice = (current_indice + indice) % N

            if (i % 3) == 0:
                f.write("f")

            f.write(f" {current_indice+1}/{current_indice+1}/{current_indice+1}")

            if (i % 3) == 2:
                f.write("\n")


def export_obj2(filename, vertices, faces, material_name):  # surf
    N = len(vertices)

    with open(filename, "w") as f:
        f.write(f"o {os.path.basename(filename)}\n")
        for v in vertices:
            f.write(f"v {v.x} {v.z} {-v.y}\n")
        f.write(f"usemtl {material_name}\n")

        for face in faces:
            f.write(f"f {face.x+1} {face.y+1} {face.z+1}\n")


def extract_solid2model(data, node, lod=1):
    assert node.header.class_id == 0x090BB000

    obj_chunk = node.body[0].chunk

    if len(obj_chunk.lodDistances) == 0:
        lod = 1
    elif len(obj_chunk.lodDistances) < lod:
        lod = obj_chunk.lodDistances
    lod = 2 ** (lod - 1)

    meshes = []
    for i, geom in enumerate(obj_chunk.shaded_geoms):
        if (geom.lod & lod) == 0:
            continue

        visual_idx = obj_chunk.visuals[geom.visual_index]

        vertices = []
        normals = []
        uv0 = []

        root_node = data  # node if "nodes" in node else node.root_node
        vertex_stream = root_node.nodes[visual_idx + 1].body[0].chunk
        for data_idx, data_decl in enumerate(vertex_stream.DataDecl):
            match data_decl.header.Name:
                case "Position":
                    vertices = vertex_stream.Data[data_idx]
                case "Normal":
                    normals = vertex_stream.Data[data_idx]
                case "TexCoord0":
                    uv0 = vertex_stream.Data[data_idx]

        indices = root_node.nodes[visual_idx].body[8].chunk.index_buffer[0].chunk.indices

        if len(obj_chunk.materials_names) > 0:
            mat = obj_chunk.materials_names[geom.material_index]
        else:
            if len(obj_chunk.materials) > 0:
                mat_idx = obj_chunk.materials[geom.material_index]
            else:
                mat_idx = obj_chunk.custom_materials[geom.material_index].material_user_inst

            if type(root_node.nodes[mat_idx]) == str:
                mat = root_node.nodes[mat_idx].split(".")[0]
            else:
                mat = root_node.nodes[mat_idx].body[0].chunk.link

        meshes.append([vertices, normals, uv0, indices, mat])

    return meshes


def export_meshes(export_dir, filename, meshes, pos=None, rot=None):
    for sub_mesh_idx, sub_mesh in enumerate(meshes):
        obj_filepath = export_dir + filename + f"_{sub_mesh_idx}.obj"
        print(obj_filepath)
        # print(sub_mesh)
        # print(final_pos)
        # print(final_rot)
        export_obj(obj_filepath, *sub_mesh, pos, rot)


def export_ents(export_dir, file, data, offset_index=None, off_pos=None, off_rot=None):
    if offset_index is None:
        offset_index = []
    if off_pos is None:
        off_pos = []
    if off_rot is None:
        off_rot = []

    assert data.header.class_id == 0x09145000

    if not os.path.exists(export_dir):
        os.makedirs(export_dir)

    def extract_mesh(data, static_node, lod, offset_index, ent_idx, off_pos, off_rot):
        if static_node.header.class_id == 0x09145000:
            export_ents(
                export_dir,
                file,
                static_node,
                [*offset_index, ent_idx],
                off_pos,
                off_rot,
            )
            return None
        if static_node.header.class_id == 0x900C000:
            # skip surf (for now?)
            return None
        if static_node.header.class_id != 0x09159000:
            print("skip " + hex(static_node.header.class_id))
            return None

        node = data.nodes[static_node.body.mesh]
        if node.header.class_id == 0x09145000:
            export_ents(
                export_dir,
                file,
                node,
                [*offset_index, ent_idx],
                off_pos,
                off_rot,
            )
            return None
        if node.header.class_id == 0x09159000:
            # TODO why we have that case?
            node = data.nodes[node.body.mesh]

        return extract_solid2model(data, node)

    for ent_idx, ent in enumerate(data.body.Ents):
        model = data.nodes[ent.model]
        if type(model) == str:
            print("skip " + model)
            continue

        final_pos = [ent.pos, *off_pos]
        final_rot = [ent.rot, *off_rot]

        meshes = extract_mesh(data, model, 1, offset_index, ent_idx, final_pos, final_rot)
        filename = (
            os.path.basename(file).split(".")[0]
            + ("_" if len(offset_index) > 0 else "")
            + "_".join(map(str, offset_index))
            + f"_{ent_idx}"
        )
        export_meshes(export_dir, filename, meshes, final_pos, final_rot)

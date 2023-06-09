import os


def export_obj(filename, vertices, normals, uv0, indices, material_name):
    N = len(vertices)

    with open(filename, "w") as f:
        f.write(f"o {os.path.basename(filename)}\n")
        for v in vertices:
            f.write(f"v {v.x} {v.z} {-v.y}\n")
        for n in normals:
            f.write(f"vn {n.x} {n.z} {-n.y}\n")
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

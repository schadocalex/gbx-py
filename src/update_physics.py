import os
import sys
from glob import glob

from PySide6.QtWidgets import QApplication, QFileDialog

from .parser import parse_file, generate_file
from .editor import GbxEditorUi, GbxEditorUiWindow
from .utils.misc import update_surf

GUI = False


def get_all_models(data):
    if data.classId == 0x2E002000:
        yield from get_all_models(data.body[0x2E002019].EntityModel)
    elif data.classId == 0x09145000:
        for ent in data.body.Ents:
            if ent.model._index > 0:
                yield from get_all_models(ent.model)
    elif data.classId == 0x09159000:
        yield data
    elif data.classId == 0x09144000:
        yield data
    elif data.classId == 0x2F0CA000:
        pass
    else:
        print("Unknown classId: " + str(data.classId))


def update_surf(surf, from_physics_id, to_physics_id):
    for materialId in surf.body[0x0900C003].materialsIds:
        if materialId.physicsId == from_physics_id:
            materialId.physicsId = to_physics_id

    for tri in surf.body[0x0900C003].surf.data.triangles:
        if tri.materialId.physicsId == from_physics_id:
            tri.materialId.physicsId = to_physics_id


def main():
    if GUI:
        app = QApplication.instance() or QApplication(sys.argv)
        win = GbxEditorUiWindow()
        win.setWindowTitle("Before")
        win2 = GbxEditorUiWindow()
        win2.setWindowTitle("After")

    # loop over all items
    for file in glob(r"./items/*.Item.Gbx", recursive=True):
        print(file)
        data = parse_file(file)

        if GUI:
            win.set_data(data)

        for model in get_all_models(data):
            # Meshes

            for custom_mat in model.body.Mesh.body[0x90BB000].customMaterials:
                mat = custom_mat.materialUserInst.body[0x90FD000]
                if mat.surfacePhysicId == "Ice":  # and mat.materialName == "m0"
                    mat.surfacePhysicId = "RoadIce"
                if mat.link == "Stadium\Media\Modifier\PlatformIce\PlatformTech":
                    mat.link = "MyNewMaterial"

            # collidables shapes

            if model.classId == 0x09159000:
                # Static object

                if model.body.Shape._index > 0:
                    update_surf(model.body.Shape, "Ice", "RoadIce")

            elif model.classId == 0x09144000:
                # Dyna object

                update_surf(model.body.DynaShape, "Ice", "RoadIce")
                # assume StaticShape is the same model

        # Generate the new file and overwrite it
        if not GUI:
            with open(file, "wb") as f:
                f.write(generate_file(data))

        if GUI:
            win2.set_data(data)
            app.exec()
            return  # only show GUI for the first item

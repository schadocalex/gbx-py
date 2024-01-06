import sys
import os
import subprocess

import bpy

from ..utils.Functions import reload_current_blend_file, timer
from ..operators.OT_Settings import TM_OT_Settings_OpenMessageBox

MODULES_FOLDER = bpy.utils.user_resource("SCRIPTS", path="modules") + os.path.sep
PYTHON_BIN = sys.executable


def run_pip_command(*cmds, run_module="pip"):
    command = [PYTHON_BIN, "-m", run_module, *cmds]

    print(" ".join(command))
    return subprocess.run(command, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


classes = None
panel_registered = False
installation_success = False


class TM_PT_NICE_installer(bpy.types.Panel):
    bl_label = "NICE"
    bl_idname = "TM_PT_NICE_installer"
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
            "Nadeo Importer Community Edition",
            "",
            "To use NICE, you must install python dependencies.",
            "Blender will freeze during the installation, don't worry!",
        )

    def draw(self, context):
        layout = self.layout

        box = layout.box()

        if installation_success:
            col = box.column()
            col.label(text="Installation successful!", icon="CHECKMARK")
            col.label(text="Reloading blender ...", icon="BLANK1")
        
        else:
            box.label(text="Nadeo Importer Community Edition")
            col = box.column()
            col.alert = True
            col.scale_y = .7
            col.label(text="Dependencies are missing.")
            col.alert = False
            col.label(text="Install below to use NICE.")
            col.label(text="Save your blender file before installing")
            col.label(text="(expect freeze & auto restart)")

            row = layout.row()
            row.scale_y = 1.5
            row.operator("view3d.tm_nice_install_deps", text="Install NICE dependencies")


def try_register():
    try:
        from .blender.importer import TM_OT_NICE_Item_Import, TM_PT_NICE

        global classes
        classes = (TM_OT_NICE_Item_Import, TM_PT_NICE)

        for cls in classes:
            bpy.utils.register_class(cls)

        return True
    except ModuleNotFoundError as err:
        print("ModuleNotFoundError")
        print(err)
        return False


class TM_OT_NICE_Item_Install_Deps(bpy.types.Operator):
    bl_idname = "view3d.tm_nice_install_deps"
    bl_description = "Install NICE dependencies using pip."
    bl_label = "Install NICE dependencies"

    def execute(self, context):
        run_pip_command(run_module="ensurepip")
        run_pip_command("install", "--target", MODULES_FOLDER, "construct", "python-lzo", "Pillow")

        # display reload text
        global installation_success
        installation_success = True

        def run(): 
            reload_current_blend_file()
                
        timer(run, 2)

        return {"FINISHED"}


def NICE_register():
    if not try_register():
        bpy.utils.register_class(TM_OT_NICE_Item_Install_Deps)
        bpy.utils.register_class(TM_PT_NICE_installer)
        global panel_registered
        panel_registered = True


def NICE_unregister():
    if panel_registered:
        bpy.utils.unregister_class(TM_OT_NICE_Item_Install_Deps)
        bpy.utils.unregister_class(TM_PT_NICE_installer)

    if classes is not None:
        for cls in reversed(classes):
            bpy.utils.unregister_class(cls)

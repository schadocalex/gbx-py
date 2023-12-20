import sys
import os

import bpy
from .blender.importer import TM_OT_NICE_Item_Import, TM_PT_NICE

classes = (TM_OT_NICE_Item_Import, TM_PT_NICE)


def NICE_register():
    for cls in classes:
        bpy.utils.register_class(cls)


def NICE_unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

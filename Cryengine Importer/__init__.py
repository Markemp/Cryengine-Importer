# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8 compliant>
#

# Cryengine Importer 1.1 (Blender Python module)
# https://www.heffaypresents.com/GitHub

import bpy
import collections
import bpy.types
import bpy.utils
import array
import bmesh
import glob
import math
import mathutils
import os, os.path
import time
import types
import xml.etree as etree
import xml.etree.ElementTree as ET
from bpy_extras.image_utils import load_image
from bpy_extras.wm_utils import progress_report
from bpy.props import (
        BoolProperty,
        FloatProperty,
        StringProperty,
        EnumProperty,
        )
from bpy_extras.io_utils import (
        ImportHelper,
        ExportHelper,
        orientation_helper,
        path_reference_mode,
        axis_conversion,
        unpack_list,
        )
from math import radians
from . import (
    collections,
    Cryengine_Importer,
    )

bl_info = {
    'name': 'Cryengine Importer', 
    'description': 'Imports Cryengine assets that have been converted to Collada with Cryengine Converter.',
    'author': 'Geoff Gerber',
    'category': 'Import-Export',
    'version': (1, 1, 0),
    'blender': (2, 80, 0),
    'location': 'File > Import-Export',
    'warning': 'Requires all Cryengine .cga and .cgf files to be converted to Collada (.dae) using Cryengine Converter prior to use.',
    'wiki_url': 'https://github.com/markemp/Cryengine-Importer',
    'support': 'TESTING'
    }

#@orientation_helper(axis_forward='Y', axis_up='Z')
class CryengineImporter(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.cryassets"
    bl_label = "Import Cryengine Assets"
    bl_options = {'PRESET', 'UNDO'}
    texture_type: EnumProperty(
        name="Texture Type",
        description = "Identify the type of texture file imported into the Texture nodes.",
        items = (('ON', "DDS", "Reference DDS files for textures."),
                 ('OFF', "TIF", "Reference TIF files for textures."),
                 ),
                )
    path: StringProperty(
        name="Import Directory",
        description="Directory to Import",
        default="",
        maxlen=1024,
        subtype='DIR_PATH')
    auto_save_file: BoolProperty(
        name = "Save File",
        description = "Automatically save file",
        default = True)
    auto_generate_preview: BoolProperty(
        name = "Generate Preview",
        description = "Auto-generate thumbnails",
        default = False)
    filter_glob: StringProperty(
        default="*.dae",
        options={'HIDDEN'})
    use_dds: BoolProperty(
        name = "Use DDS",
        description = "Use DDS format for image textures",
        default = True)
    use_tif: BoolProperty(
        name = "Use TIF",
        description = "Use TIF format for image textures",
        default = False)
    # From ImportHelper.  Filter filenames.
    #path_mode = path_reference_mode
    show_hidden = True
    check_extension = True
    filename_ext = ".dae"
    use_filter_folder = True
    display_type = 'THUMBNAIL'
    title = "Directory to Import"
    def execute(self, context):
        if self.texture_type == 'OFF':
            self.use_tif = True
            self.use_dds = False
        else:
            self.use_dds = True
            self.use_tif = False
        keywords = self.as_keywords(ignore=("texture_type", 
                                            "filter_glob",
                                            "path_mode",
                                            "filepath"
                                            ))
        userpath = self.properties.filepath
        fdir = self.properties.filepath
        keywords["path"] = fdir
        return import_asset(context, **keywords)
    def draw(self, context):
        layout = self.layout
        row = layout.row(align = True)
        box = layout.box()
        box.label(text="Select texture type")
        row = box.row()
        row.prop(self, "texture_type", expand = True)
        row = layout.row(align=True)
        row.prop(self, "auto_save_file")
        row = layout.row(align=True)
        row.prop(self, "auto_generate_preview")

#@orientation_helper(axis_forward='Y', axis_up='Z')
class MechImporter(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.mech"
    bl_label = "Import Mech"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".cdf"
    #path_mode = path_reference_mode
    check_extension = True
    auto_save_file: BoolProperty(
        name = "Save File",
        description = "Automatically save file",
        default = True)
    filter_glob: StringProperty(
        default="*.cdf",
        options={'HIDDEN'}
        ,)
    texture_type: EnumProperty(
        name="Texture Type",
        description = "Identify the type of texture file imported into the Texture nodes.",
        items = (('ON', "DDS", "Reference DDS files for textures."),
                 ('OFF', "TIF", "Reference TIF files for textures."),
                 ),)
    use_dds: BoolProperty(
        name = "Use DDS",
        description = "Use DDS format for image textures",
        default = True)
    use_tif: BoolProperty(
        name = "Use TIF",
        description = "Use TIF format for image textures",
        default = False)
    def execute(self, context):
        if self.texture_type == 'OFF':
            self.use_tif = True
            self.use_dds = False
        else:
            self.use_dds = True
            self.use_tif = False
        keywords = self.as_keywords(ignore=("texture_type", 
                                            "filter_glob",
                                            "path_mode",
                                            "filepath"
                                            ))
        if bpy.data.is_saved and context.preferences.filepaths.use_relative_paths:
            import os
            keywords["relpath"] = os.path.dirname(bpy.data.filepath)
        fdir = self.properties.filepath
        keywords["path"] = fdir
        import_mech(context, **keywords)
        return { 'FINISHED'}
    def draw(self, context):
        layout = self.layout
        row = layout.row(align = True)
        box = layout.box()
        box.label(text="Select texture type")
        row = box.row()
        row.prop(self, "texture_type", expand = True)
        row = layout.row(align=True)
        row.prop(self, "auto_save_file")

#@orientation_helper(axis_forward='Y', axis_up='Z')
class PrefabImporter(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.prefab"
    bl_label = "Import Cryengine Prefab"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".xml"
    #path_mode = path_reference_mode
    check_extension = True
    auto_save_file: BoolProperty(
        name = "Save File",
        description = "Automatically save file",
        default = True)
    filter_glob: StringProperty(
        default="*.xml",
        options={'HIDDEN'},
        )
    texture_type: EnumProperty(
        name="Texture Type",
        description = "Identify the type of texture file imported into the Texture nodes.",
        items = (('ON', "DDS", "Reference DDS files for textures."),
                 ('OFF', "TIF", "Reference TIF files for textures."),
                 ),
    )
    use_dds: BoolProperty(
        name = "Use DDS",
        description = "Use DDS format for image textures",
        default = True)
    use_tif: BoolProperty(
        name = "Use TIF",
        description = "Use TIF format for image textures",
        default = False)
    def execute(self, context):
        if self.texture_type == 'OFF':
            self.use_tif = True
            self.use_dds = False
        else:
            self.use_dds = True
            self.use_tif = False
        keywords = self.as_keywords(ignore=("texture_type", 
                                            "filter_glob",
                                            "path_mode",
                                            "filepath"
                                            ))
        fdir = self.properties.filepath
        keywords["path"] = fdir
        return import_prefab(context, **keywords)
    def draw(self, context):
        layout = self.layout
        row = layout.row(align = True)
        box = layout.box()
        box.label(text="Select texture type")
        row = box.row()
        row.prop(self, "texture_type", expand = True)
        row = layout.row(align=True)
        row.prop(self, "auto_save_file")

# -----------------------------------------------------------------------------
#                                                                          Menu


def menu_func_mech_import(self, context):
    self.layout.operator(MechImporter.bl_idname, text="Import Mech")

def menu_func_import(self, context):
    self.layout.operator(CryengineImporter.bl_idname, text="Import Cryengine Asset")

def menu_func_prefab_import(self, context):
    self.layout.operator(PrefabImporter.bl_idname, text="Import Cryengine Prefab (NYI)")

# -----------------------------------------------------------------------------
#                                                                      Register

# classes = (
#     MechImporter,
#     CryengineImporter,
#     PrefabImporter
# )

def register():
    bpy.utils.register_class(CryengineImporter)
    bpy.utils.register_class(MechImporter)	   
    bpy.utils.register_class(PrefabImporter)	
    bpy.types.TOPBAR_MT_file_import.append(menu_func_mech_import)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)	   
    bpy.types.TOPBAR_MT_file_import.append(menu_func_prefab_import)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_mech_import)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_prefab_import)
    bpy.utils.unregister_class(MechImporter)
    bpy.utils.unregister_class(CryengineImporter)
    bpy.utils.unregister_class(PrefabImporter)

# register, unregister = bpy.utils.register_classes_factory(classes)

# This allows you to run the script directly from blenders text editor
# to test the addon without having to install it.
if __name__ == "__main__":
    register()

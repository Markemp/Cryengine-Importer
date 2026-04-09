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

# Cryengine Importer 4.0 (Blender Python module)
# https://www.heffaypresents.com/GitHub

import bpy
import bpy.types
import bpy.utils
from bpy.props import (
        BoolProperty,
        IntProperty,
        StringProperty,
        EnumProperty)
from bpy_extras.io_utils import ImportHelper, orientation_helper

import os
from . import Cryengine_Importer
from . import animations

# Handoff state for the modal animation import operator
_anim_import_state = {
    "anim_files": [],
    "armature": None,
    "asset_name": "",
}

bl_info = {
    "name": 'Cryengine Importer',
    "description": 'Imports Cryengine assets converted to USD with Cryengine Converter.',
    "author": 'Geoff Gerber',
    "category": 'Import-Export',
    "version": (4, 0, 0),
    "blender": (5, 0, 0),
    "location": 'File > Import-Export',
    "warning": 'Requires all Cryengine .cga and .cgf files to be converted to USD (.usda) using Cryengine Converter 2.0 prior to use.',
    "doc_url": 'https://github.com/markemp/Cryengine-Importer',
    "support": "COMMUNITY"
    }

@orientation_helper(axis_forward='Y', axis_up='Z')
class AssetImporter(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.cryassets"
    bl_label = "Import Cryengine Asset"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".usda"
    check_extension: BoolProperty(
        default=True)
    filter_glob: StringProperty(
        default="*.usda",
        options={'HIDDEN'})
    import_animations: BoolProperty(
        name="Import Animations",
        description="Import animation files found in the same directory",
        default=True)
    animation_filter: StringProperty(
        name="Animation Filter",
        description="Filename pattern to filter animations (e.g. *idle*, *run*)",
        default="*")
    animation_max_count: IntProperty(
        name="Max Animations",
        description="Maximum number of animations to import (0 = unlimited)",
        default=0,
        min=0)

    def execute(self, context):
        import fnmatch
        filepath = self.properties.filepath
        Cryengine_Importer.import_asset_geometry(filepath)

        if self.import_animations:
            anim_files, armature = Cryengine_Importer.discover_asset_animations(filepath)
            if anim_files and armature:
                # Apply filename filter — auto-wrap as *filter* if no wildcards
                if self.animation_filter and self.animation_filter != "*":
                    pattern = self.animation_filter
                    if "*" not in pattern and "?" not in pattern:
                        pattern = f"*{pattern}*"
                    anim_files = [f for f in anim_files
                                  if fnmatch.fnmatch(os.path.basename(f).lower(),
                                                     pattern.lower())]

                # Apply max count limit
                if self.animation_max_count > 0:
                    anim_files = anim_files[:self.animation_max_count]

                if anim_files:
                    _anim_import_state["anim_files"] = anim_files
                    _anim_import_state["armature"] = armature
                    _anim_import_state["asset_name"] = os.path.basename(filepath)
                    bpy.ops.import_scene.cryassets_anims('INVOKE_DEFAULT')

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.prop(self, "import_animations")
        sub = layout.column()
        sub.enabled = self.import_animations
        sub.prop(self, "animation_filter")
        sub.prop(self, "animation_max_count")

@orientation_helper(axis_forward='Y', axis_up='Z')
class MechImporter(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.mech"
    bl_label = "Import Mech"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".cdf"
    check_extension: BoolProperty(
        default=True)
    auto_save_file: BoolProperty(
        name="Save File",
        description="Automatically save file",
        default=True)
    filter_glob: StringProperty(
        default="*.cdf",
        options={'HIDDEN'}
    )
    add_control_bones: BoolProperty(
        name="Add Control Bones",
        description="Add IK bones to make creating animations easier",
        default=True)
    texture_type: EnumProperty(
        name="Texture Type",
        description="Identify the type of texture file imported into the Texture nodes.",
        items=(('ON', "DDS", "Reference DDS files for textures."),
               ('OFF', "TIF", "Reference TIF files for textures."),
        ))
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
                                            "filepath",
                                            "check_extension",
                                            "axis_forward",
                                            "axis_up"))
        if bpy.data.is_saved and context.preferences.filepaths.use_relative_paths:
            import os
            keywords["relpath"] = os.path.dirname(bpy.data.filepath)
        fdir = self.properties.filepath
        keywords["path"] = fdir
        self.add_control_bones
        Cryengine_Importer.import_mech(context, **keywords)
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
        row = layout.row(align=True)
        row.prop(self, "add_control_bones")

@orientation_helper(axis_forward='Y', axis_up='Z')
class PrefabImporter(bpy.types.Operator, ImportHelper):
    bl_idname = "import_scene.prefab"
    bl_label = "Import Cryengine Prefab"
    bl_options = {'PRESET', 'UNDO'}
    filename_ext = ".xml"
    check_extension: BoolProperty(
        default=True)
    auto_save_file: BoolProperty(
        name="Save File",
        description="Automatically save file",
        default=True)
    filter_glob: StringProperty(
        default="*.xml",
        options={'HIDDEN'}
    )
    texture_type: EnumProperty(
        name="Texture Type",
        description="Identify the type of texture file imported into the Texture nodes.",
        items=(('ON', "DDS", "Reference DDS files for textures."),
               ('OFF', "TIF", "Reference TIF files for textures."),
        )
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
                                            "filepath",
                                            "check_extension",
                                            "axis_forward",
                                            "axis_up"
                                            ))
        fdir = self.properties.filepath
        keywords["path"] = fdir
        return Cryengine_Importer.import_prefab(context, **keywords)
    def draw(self, context):
        layout = self.layout
        row = layout.row(align = True)
        box = layout.box()
        box.label(text="Select texture type")
        row = box.row()
        row.prop(self, "texture_type", expand = True)
        row = layout.row(align=True)
        row.prop(self, "auto_save_file")

class AnimationImportModal(bpy.types.Operator):
    """Import animations one at a time with progress feedback."""
    bl_idname = "import_scene.cryassets_anims"
    bl_label = "Importing Animations..."
    bl_options = {'INTERNAL'}

    def invoke(self, context, event):
        self._anim_files = _anim_import_state["anim_files"]
        self._armature = _anim_import_state["armature"]
        self._asset_name = _anim_import_state["asset_name"]
        self._total = len(self._anim_files)
        self._index = 0
        self._imported = 0

        # Find a 3D viewport area for header text
        self._area = None
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                self._area = area
                break

        self._timer = context.window_manager.event_timer_add(0.01, window=context.window)
        context.window_manager.modal_handler_add(self)

        if self._area:
            self._area.header_text_set(
                f"{self._asset_name} — Importing animation 0/{self._total}...")

        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'ESC':
            self._cleanup(context)
            self.report({'INFO'},
                        f"Animation import cancelled. Imported {self._imported}/{self._total}.")
            return {'CANCELLED'}

        if event.type == 'TIMER':
            if self._index >= self._total:
                self._cleanup(context)
                self.report({'INFO'},
                            f"Imported {self._imported} animations for {self._asset_name}.")
                return {'FINISHED'}

            anim_file = self._anim_files[self._index]
            anim_name = os.path.splitext(os.path.basename(anim_file))[0]

            if self._area:
                self._area.header_text_set(
                    f"{self._asset_name} — Importing animation "
                    f"{self._index + 1}/{self._total}: {anim_name}")

            action = animations.import_animation(anim_file, self._armature)
            if action:
                self._imported += 1

            self._index += 1

        return {'RUNNING_MODAL'}

    def _cleanup(self, context):
        context.window_manager.event_timer_remove(self._timer)
        if self._area:
            self._area.header_text_set(None)

# -----------------------------------------------------------------------------
#                                                                          Menu

class MessageOperator(bpy.types.Operator):
    """ Display message in log from application """
    bl_idname = "wm.display_message"
    bl_label = "Message"
    
    message: bpy.props.StringProperty(name="message", default="")
    severity: bpy.props.StringProperty(name="severity", default="INFO")

    def execute(self, context):
        self.report({self.severity}, self.message)
        return {'FINISHED'}

def menu_func_mech_import(self, context):
    self.layout.operator(MechImporter.bl_idname, text="Import Mech")

def menu_func_asset_import(self, context):
    self.layout.operator(AssetImporter.bl_idname, text="Import Cryengine Asset")

def menu_func_prefab_import(self, context):
    self.layout.operator(PrefabImporter.bl_idname, text="Import Cryengine Prefab")

classes = (
     AssetImporter,
     MechImporter,
     PrefabImporter,
     AnimationImportModal,
     MessageOperator
 )

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_asset_import)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_mech_import)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_prefab_import)

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_asset_import)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_mech_import)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_prefab_import)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()

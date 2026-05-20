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

# Cryengine Importer 4.0 (Blender Python module)
# https://www.heffaypresents.com/GitHub/Cryengine-Importer

import os, os.path
import bpy
import bpy.types
import bpy.utils
import mathutils

from . import animations, cockpit, collections, constants, bones, widgets, loadouts, materials, prefabs, utilities
from .import_report import ImportReport
from .CryXmlB.CryXmlReader import CryXmlSerializer

object_dictionary = {}

def strip_slash(line_split):
    if line_split[-1][-1] == 92:  # '\' char
        if len(line_split[-1]) == 1:
            line_split.pop()  # remove the \ item
        else:
            line_split[-1] = line_split[-1][:-1]  # remove the \ from the end last number
        return True
    return False

def get_base_dir(filepath):
    dirpath = filepath
    if os.path.isfile(filepath):
        dirpath = os.path.dirname(filepath)
    if os.path.basename(dirpath).lower() == 'objects' or os.path.basename(dirpath).lower() == 'prefabs':
        return os.path.abspath(os.path.join(dirpath, os.pardir))
    else:
        return get_base_dir(os.path.abspath(os.path.join(dirpath, os.pardir)))

def get_body_dir(filepath):
    return os.path.join(os.path.dirname(filepath), 'body')

def get_mech_name(filepath):
    return os.path.splitext(os.path.basename(filepath))[0]

def create_collections():
    # Generate group for each object to make linking into scenes easier.
    for obj in bpy.context.selectable_objects:
        if (obj.name != 'Camera' and obj.name != 'Light' and obj.name != 'Cube'):
            print ('   Creating collection for ' + obj.name)
            bpy.data.collections.new(obj.name)
            collections.move_object_to_collection(obj, obj.name)

def create_IKs(mech):
    armature = bones.find_armature_in_objects(bpy.data.objects)
    amt = armature.data
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')

    # --- EDIT MODE: Create control bones ---

    # Torso: Hip_Root from flipped Pelvis copy
    hip_root_bone = bones.copy_bone(armature, "Bip01_Pelvis", "Hip_Root")
    amt.edit_bones[hip_root_bone].use_connect = False
    bones.flip_bone(armature, hip_root_bone)
    amt.edit_bones['Bip01_Pelvis'].parent = amt.edit_bones[hip_root_bone]
    amt.edit_bones['Bip01_Pitch'].use_inherit_rotation = True

    # Root bone: sit on floor, non-deforming
    root_bone = amt.edit_bones['Bip01']
    root_bone.tail.y = root_bone.tail.z
    root_bone.tail.z = 0.0
    root_bone.use_deform = False
    root_bone.use_connect = False

    # Chickenwalker detection: calf points backward if head.y < tail.y
    knee_offset = 4
    if amt.edit_bones['Bip01_R_Calf'].head.y < amt.edit_bones['Bip01_R_Calf'].tail.y:
        knee_offset = -4
    print(f"Knee offset: {knee_offset} ({'chickenwalker' if knee_offset < 0 else 'regular'})")

    # --- Leg IK bones ---
    for side in ['R', 'L']:
        foot_name = f"Bip01_{side}_Foot"
        calf_name = f"Bip01_{side}_Calf"

        # Foot IK target (copy of foot, parented to root)
        foot_ik = bones.copy_bone_simple(armature, foot_name, f"Foot_IK.{side}")
        amt.edit_bones[foot_ik].use_connect = False
        amt.edit_bones[foot_ik].use_deform = False
        amt.edit_bones[foot_ik].parent = amt.edit_bones["Bip01"]

        # Knee pole target (in front of knee for regular, behind for chickenwalker)
        knee_ik = bones.new_bone(armature, f"Knee_IK.{side}")
        calf_head = amt.edit_bones[calf_name].head
        amt.edit_bones[knee_ik].head = calf_head + mathutils.Vector((0, knee_offset, 0))
        amt.edit_bones[knee_ik].tail = amt.edit_bones[knee_ik].head + mathutils.Vector((0, knee_offset / 4, 0))
        amt.edit_bones[knee_ik].use_deform = False
        amt.edit_bones[knee_ik].parent = amt.edit_bones["Bip01"]

    # --- Arm IK bones ---
    if mech in constants.shoulder_only_mechs:
        print(f"Shoulder only mech: {mech}")
        for side in ['R', 'L']:
            clavicle_name = f"Bip01_{side}_Clavicle"
            shoulder = bones.copy_bone_simple(armature, clavicle_name, f"Shoulder.{side}")
            amt.edit_bones[shoulder].head = amt.edit_bones[clavicle_name].tail
            amt.edit_bones[shoulder].tail = amt.edit_bones[shoulder].head + mathutils.Vector((0, 1, 0))
            amt.edit_bones[shoulder].use_deform = False
            amt.edit_bones[shoulder].use_connect = False
            amt.edit_bones[shoulder].use_inherit_rotation = False
            amt.edit_bones[shoulder].parent = amt.edit_bones["Bip01_Pitch"]
        copy_bone_right = None
        copy_bone_left = None
    else:
        print(f"Armed mech: {mech}")
        copy_bone_right = bones.get_last_bone_from(armature, "Bip01_R_Forearm")
        copy_bone_left = bones.get_last_bone_from(armature, "Bip01_L_Forearm")

        for side, copy_bone in [('R', copy_bone_right), ('L', copy_bone_left)]:
            forearm_name = f"Bip01_{side}_Forearm"

            # Hand IK target — placed at the hand bone's tail so the IK
            # solver doesn't need to move the chain to reach the target.
            hand_ik = bones.copy_bone_simple(armature, copy_bone, f"Hand_IK.{side}")
            amt.edit_bones[hand_ik].head = amt.edit_bones[copy_bone].tail
            amt.edit_bones[hand_ik].tail = amt.edit_bones[hand_ik].head + mathutils.Vector((0, 1, 0))
            amt.edit_bones[hand_ik].use_deform = False
            amt.edit_bones[hand_ik].use_connect = False
            amt.edit_bones[hand_ik].use_inherit_rotation = False
            amt.edit_bones[hand_ik].parent = amt.edit_bones["Bip01_Pitch"]

            # Elbow pole target (behind the elbow)
            elbow_ik = bones.new_bone(armature, f"Elbow_IK.{side}")
            amt.edit_bones[elbow_ik].head = amt.edit_bones[forearm_name].head + mathutils.Vector((0, -4, 0))
            amt.edit_bones[elbow_ik].tail = amt.edit_bones[elbow_ik].head + mathutils.Vector((0, -1, 0))
            amt.edit_bones[elbow_ik].use_deform = False
            amt.edit_bones[elbow_ik].use_connect = False
            amt.edit_bones[elbow_ik].use_inherit_rotation = False
            amt.edit_bones[elbow_ik].parent = amt.edit_bones["Bip01_Pitch"]

    # Set custom shapes (switches to object mode internally)
    set_custom_shapes(armature, mech)

    # --- POSE MODE: Add constraints ---
    bpy.ops.object.mode_set(mode='POSE')
    bpose = armature.pose

    # Feet: copy rotation from Foot_IK, disable inherit rotation
    for side in ['R', 'L']:
        amt.bones[f'Bip01_{side}_Foot'].use_inherit_rotation = False
        crc_foot = bpose.bones[f"Bip01_{side}_Foot"].constraints.new('COPY_ROTATION')
        crc_foot.target = armature
        crc_foot.subtarget = f"Foot_IK.{side}"
        crc_foot.target_space = 'LOCAL_WITH_PARENT'
        crc_foot.owner_space = 'LOCAL_WITH_PARENT'
        crc_foot.use_offset = True

    # Legs: IK on calf with pole target on knee
    for side in ['R', 'L']:
        ik = bpose.bones[f"Bip01_{side}_Calf"].constraints.new('IK')
        ik.target = armature
        ik.subtarget = f'Foot_IK.{side}'
        ik.pole_target = armature
        ik.pole_subtarget = f'Knee_IK.{side}'
        ik.pole_angle = -1.5708  # -π/2
        ik.chain_count = 2

    # Arms
    if mech not in constants.shoulder_only_mechs:
        for side, copy_bone, upper_arm in [
            ('R', copy_bone_right, 'Bip01_R_UpperArm'),
            ('L', copy_bone_left, 'Bip01_L_UpperArm'),
        ]:
            # Hand IK: Child Of pitch (influence 0 for optional toggle)
            coc = bpose.bones[f"Hand_IK.{side}"].constraints.new('CHILD_OF')
            coc.target = armature
            coc.subtarget = "Bip01_Pitch"
            coc.influence = 0.0

            # IK on last arm bone with elbow pole target
            ik = bpose.bones[copy_bone].constraints.new('IK')
            ik.target = armature
            ik.subtarget = f'Hand_IK.{side}'
            ik.pole_target = armature
            ik.pole_subtarget = f'Elbow_IK.{side}'
            ik.pole_angle = -1.5708  # -π/2
            ik.chain_count = get_chain_count(bpose.bones[upper_arm])
    else:
        for side in ['R', 'L']:
            # Shoulder: Child Of pitch (influence 0)
            coc = bpose.bones[f"Shoulder.{side}"].constraints.new('CHILD_OF')
            coc.target = armature
            coc.subtarget = "Bip01_Pitch"
            coc.influence = 0.0

            # UpperArm copies shoulder rotation
            crc_arm = bpose.bones[f"Bip01_{side}_UpperArm"].constraints.new('COPY_ROTATION')
            crc_arm.target = armature
            crc_arm.subtarget = f"Shoulder.{side}"
            crc_arm.target_space = 'LOCAL_WITH_PARENT'
            crc_arm.owner_space = 'LOCAL_WITH_PARENT'
            crc_arm.use_offset = True

    for bone in ['Foot_IK.R', 'Foot_IK.L', 'Bip01_Pelvis', 'Bip01_Pitch']:
        bpose.bones[bone].use_custom_shape_bone_size = False

    bones.set_bone_collections(armature)

def get_chain_count(bone):
    count = 1
    while len(bone.children) != 0:
        found_last_bone = True
        for child in bone.children:
            if len(child.children) != 0:
                bone = child
                found_last_bone = False
        if found_last_bone:
            count += 1
            print("*** Chain count: " + str(count))
            return count
        count += 1

def set_custom_shapes(armature, mech):
    # Set custom shapes
    print("Setting up widgets")
    bpy.ops.object.mode_set(mode='OBJECT')
    widgets.create_root_widget(armature, "Root", "Bip01")
    widgets.create_cube_widget(armature, "Foot_IK.R", 1.0)
    widgets.create_cube_widget(armature, "Foot_IK.L", 1.0)
    widgets.create_sphere_widget(armature, "Knee_IK.R")
    widgets.create_sphere_widget(armature, "Knee_IK.L")
    widgets.create_circle_widget(armature, "Bip01_Pitch", 2.0, 1.0, True)
    widgets.create_circle_widget(armature, "Bip01_Pelvis", 2.0, 0.0, True)
    widgets.create_cube_widget(armature, "Hip_Root", 3.0)
    if mech not in constants.shoulder_only_mechs:
        widgets.create_cube_widget(armature, "Hand_IK.R", 1.25)
        widgets.create_cube_widget(armature, "Hand_IK.L", 1.25)
        widgets.create_sphere_widget(armature, "Elbow_IK.R")
        widgets.create_sphere_widget(armature, "Elbow_IK.L")
        armature.pose.bones['Hand_IK.R'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Hand_IK.R"]
        armature.pose.bones['Hand_IK.L'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Hand_IK.L"]
        armature.pose.bones['Elbow_IK.R'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Elbow_IK.R"]
        armature.pose.bones['Elbow_IK.L'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Elbow_IK.L"]
    else:
        widgets.create_cube_widget(armature, "Shoulder.L", 1.0)
        widgets.create_cube_widget(armature, "Shoulder.R", 1.0)
        armature.pose.bones['Shoulder.L'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Shoulder.L"]
        armature.pose.bones['Shoulder.R'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Shoulder.R"]
    bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Root"].rotation_euler = (0,0,0)
    armature.pose.bones['Bip01'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Root"]
    armature.pose.bones["Foot_IK.R"].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Foot_IK.R"]
    armature.pose.bones["Foot_IK.L"].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Foot_IK.L"]
    armature.pose.bones['Knee_IK.R'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Knee_IK.R"]
    armature.pose.bones['Knee_IK.L'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Knee_IK.L"]
    armature.pose.bones['Bip01_Pitch'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Bip01_Pitch"]
    armature.pose.bones['Bip01_Pelvis'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Bip01_Pelvis"]
    armature.pose.bones['Hip_Root'].custom_shape = bpy.data.objects[constants.WIDGET_PREFIX + armature.name + "_" + "Hip_Root"]
    print("End setting up widgets")

def import_geometry(usd_file, basedir):
    try:
        objects_before = set(bpy.data.objects)
        bpy.ops.wm.usd_import(filepath=usd_file, import_skeletons=True, import_meshes=True,
                               import_materials=True, import_usd_preview=True)
        objects_after = set(bpy.data.objects)
        new_objects = list(objects_after - objects_before)
        return utilities.cleanup_usd_import(new_objects)
    except:
        print(f"Error importing USD file: {usd_file}, basedir: {basedir}")
    
def import_mech_geometry(cdf_file, basedir, bodydir, mechname, report=None):
    armature = bones.find_armature_in_objects(bpy.data.objects)
    print("Importing mech geometry...")
    cry_xml = CryXmlSerializer()
    geometry = cry_xml.read_file(cdf_file)
    for geo in geometry.iter("Attachment"):
        if not geo.attrib["AName"] == "cockpit":
            print("Importing " + geo.attrib["AName"])
            # Get all the attribs
            aname    = geo.attrib["AName"]
            rotation = utilities.convert_to_quaternion(geo.attrib["Rotation"])
            location = utilities.convert_to_vector(geo.attrib["Position"])
            bonename = process_bonename(geo, aname)
            print("*** *** Bonename: " + bonename)
            binding  = os.path.join(basedir, os.path.splitext(geo.attrib["Binding"])[0] + ".usda")
            flags    = geo.attrib["Flags"]
            # Materials depend on the part type.  For most, <mech>_body.  Weapons is <mech>_variant.  Window/cockpit is 
            # <mech>_window.
            materialname = mechname + "_body"
            if any(weapon in aname for weapon in constants.weapons):
                materialname = mechname + "_variant"
            if "_damaged" in aname or "_prop" in aname:
                materialname = mechname + "_body"
            if "head_cockpit" in aname:
                if mechname == "atlas":
                    materialname = mechname + "_eyes"
                else:
                    materialname = mechname + "_window"
            # We now have all the geometry parts that need to be imported, their loc/rot, and material.  Import.
            print('Material: ' + materialname)
            try:
                objects_before = set(bpy.data.objects)
                bpy.ops.wm.usd_import(filepath=binding, import_skeletons=True, import_meshes=True,
                                       import_materials=True, import_usd_preview=True)
                objects_after = set(bpy.data.objects)
                obj_objects = utilities.cleanup_usd_import(list(objects_after - objects_before))
            except Exception as e:
                # Unable to open the file.  Probably not found (like Urbie lights, under purchasable).
                if report is not None:
                    report.add_skipped(aname, f"USD import failed: {e}")
                continue
            if not obj_objects:
                if report is not None:
                    report.add_skipped(aname, "USD import returned no objects")
                continue
            if report is not None:
                report.add_imported(aname)
            # Delete component's imported skeleton (redundant — we use the main armature)
            component_armatures = [obj for obj in obj_objects if obj.type == 'ARMATURE']
            for obj in component_armatures:
                bpy.data.objects.remove(obj, do_unlink=True)
            mesh_objects = [obj for obj in obj_objects if obj.type == 'MESH']
            i = 0
            for obj in mesh_objects:
                collections.move_object_to_collection(obj, constants.MECH_COLLECTION)
                armature.select_set(True)
                bpy.context.view_layer.objects.active = armature
                bpy.context.view_layer.objects.active = obj
                # If this is a parent node, rotate/translate it. Otherwise skip it.
                if i == 0:
                    matrix = utilities.get_transform_matrix(rotation, location)
                    # Clear residual transform from deleted USD hierarchy
                    obj.matrix_world = mathutils.Matrix.Identity(4)
                    obj.rotation_mode = 'QUATERNION'
                    obj.parent = armature
                    obj.parent_bone = bonename
                    obj.parent_type = 'BONE'
                    obj.matrix_world = matrix
                    i = i + 1
                # Vertex groups
                vg = obj.vertex_groups.new(name=bonename)
                nverts = len(obj.data.vertices)
                for i in range(nverts):
                    vg.add([i], 1.0, 'REPLACE')
                if len(bpy.context.object.material_slots) == 0:
                    bpy.context.object.data.materials.append(bpy.data.materials[materialname])  # If there is no material, add a dummy mat.
                if "_prop" in obj.name:
                    materialname = mechname + "_body"
                bpy.context.object.data.materials[0] = bpy.data.materials[materialname]
                obj.select_set(False)

def process_bonename(geo, aname):
    if aname in constants.bad_bonename_map:
        return constants.bad_bonename_map[aname]
    else:
        return geo.attrib["BoneName"].replace(' ','_')

def link_geometry(object_name, cgf_name, library_file, collection):
    # Link the object from the library file and translate/rotate.
    if os.path.isfile(library_file):
        with bpy.data.libraries.load(library_file, link=True) as (data_from, data_to):
            data_to.objects = [o for o in data_from.objects if o == cgf_name]
        for obj in data_to.objects:
            if obj is not None:
                print("Obj.name: " + obj.name + ", object_name: " + object_name)
                collections.link_object_to_collection(obj, collection.name)
                proxy = bpy.data.objects.new(object_name + "_proxy", None)
                obj.users_collection[0].objects.link(proxy)
                proxy.empty_display_type = 'SPHERE'
                proxy.location = obj.location
                obj.parent = proxy
                print("Imported object: " + obj.name)
                return proxy
            else:
                print("Couldn't find object " + obj.name)
                return None
    else:
        print("Unable to find library file " + library_file)
        return None

def get_root(object):
    if object.parent != None:
        return get_root(object.parent)
    else:
        return object

def get_all_child_objects(object, include_root=True):
    result = []
    def recurse(obj):
        result.append(obj)
        if len(obj.children) != 0:
            for o in obj.children:
                recurse(o)
    if include_root:
        result.append(object)
    for child in object.children:
        recurse(child)
    return result

def save_file(file):
    # Save the Blender scene as a .blend named after the imported asset.
    # `file` is the path the user chose in the file selector — the .cdf for
    # the mech importer, a directory for the asset importer. The .cdf is
    # never written; only the .blend file is created.
    if not os.path.isfile(file):  # Directory
        basename = os.path.basename(os.path.dirname(file))
        blend_path = os.path.join(file, basename + ".blend")
    else:
        stem = file[:-4] if file.lower().endswith(".cdf") else file
        basename = os.path.basename(stem)
        blend_path = os.path.join(os.path.dirname(stem), basename + ".blend")
    print("Saving " + blend_path)
    if not bpy.path.abspath("//"):  # not saved yet
        bpy.ops.wm.save_as_mainfile(filepath=blend_path, check_existing=True)
    
def generate_preview(file):
    if os.path.isfile(file):
        path = bpy.path.abspath("//")
        filename = bpy.path.basename(bpy.context.blend_data.filepath)
        bpy.ops.wm.previews_batch_generate(directory = path, files=[{ "name": filename }], use_groups=True,use_scenes=False,use_objects=False)

def set_viewport_shading():
    # Set material mode. # iterate through areas in current screen
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces: 
                if space.type == 'VIEW_3D': 
                    space.shading.type = 'MATERIAL'

def add_objects_to_collections():
    # First, get all the objects that need to be sorted into collections
    armature = bones.find_armature_in_objects(bpy.data.objects)
    
    # Clear armature from any existing collections (in case it's already in any)
    for collection in armature.users_collection:
        collection.objects.unlink(armature)
    
    # Get the Mech collection and add armature as the first object
    mech_collection = bpy.data.collections[constants.MECH_COLLECTION]
    mech_collection.objects.link(armature)
    
    # Now handle the rest of the objects
    empties = [obj for obj in bpy.data.objects 
               if obj.name.startswith('fire') 
               or 'physics_proxy' in obj.name 
               or obj.name.endswith('_fx') 
               or obj.name.endswith('_case')
               or obj.name.startswith('animation')
               or obj.name.startswith('.animation')]
    for empty in empties:
        collections.move_object_to_collection(empty, constants.EMPTIES_COLLECTION)
    # Set weapons and special geometry to Weapons Collection.  Per-object
    # eyeballs stay open; collection-level hides drive what's visible
    # (Weapons + Variants/<VARIANT> are hidden by default).
    for weapon in bpy.data.objects:
        if any(x in weapon.name for x in constants.weapons):
            collections.move_object_to_collection(weapon, constants.WEAPONS_COLLECTION)
    move_damaged_parts_to_collection()

def apply_loadouts(mech_dir, basedir, report=None):
    """For each <variant>.mdf in mech_dir, resolve the variant's stock loadout
    and link the matching weapon objects into its variant collection.
    Variant collections are pre-created by collections.set_up_collections()
    using uppercased filenames (e.g. ADR-A)."""
    for filename in os.listdir(mech_dir):
        if not filename.lower().endswith(".mdf"):
            continue
        variant_name = os.path.splitext(filename)[0]
        variant_collection_name = variant_name.upper()
        if variant_collection_name not in bpy.data.collections:
            if report is not None:
                report.add_warning(f"Variant collection missing: {variant_collection_name}")
            continue

        try:
            resolved = loadouts.resolve_variant(variant_name, basedir, mech_dir)
        except Exception as e:
            if report is not None:
                report.add_skipped(variant_name, f"loadout resolution failed: {e}")
            continue

        if resolved is None:
            if report is not None:
                report.add_skipped(variant_name, "loadout files not found")
            continue

        # Dedupe ANames across components so we link each object once per variant.
        anames = {a for v in resolved.values() for a in v["attachments"]}
        unresolved = [(c, w) for c, v in resolved.items() for w in v["unresolved"]]
        linked = 0
        missing = []
        for aname in anames:
            obj = bpy.data.objects.get(aname)
            if obj is None:
                missing.append(aname)
                continue
            collections.link_object_to_collection(obj, variant_collection_name)
            linked += 1

        if report is not None:
            for comp, (wid, wname) in unresolved:
                report.add_warning(
                    f"{variant_name}: {comp} weapon {wid} ({wname}) has no matching hardpoint")
            for aname in missing:
                report.add_warning(f"{variant_name}: imported object not found for {aname}")
            report.add_imported(f"{variant_collection_name} loadout ({linked} weapons)")


def move_damaged_parts_to_collection():
    for obj in bpy.data.objects:
        if obj.name.endswith('_damaged') or obj.name.endswith('_damged'):
            collections.move_object_to_collection(obj, constants.DAMAGED_PARTS_COLLECTION)

def show_all_prefab_folders(prefab_xml):
    print("NOTE:  Asset importer needs to create .blend files for the following directories:")
    all_dirs = []
    for prefab in prefab_xml.iter("Object"):
        if prefab.attrib["Type"] == "Brush":
            file = "/".join(prefab.attrib["Prefab"].split("/")[0:-1])
            all_dirs.append(file)
        elif prefab.attrib["Type"] == "Entity":
            properties = prefab[0]
            file = "/".join(properties.attrib["objModel"].split("/")[0:-1])
            all_dirs.append(file)
        elif prefab.attrib["Type"] == "GeomEntity":
            file = "/".join(prefab.attrib["Geometry"].split("/")[0:-1])
            all_dirs.append(file)
    for dir in (set(all_dirs)):
        print(dir)

def import_light(object):
    # For a Prefab light, create a new light object, position/rotate it and return the object.
    # object is the xml object with all the needed attributes.
    scene = bpy.context.scene
    light_data = bpy.data.lights.new(object.attrib["Name"], type='POINT')
    obj = bpy.data.objects.new(name = object.attrib["Name"], object_data = light_data)
    objname = object.attrib["Name"]
    scene.collection.objects.link(obj)
    properties = object.find("Properties")
    # Set shadows
    options = properties.find("Options")
    color = properties.find("Color")
    if not options == None:
        if options.attrib["bCastShadow"] == "0":
            bpy.data.lights[objname].cycles.cast_shadow = False
        else:
            bpy.data.lights[objname].cycles.cast_shadow = True
    if not color == None:
        bpy.data.lights[objname].color = utilities.convert_to_rgb(color.attrib["clrDiffuse"])
    location = utilities.convert_to_vector(object.attrib["Pos"])
    rotation = utilities.convert_to_quaternion(object.attrib["Rotate"])
    matrix = utilities.get_transform_matrix(rotation, location)
    # obj = bpy.data.objects["objectname"]
    obj.rotation_mode = 'QUATERNION'
    obj.matrix_world = matrix
    return obj

def import_asset_geometry(filepath):
    """Import geometry only (no animations)."""
    print("Import Asset.  File: " + filepath)
    set_viewport_shading()
    import_geometry(filepath, get_base_dir(filepath))


def discover_asset_animations(filepath):
    """Discover animation files for an asset using CDF or chrparams.
    Returns (anim_files, armature) or ([], None) if none found.
    """
    directory = os.path.dirname(filepath)
    game_root = get_base_dir(filepath)
    armature = bones.find_armature_in_objects(bpy.data.objects)
    model_name = os.path.splitext(os.path.basename(filepath))[0]

    if not armature:
        return ([], None)

    anim_files = []

    # Try CDF first (e.g. MWO mechs)
    cdf_path = os.path.join(directory, model_name + ".cdf")
    if os.path.isfile(cdf_path):
        skeleton_name = animations.get_skeleton_name_from_cdf(cdf_path)
        if skeleton_name:
            anim_files = animations.discover_animation_files(directory, skeleton_name)

    # Fall back to chrparams (e.g. Pandemic Express, KCD2)
    if not anim_files:
        chrparams_path = os.path.join(directory, model_name + ".chrparams")
        if os.path.isfile(chrparams_path):
            skeleton_name = animations.get_skeleton_name_from_chrparams(chrparams_path)
            anim_files = animations.discover_animations_from_chrparams(
                chrparams_path, game_root, skeleton_name)

    return (anim_files, armature)


def import_asset(filepath, import_animations=True):
    """Import an asset with optional animations. Kept for backward compatibility."""
    import_asset_geometry(filepath)

    if import_animations:
        anim_files, armature = discover_asset_animations(filepath)
        if anim_files:
            animations.import_all_animations_from_files(anim_files, armature)

    return {'FINISHED'}

def import_mech(context, *, use_dds=True, use_tif=False, auto_save_file=True,
                add_control_bones=True, import_loadouts=True, path):
    print("Import Mech")
    print(path)
    report = ImportReport()
    cdf_file = path      # The input file
    # Split up path into the variables we want.
    constants.basedir = get_base_dir(path)
    bodydir = get_body_dir(path)
    mechdir = os.path.dirname(path)
    mech = get_mech_name(path)
    matfile = os.path.join(bodydir, mech + "_body.mtl")
    cockpit_matfile = os.path.join(mechdir, "cockpit_standard", mech +
                                   "_a_cockpit_standard.mtl")
    # Set material mode. # iterate through areas in current screen
    set_viewport_shading()
    collections.set_up_collections(path)
    # Try to import the armature.  If we can't find it, then return error.
    bones.import_armature(os.path.join(bodydir, mech + ".usda"), mech)

    # Create the materials.
    constants.materials = materials.create_materials(matfile, constants.basedir, use_dds, use_tif)
    constants.cockpit_materials = materials.create_materials(cockpit_matfile, constants.basedir, use_dds, use_tif)
    # Import the geometry and assign materials.
    import_mech_geometry(cdf_file, constants.basedir, bodydir, mech, report=report)

    # Import the interior cockpit (separate sub-CDF) into its own hidden collection.
    armature_obj = bones.find_armature_in_objects(bpy.data.objects)
    if armature_obj is not None:
        cdf_xml = CryXmlSerializer().read_file(cdf_file)
        cockpit_attachment = cockpit.find_cockpit_attachment(cdf_xml)
        if cockpit_attachment is not None:
            cockpit.import_cockpit(cockpit_attachment, constants.basedir, mech, armature_obj, report=report)

    # Set the layers for existing objects
    add_objects_to_collections()

    # Link variant-specific weapons into Variants/<VARIANT> collections.
    if import_loadouts:
        apply_loadouts(mechdir, constants.basedir, report=report)

    # Advanced Rigging stuff.  Make bone shapes, IKs, etc.
    if add_control_bones == True:
        create_IKs(mech)

    # Ensure there's an active object before switching modes — post-import
    # steps (cockpit/loadout link/unlink) can leave context.active_object as
    # None, which makes bpy.ops.object.mode_set fail its poll.
    if armature_obj is not None:
        bpy.context.view_layer.objects.active = armature_obj
    if bpy.context.view_layer.objects.active is not None:
        bpy.ops.object.mode_set(mode='OBJECT')

    materials.remove_unlinked_materials()

    if auto_save_file == True:
        save_file(path)
    return report

def import_prefab(context, *, use_dds=True, use_tif=False, auto_save_file=True,
                  auto_generate_preview=False, path):
    """Import a Cryengine PrefabsLibrary XML. Texture flags are kept for
    operator-preset compatibility but unused — USD materials drive textures."""
    set_viewport_shading()
    basedir = get_base_dir(path)
    print("Basedir: " + basedir)

    report = ImportReport()
    library_name = prefabs.import_prefab_library(path, basedir, report)

    if auto_save_file and library_name is not None:
        save_file(path)
    return report

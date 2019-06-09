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

import array
import glob
import math
import os, os.path
import time
import types
import xml.etree as etree
import xml.etree.ElementTree as ET
import bpy
import bmesh
import bpy.types
import bpy.utils
import mathutils
from math import radians

from . import constants, cc_collections, bones, widgets, materials, utilities

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

def get_mech(filepath):
    return os.path.splitext(os.path.basename(filepath))[0]

def create_object_groups():
    # Generate group for each object to make linking into scenes easier.
    for obj in bpy.context.selectable_objects:
        if (obj.name != 'Camera' and obj.name != 'Light' and obj.name != 'Cube'):
            print ('   Creating collection for ' + obj.name)
            bpy.data.collections.new(obj.name)
            bpy.data.collections[obj.name].objects.link(obj)

# This subroutine needs to be broken up in smaller parts
def create_IKs():
    print("Creating IKs.  v1.0.4")
    bpy.ops.object.mode_set(mode='EDIT')
    armature = bpy.data.objects['Armature']
    amt = armature.data
    bpy.context.view_layer.objects.active = armature
    # EDIT MODE CHANGES
    # Set up hip and torso bones.  Connect Pelvis to Pitch
    # armature.data.edit_bones['Bip01_Pelvis'].tail = armature.data.edit_bones['Bip01_Pitch'].head      # Causes Pelvis bone to disappear sometimes
    hip_root_bone = bones.copy_bone(armature, "Bip01_Pelvis", "Hip_Root")
    armature.data.edit_bones['Hip_Root'].use_connect = False
    bones.flip_bone(armature, "Hip_Root")
    # Parent Pelvis to hip_root
    armature.data.edit_bones['Bip01_Pelvis'].parent = armature.data.edit_bones['Hip_Root']
    armature.data.edit_bones['Bip01_Pitch'].use_inherit_rotation = False
    # Make root bone sit on floor, turn off deform.
    rootbone = armature.data.edit_bones['Bip01']
    rootbone.tail.y = rootbone.tail.z
    rootbone.tail.z = 0.0
    rootbone.use_deform = False
    rootbone.use_connect = False
    
    # Determine knee IK offset.  Behind for chickenwalkers, forward for regular.  Edit mode required.
    offset = 4
    if amt.edit_bones['Bip01_R_Calf'].head.y < amt.edit_bones['Bip01_R_Calf'].tail.y:
        offset = -4

    print("Offset is " + str(offset))
    ### Create IK bones
    print("Creating IK Bones")
    # Right foot
    rightFootIKName = bones.copy_bone(armature, "Bip01_R_Foot", "Foot_IK.R")
    amt.edit_bones[rightFootIKName].use_connect = False
    amt.edit_bones[rightFootIKName].use_deform = False
    amt.edit_bones[rightFootIKName].parent = armature.data.edit_bones["Bip01"]

    # Right knee
    rightKneeIKName = bones.new_bone(armature, "Knee_IK.R")
    amt.edit_bones[rightKneeIKName].head = amt.edit_bones["Bip01_R_Calf"].head + mathutils.Vector((0,offset,0))
    amt.edit_bones[rightKneeIKName].tail = amt.edit_bones[rightKneeIKName].head + mathutils.Vector((0, offset/4, 0))
    amt.edit_bones[rightKneeIKName].use_deform = False
    amt.edit_bones[rightKneeIKName].parent = armature.data.edit_bones["Bip01"]

    # Left foot
    leftFootIKName = bones.copy_bone(armature, "Bip01_L_Foot", "Foot_IK.L")
    amt.edit_bones[leftFootIKName].use_connect = False
    amt.edit_bones[leftFootIKName].use_deform = False
    amt.edit_bones[leftFootIKName].parent = armature.data.edit_bones["Bip01"]
    
    # Left knee
    leftKneeIKName = bones.new_bone(armature, "Knee_IK.L")
    amt.edit_bones[leftKneeIKName].head = amt.edit_bones['Bip01_L_Calf'].head + mathutils.Vector((0,offset,0))
    amt.edit_bones[leftKneeIKName].tail = amt.edit_bones[leftKneeIKName].head + mathutils.Vector((0, offset/4, 0))
    amt.edit_bones[leftKneeIKName].use_deform = False
    amt.edit_bones[leftKneeIKName].parent = amt.edit_bones["Bip01"]
    
    # Right Hand
    rightHandIKName = bones.copy_bone(armature, "Bip01_R_Hand", "Hand_IK.R")
    amt.edit_bones[rightHandIKName].head = amt.edit_bones["Bip01_R_Hand"].head
    amt.edit_bones[rightHandIKName].tail = amt.edit_bones[rightHandIKName].head + mathutils.Vector((0, 1, 0))
    amt.edit_bones[rightHandIKName].use_deform = False
    amt.edit_bones[rightHandIKName].parent = armature.data.edit_bones["Bip01_Pitch"]
    amt.edit_bones["Bip01_R_Hand"].use_inherit_rotation = False

    # Right Elbow
    rightElbowIKName = bones.new_bone(armature, "Elbow_IK.R")
    amt.edit_bones[rightElbowIKName].head = amt.edit_bones["Bip01_R_Forearm"].head + mathutils.Vector((0, -4, 0))
    amt.edit_bones[rightElbowIKName].tail = amt.edit_bones[rightElbowIKName].head + mathutils.Vector((0, -1, 0))
    amt.edit_bones[rightElbowIKName].use_deform = False
    amt.edit_bones[rightElbowIKName].parent = armature.data.edit_bones["Bip01_Pitch"]
    amt.edit_bones[rightElbowIKName].use_inherit_rotation = False

    # Left Hand
    leftHandIKName = bones.copy_bone(armature, "Bip01_L_Hand", "Hand_IK.L")
    amt.edit_bones[leftHandIKName].head = armature.data.edit_bones['Bip01_L_Hand'] .head
    amt.edit_bones[leftHandIKName].tail = amt.edit_bones[leftHandIKName].head + mathutils.Vector((0, 1, 0))
    amt.edit_bones[leftHandIKName].use_deform = False
    amt.edit_bones[leftHandIKName].parent = armature.data.edit_bones["Bip01_Pitch"]
    amt.edit_bones["Bip01_L_Hand"].use_inherit_rotation = False

    # Left Elbow
    leftElbowIKName = bones.new_bone(armature, "Elbow_IK.L")
    amt.edit_bones[leftElbowIKName].head = amt.edit_bones["Bip01_L_Forearm"].head + mathutils.Vector((0, -4, 0))
    amt.edit_bones[leftElbowIKName].tail = amt.edit_bones[leftElbowIKName].head + mathutils.Vector((0, -1, 0))
    amt.edit_bones[leftElbowIKName].use_deform = False
    amt.edit_bones[leftElbowIKName].parent = armature.data.edit_bones["Bip01_Pitch"]
    amt.edit_bones[leftElbowIKName].use_inherit_rotation = False
    print("End creating IK Bones")
    
    # Set custom shapes
    print("Setting up widgets")
    bpy.ops.object.mode_set(mode='OBJECT')
    widgets.create_root_widget(armature, "Root", "Bip01")
    widgets.create_cube_widget(armature, "Hand_IK.R", 1.25)
    widgets.create_cube_widget(armature, "Hand_IK.L", 1.25)
    widgets.create_cube_widget(armature, "Foot_IK.R", 1.0)
    widgets.create_cube_widget(armature, "Foot_IK.L", 1.0)
    widgets.create_sphere_widget(armature, "Knee_IK.R")
    widgets.create_sphere_widget(armature, "Knee_IK.L")
    widgets.create_sphere_widget(armature, "Elbow_IK.R")
    widgets.create_sphere_widget(armature, "Elbow_IK.L")
    widgets.create_circle_widget(armature, "Bip01_Pitch", 2.0, 1.0, True)
    widgets.create_circle_widget(armature, "Bip01_Pelvis", 2.0, 0.0, True)
    widgets.create_cube_widget(armature, "Hip_Root", 3.0)
    bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Root"].rotation_euler = (0,0,0)
    armature.pose.bones['Bip01'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Root"]
    armature.pose.bones['Hand_IK.R'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Hand_IK.R"]
    armature.pose.bones['Hand_IK.L'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Hand_IK.L"]
    armature.pose.bones["Foot_IK.R"].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Foot_IK.R"]
    armature.pose.bones["Foot_IK.L"].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Foot_IK.L"]
    armature.pose.bones['Knee_IK.R'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Knee_IK.R"]
    armature.pose.bones['Knee_IK.L'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Knee_IK.L"]
    armature.pose.bones['Elbow_IK.R'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Elbow_IK.R"]
    armature.pose.bones['Elbow_IK.L'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Elbow_IK.L"]
    armature.pose.bones['Bip01_Pitch'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Bip01_Pitch"]
    armature.pose.bones['Bip01_Pelvis'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Bip01_Pelvis"]
    armature.pose.bones['Hip_Root'].custom_shape = bpy.data.objects[constants.WGT_PREFIX + armature.name + "_" + "Hip_Root"]
    print("End setting up widgets")

    # POSE MODE CHANGES
    # Set up IK Constraints
    bpy.ops.object.mode_set(mode='POSE')
    bpose = bpy.context.object.pose
    # Add copy rotation constraint to pitch
    crc = armature.pose.bones["Bip01_Pitch"].constraints.new('COPY_ROTATION')
    crc.target = armature
    crc.subtarget = "Bip01_Pelvis"
    crc.target_space = 'LOCAL'
    crc.owner_space = 'LOCAL'
    crc.use_offset = True
    # Add copy rotation constraint to Feet
    crcFootL = armature.pose.bones["Bip01_L_Foot"].constraints.new('COPY_ROTATION')
    crcFootL.target = armature
    crcFootL.subtarget = "Foot_IK.L"
    crcFootL.target_space = 'LOCAL_WITH_PARENT'
    crcFootL.owner_space = 'LOCAL_WITH_PARENT'
    crcFootL.use_offset = True
    crcFootR = armature.pose.bones["Bip01_R_Foot"].constraints.new('COPY_ROTATION')
    crcFootR.target = armature
    crcFootR.subtarget = "Foot_IK.R"
    crcFootR.target_space = 'LOCAL_WITH_PARENT'
    crcFootR.owner_space = 'LOCAL_WITH_PARENT'
    crcFootR.use_offset = True
    # Add child of constraint to hand IKs
    coc = armature.pose.bones["Hand_IK.R"].constraints.new('CHILD_OF')
    coc.target = armature
    coc.subtarget = "Bip01_Pitch"
    coc = armature.pose.bones["Hand_IK.L"].constraints.new('CHILD_OF')
    coc.target = armature
    coc.subtarget = "Bip01_Pitch"
    armature.pose.bones["Hand_IK.R"].constraints["Child Of"].influence = 0.0
    armature.pose.bones["Hand_IK.L"].constraints["Child Of"].influence = 0.0
    pbone = bpy.context.active_object.pose.bones["Hand_IK.R"]
    context_copy = bpy.context.copy()
    context_copy["constraint"] = pbone.constraints["Child Of"]
    bpy.context.active_object.data.bones.active = pbone.bone
    bpy.ops.constraint.childof_set_inverse(context_copy, constraint="Child Of", owner='BONE')
    pbone = bpy.context.active_object.pose.bones["Hand_IK.L"]
    context_copy = bpy.context.copy()
    context_copy["constraint"] = pbone.constraints["Child Of"]
    bpy.context.active_object.data.bones.active = pbone.bone
    bpy.ops.constraint.childof_set_inverse(context_copy, constraint="Child Of", owner='BONE')
    amt.bones['Bip01_L_Foot'].use_inherit_rotation = False
    amt.bones['Bip01_R_Foot'].use_inherit_rotation = False
    bpose.bones['Bip01_R_Hand'].constraints.new(type='IK')
    bpose.bones['Bip01_R_Hand'].constraints['IK'].target = armature
    bpose.bones['Bip01_R_Hand'].constraints['IK'].subtarget = 'Hand_IK.R'
    if "Bip01_R_Elbow" in bpose.bones.keys():
        bpose.bones['Bip01_R_Hand'].constraints['IK'].chain_count = 5
    else:
        bpose.bones['Bip01_R_Hand'].constraints['IK'].chain_count = 3
    bpose.bones['Bip01_L_Hand'].constraints.new(type='IK')
    bpose.bones['Bip01_L_Hand'].constraints['IK'].target = armature
    bpose.bones['Bip01_L_Hand'].constraints['IK'].subtarget = 'Hand_IK.L'
    if "Bip01_L_Elbow" in bpose.bones.keys():
        bpose.bones['Bip01_L_Hand'].constraints['IK'].chain_count = 5
    else:
        bpose.bones['Bip01_L_Hand'].constraints['IK'].chain_count = 3
    bpose.bones['Bip01_R_UpperArm'].constraints.new(type='IK')
    bpose.bones['Bip01_R_UpperArm'].constraints['IK'].target = armature
    bpose.bones['Bip01_R_UpperArm'].constraints['IK'].subtarget = 'Elbow_IK.R'
    bpose.bones['Bip01_R_UpperArm'].constraints['IK'].chain_count = 1
    bpose.bones['Bip01_L_UpperArm'].constraints.new(type='IK')
    bpose.bones['Bip01_L_UpperArm'].constraints['IK'].target = armature
    bpose.bones['Bip01_L_UpperArm'].constraints['IK'].subtarget = 'Elbow_IK.L'
    bpose.bones['Bip01_L_UpperArm'].constraints['IK'].chain_count = 1
    bpose.bones['Bip01_R_Calf'].constraints.new(type='IK')
    bpose.bones['Bip01_R_Calf'].constraints['IK'].target = armature
    bpose.bones['Bip01_R_Calf'].constraints['IK'].subtarget = 'Foot_IK.R'
    bpose.bones['Bip01_R_Calf'].constraints['IK'].chain_count = 2
    bpose.bones['Bip01_L_Calf'].constraints.new(type='IK')
    bpose.bones['Bip01_L_Calf'].constraints['IK'].target = armature
    bpose.bones['Bip01_L_Calf'].constraints['IK'].subtarget = 'Foot_IK.L'
    bpose.bones['Bip01_L_Calf'].constraints['IK'].chain_count = 2
    bpose.bones['Bip01_R_Thigh'].constraints.new(type='IK')
    bpose.bones['Bip01_R_Thigh'].constraints['IK'].target = armature
    bpose.bones['Bip01_R_Thigh'].constraints['IK'].subtarget = 'Knee_IK.R'
    bpose.bones['Bip01_R_Thigh'].constraints['IK'].chain_count = 1
    bpose.bones['Bip01_L_Thigh'].constraints.new(type='IK')
    bpose.bones['Bip01_L_Thigh'].constraints['IK'].target = armature
    bpose.bones['Bip01_L_Thigh'].constraints['IK'].subtarget = 'Knee_IK.L'
    bpose.bones['Bip01_L_Thigh'].constraints['IK'].chain_count = 1
    
    # Move bones to proper layers
    bones.set_bone_layers(armature)

def import_geometry(daefile, basedir):
    try:
        bpy.ops.wm.collada_import(filepath=daefile,find_chains=True,auto_connect=True)
        return bpy.context.selected_objects[:]      # Return the objects added.
    except:
        # Unable to open the file.  Probably not found (like Urbie lights, under purchasables).
        #continue
        print("Error importing Collada file: " + daefile + ", basedir: " + basedir)
    
def import_mech_geometry(cdffile, basedir, bodydir, mechname):
    armature = bpy.data.objects['Armature']
    print("Importing mech geometry...")
    geometry = ET.parse(cdffile)
    for geo in geometry.iter("Attachment"):
        if not geo.attrib["AName"] == "cockpit":
            print("Importing " + geo.attrib["AName"])
            # Get all the attribs
            aname    = geo.attrib["AName"]
            rotation = utilities.convert_to_rotation(geo.attrib["Rotation"])
            location = utilities.convert_to_location(geo.attrib["Position"])
            bonename = geo.attrib["BoneName"].replace(' ','_')
            binding  = os.path.join(basedir, os.path.splitext(geo.attrib["Binding"])[0] + ".dae")
            flags    = geo.attrib["Flags"]
            # Materials depend on the part type.  For most, <mech>_body.  Weapons is <mech>_variant.  Window/cockpit is 
            # <mech>_window.  Also need to figure out how to deal with _generic materials after the import.
            materialname = mechname + "_body"
            if any(weapon in aname for weapon in constants.weapons):
                materialname = mechname + "_variant"
            if "_damaged" in aname or "_prop" in aname:
                materialname = mechname + "_body"
            if "head_cockpit" in aname:
                materialname = mechname + "_window"
            # We now have all the geometry parts that need to be imported, their loc/rot, and material.  Import.
            print('Material: ' + materialname)
            try:
                bpy.ops.wm.collada_import(filepath=binding,find_chains=True,auto_connect=True)
            except:
                # Unable to open the file.  Probably not found (like Urbie lights, under purchasables).
                continue
            obj_objects = bpy.context.selected_objects[:]
            i = 0
            for obj in obj_objects:
                if not obj.type == 'EMPTY':
                    armature.select_set(True)
                    bpy.context.view_layer.objects.active = armature
                    bpy.context.view_layer.objects.active = obj
                    print("    Name: " + obj.name)
                    # If this is a parent node, rotate/translate it. Otherwise skip it.
                    if i == 0:
                        matrix = utilities.get_transform_matrix(rotation, location)       # Converts the location vector and rotation quat into a 4x4 matrix.
                        #parent this first object to the appropriate bone
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
                        # no materials
                        bpy.context.object.data.materials.append(bpy.data.materials[materialname])               # If there is no material, add a dummy mat.
                    else:
                        # Material corrections.  If material slot 0 contains "generic", it's a generic material, unless the key doesn't exist.  Otherwise stays variant.
                        if "generic" in obj.material_slots[0].name:
                            if  mechname + "_generic" in bpy.data.materials.keys():
                                materialname = mechname + "_generic"
                            else:
                                materialname = "generic"            # For some reason it's just generic, not <mech>_generic
                        else:
                            materialname = mechname + "_variant"
                        if "_prop" in obj.name:
                            materialname = mechname + "_body"
                        bpy.context.object.data.materials[0] = bpy.data.materials[materialname]
                    obj.select_set(False)

def link_geometry(objectname, libraryfile, itemgroupname):
    # Link the object from the library file and translate/rotate.
    # print("Linking " + itemgroupname + " from " + libraryfile)
    scene = bpy.context.scene
    if os.path.isfile(libraryfile):
        with bpy.data.libraries.load(libraryfile, link=True) as (data_src, data_dest):
            data_dest.groups = data_src.groups
        for group in data_dest.groups:
            if group.name == itemgroupname:
                ob = bpy.data.objects.new(group.name, None)
                ob.dupli_group = group
                ob.dupli_type = 'GROUP'
                ob.name = objectname
                scene.collection.objects.link(ob)
                print("Imported object: " + ob.name)
                return ob
    elif os.path.isfile(libraryfile.replace("industrial", "frontend//mechlab_a")):  # MWO Mechlab hack
        libraryfile = libraryfile.replace("industrial", "frontend//mechlab_a")
        with bpy.data.libraries.load(libraryfile, link=True) as (data_src, data_dest):
            data_dest.groups = data_src.groups
        for group in data_dest.groups:
            if group.name == itemgroupname:
                ob = bpy.data.objects.new(group.name, None)
                ob.dupli_group = group
                ob.dupli_type = 'GROUP'
                ob.name = objectname
                #scene.objects.link(ob)
                scene.collection.objects.link(ob)
                print("Imported object: " + ob.name)
                return ob
    else:
        print("Unable to find library file " + libraryfile)
        return None

def save_file(file):
    # Save the Blender file as the name of the directory it is in.
    # file is the value put into the file selector.  The cdf file for mech importer,
    # directory for asset importer.
    print("Saving " + file)
    if not os.path.isfile(file):  # Directory
        basename = os.path.basename(os.path.dirname(file))
        if not bpy.path.abspath("//"):      # not saved yet
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(file, basename + ".blend"), check_existing = True)
    else:
        if file.endswith(".cdf"):
            file = file.replace(".cdf", "")
        basename = os.path.basename(file)
        if not bpy.path.abspath("//"):      # not saved yet
            bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(file), basename + ".blend"), check_existing = True)  # CDF file
    
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
    empties = [obj for obj in bpy.data.objects 
               if obj.name.startswith('fire') 
               or 'physics_proxy' in obj.name 
               or obj.name.endswith('_fx') 
               or obj.name.endswith('_case')
               or obj.name.startswith('animation')]
    for empty in empties:
        cc_collections.link_object_to_collection(empty, constants.EMPTIES_LAYER)
    # Set weapons and special geometry to Weapons Collection
    #names = bpy.data.objects.keys()
    for weapon in bpy.data.objects:
        if any(x in weapon.name for x in constants.weapons):
            cc_collections.link_object_to_collection(weapon, constants.WEAPONS_LAYER)
    move_damaged_parts_to_collection()

def move_damaged_parts_to_collection():
    for obj in bpy.data.objects:
        if obj.name.endswith('_damaged') or obj.name.endswith('_damged'):
            cc_collections.link_object_to_collection(obj, constants.DAMAGED_PARTS_LAYER)

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
    location = utilities.convert_to_location(object.attrib["Pos"])
    rotation = utilities.convert_to_rotation(object.attrib["Rotate"])
    matrix = utilities.get_transform_matrix(rotation, location)
    # obj = bpy.data.objects["objectname"]
    obj.rotation_mode = 'QUATERNION'
    obj.matrix_world = matrix
    return obj

def import_asset(context, *, use_dds=True, use_tif=False, auto_save_file=True, auto_generate_preview=False, path):
    print("Import Asset.  Folder: " + path)
    basedir = get_base_dir(path)
    set_viewport_shading()
    cc_collections.set_up_collections()
    if os.path.isdir(path):
        os.chdir(path)
    elif os.path.isfile(path):
        os.chdir(os.path.dirname(path))
        path = os.path.dirname(path)
    for file in os.listdir(path):
        if file.endswith(".mtl"):
            constants.materials.update(materials.create_materials(file, basedir, use_dds, use_tif))
    for material in constants.materials.keys():
        print("   Material: " + material)
    for file in os.listdir(path):
        if file.endswith(".dae"):
            objects = import_geometry(file, basedir)
    objects = bpy.data.objects
    for obj in objects:
        if not obj.name == "Lamp" and not obj.name == "Camera" and not obj.name == "Cube":
            print("   Assigning materials for " + obj.name)
            for obj_mat in obj.material_slots:
                print("   Material slot matname is " + obj_mat.name)
                mat = obj_mat.name.split('.')[0]
                print("      Assigning material " + mat + " to " + obj.name)
                if mat in constants.materials.keys():
                    obj_mat.material = constants.materials[mat]
                #if mats.name[-3:].isdigit() and mats.name[:-4] == materials[mats.name[:-4]].name:
                #    mats.material = materials[mats.name[:-4]]
                #elif not mats.name[-3:].isdigit() and mats.name == materials[mats.name].name:
                #    mats.material = materials[mats.name]
    create_object_groups()
    # Save the file in the directory being read, given the directory name.  Then
    # the user can create the thumbnails into the given blend file.
    if auto_save_file == True:
        save_file(path)
    if auto_save_file == True and auto_generate_preview == True:
        generate_preview(bpy.data.filepath)            #  Only generate the preview if the file is saved.
    return {'FINISHED'}

def import_mech(context, *, use_dds=True, use_tif=False, auto_save_file=True, auto_generate_preview=False, path):
    print("Import Mech")
    print(path)
    cdffile = path      # The input file
    # Split up path into the variables we want.
    basedir = get_base_dir(path)
    bodydir = get_body_dir(path)
    mechdir = os.path.dirname(path)
    mech = get_mech(path)
    matfile = os.path.join(bodydir, mech + "_body.mtl")
    cockpit_matfile = os.path.join(mechdir, "cockpit_standard", mech + 
                                   "_a_cockpit_standard.mtl")
    # Set material mode. # iterate through areas in current screen
    set_viewport_shading()
    cc_collections.set_up_collections()
    # Try to import the armature.  If we can't find it, then return error.
    result = bones.import_armature(os.path.join(bodydir, mech + ".dae"))   # import the armature.
    if result == False:    
        print("Error importing armature at: " + 
              os.path.join(bodydir, mech + ".dae"))
        return False
    # Create the materials.
    constants.materials = materials.create_materials(matfile, basedir, use_dds, use_tif)
    constants.cockpit_materials = materials.create_materials(cockpit_matfile, basedir, use_dds, use_tif)
    # Import the geometry and assign materials.
    import_mech_geometry(cdffile, basedir, bodydir, mech)
    # Set the layers for existing objects
    add_objects_to_collections()
    # Advanced Rigging stuff.  Make bone shapes, IKs, etc.
    
    create_IKs()
    if auto_save_file == True:
        save_file(path)
    return {'FINISHED'}

def import_prefab(context, *, use_dds=True, use_tif=False, auto_save_file=True, auto_generate_preview=False, path):
    # Path is the xml file to the prefab.  If attrib "Type" is Brush or GeomEntity, object (GeomEntity has additional
    # features). Group is group of objects. Entity = light.
    set_viewport_shading()
    cc_collections.set_up_collections()
    basedir = get_base_dir(path)
    #basedir = os.path.dirname(path)  # Prefabs found at root, under prefab directory.
    print("Basedir: " + basedir)
    if os.path.isfile(path):
        prefab = ET.parse(path)
    else:
        return {'FINISHED'}  # Couldn't parse the prefab xml.
    # Parse all the Brush objects
    for object in prefab.iter("Object"):
        if object.attrib["Type"] == "Brush":
            # We have an object to import.  Try to find the object in the asset library.
            objectname = object.attrib["Name"]
            libraryfile = os.path.join(basedir, os.path.dirname(object.attrib["Prefab"]), os.path.basename(os.path.dirname(object.attrib["Prefab"])) + ".blend")
            libraryfile = libraryfile.replace("\\","\\\\").replace("/", "\\\\")
            itemgroupname = os.path.splitext(os.path.basename(object.attrib["Prefab"]))[0]
            obj = link_geometry(objectname, libraryfile, itemgroupname)
            if not obj == None:
                location = utilities.convert_to_location(object.attrib["Pos"])
                rotation = utilities.convert_to_rotation(object.attrib["Rotate"])
                matrix = utilities.get_transform_matrix(rotation, location)
                obj.rotation_mode = 'QUATERNION'
                obj.matrix_world = matrix
        if object.attrib["Type"] == "GeomEntity":
            objectname = object.attrib["Name"]
            libraryfile = os.path.join(basedir, os.path.dirname(object.attrib["Geometry"]), os.path.basename(os.path.dirname(object.attrib["Geometry"])) + ".blend")
            libraryfile = libraryfile.replace("\\","\\\\").replace("/", "\\\\")
            itemgroupname = os.path.splitext(os.path.basename(object.attrib["Geometry"]))[0]
            obj = link_geometry(objectname, libraryfile, itemgroupname)
            if not obj == None:
                location = utilities.convert_to_location(object.attrib["Pos"])
                rotation = utilities.convert_to_rotation(object.attrib["Rotate"])
                matrix = utilities.get_transform_matrix(rotation, location)
                obj.rotation_mode = 'QUATERNION'
                obj.matrix_world = matrix
        if object.attrib["Type"] == "Entity" and object.attrib["Layer"] == "Lighting":
            obj = import_light(object)
    return {'FINISHED'}

import bpy
import math
import mathutils
from mathutils import Vector, Matrix, Color
import rna_prop_ui
from . import constants, cc_collections, utilities

def import_armature(rig):
    try:
        bpy.ops.wm.collada_import(filepath=rig, find_chains=True,auto_connect=True)
        armature = bpy.data.objects['Armature']
        bpy.context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT')
        armature.show_in_front = True
        armature.data.show_axes = True
        bpy.context.object.data.display_type = 'BBONE'
        bpy.context.object.display_type = 'WIRE'
    except:
        #File not found
        return False
    return True

def set_bone_layers(armature):
    print("set_bone_layers:  Setting layers for armature.")
    original_context = bpy.context.mode
    bpy.ops.object.mode_set(mode='POSE')
    for bone in armature.data.bones:
        if bone.name not in constants.control_bones:
            bone.layers[1] = True
            bone.layers[0] = False
    bpy.ops.object.mode_set(mode=original_context)
    print("set_bone_layers:  End setting layers.")

def obj_to_bone(obj, rig, bone_name):
    if bpy.context.mode == 'EDIT_ARMATURE':
        raise utilities.MetarigError('obj_to_bone(): does not work while in edit mode')
    bone = rig.data.bones[bone_name]
    mat = rig.matrix_world @ bone.matrix_local
    obj.location = mat.to_translation()
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = mat.to_euler()
    scl = mat.to_scale()
    scl_avg = (scl[0] + scl[1] + scl[2]) / 3
    obj.scale = (bone.length * scl_avg), (bone.length * scl_avg), (bone.length * scl_avg)

def new_bone(armature, bone_name):
    """ Adds a new bone to the given armature object.
        Returns the resulting bone's name.
    """
    print("new_bone:  Creating new bone " + bone_name)
    if armature == bpy.context.active_object and bpy.context.mode == 'EDIT_ARMATURE':
        edit_bone = armature.data.edit_bones.new(bone_name)
        name = edit_bone.name
        edit_bone.head = (0, 0, 0)
        edit_bone.tail = (0, 1, 0)
        edit_bone.roll = 0
        # bpy.ops.object.mode_set(mode='OBJECT')
        # bpy.ops.object.mode_set(mode='EDIT')
        print("new_bone:  End creating new bone - " + name)
        return name
    else:
        raise utilities.MetarigError("Can't add new bone '%s' outside of edit mode" % bone_name)

def copy_bone(armature, bone_name, assign_name=''):
    """ Makes a copy of the given bone in the given armature object.
        Returns the resulting bone's name.
    """
    print("copy_bone:  Copying " + bone_name + " to " + assign_name)
    #if bone_name not in obj.data.bones:
    if bone_name not in armature.data.edit_bones:
        raise utilities.MetarigError("copy_bone(): bone '%s' not found, cannot copy it" % bone_name)
    
    if armature == bpy.context.active_object and bpy.context.mode == 'EDIT_ARMATURE':
        if assign_name == '':
            assign_name = bone_name
        # Copy the edit bone
        edit_bone_1 = armature.data.edit_bones[bone_name]
        edit_bone_2 = armature.data.edit_bones.new(assign_name)
        bone_name_1 = bone_name
        bone_name_2 = edit_bone_2.name
        
        edit_bone_2.parent = edit_bone_1.parent
        edit_bone_2.use_connect = edit_bone_1.use_connect

        # Copy edit bone attributes
        edit_bone_2.layers = list(edit_bone_1.layers)

        edit_bone_2.head = Vector(edit_bone_1.head)
        edit_bone_2.tail = Vector(edit_bone_1.tail)
        edit_bone_2.roll = edit_bone_1.roll

        edit_bone_2.use_inherit_rotation = edit_bone_1.use_inherit_rotation
        edit_bone_2.use_inherit_scale = edit_bone_1.use_inherit_scale
        edit_bone_2.use_local_location = edit_bone_1.use_local_location

        edit_bone_2.use_deform = edit_bone_1.use_deform
        edit_bone_2.bbone_segments = edit_bone_1.bbone_segments
        edit_bone_2.bbone_easein = edit_bone_1.bbone_easein
        edit_bone_2.bbone_easeout = edit_bone_1.bbone_easeout

        bpy.ops.object.mode_set(mode='OBJECT')

        # Get the pose bones
        pose_bone_1 = armature.pose.bones[bone_name_1]
        pose_bone_2 = armature.pose.bones[bone_name_2]

        # Copy pose bone attributes
        pose_bone_2.rotation_mode = pose_bone_1.rotation_mode
        pose_bone_2.rotation_axis_angle = tuple(pose_bone_1.rotation_axis_angle)
        pose_bone_2.rotation_euler = tuple(pose_bone_1.rotation_euler)
        pose_bone_2.rotation_quaternion = tuple(pose_bone_1.rotation_quaternion)

        pose_bone_2.lock_location = tuple(pose_bone_1.lock_location)
        pose_bone_2.lock_scale = tuple(pose_bone_1.lock_scale)
        pose_bone_2.lock_rotation = tuple(pose_bone_1.lock_rotation)
        pose_bone_2.lock_rotation_w = pose_bone_1.lock_rotation_w
        pose_bone_2.lock_rotations_4d = pose_bone_1.lock_rotations_4d

        # Copy custom properties
        for key in pose_bone_1.keys():
            if key != "_RNA_UI" \
            and key != "rigify_parameters" \
            and key != "rigify_type":
                prop1 = rna_prop_ui.rna_idprop_ui_prop_get(pose_bone_1, key, create=False)
                prop2 = rna_prop_ui.rna_idprop_ui_prop_get(pose_bone_2, key, create=True)
                pose_bone_2[key] = pose_bone_1[key]
                for key in prop1.keys():
                    prop2[key] = prop1[key]
        
        bpy.ops.object.mode_set(mode='EDIT')
        return bone_name_2
    else:
        raise utilities.MetarigError("Cannot copy bones outside of edit mode")

def copy_bone_simple(armature, bone_name, assign_name=''):
    """ Makes a copy of the given bone in the given armature object.
        but only copies head, tail positions and roll. Does not
        address parenting either.
    """
    print("copy_bone_simple:  Creating simple bone " + assign_name + " from " + bone_name)
    if bone_name not in armature.data.edit_bones:
        raise utilities.MetarigError("copy_bone(): bone '%s' not found, cannot copy it" % bone_name)

    if armature == bpy.context.active_object and bpy.context.mode == 'EDIT_ARMATURE':
        if assign_name == '':
            assign_name = bone_name
        # Copy the edit bone
        edit_bone_1 = armature.data.edit_bones[bone_name]
        edit_bone_2 = armature.data.edit_bones.new(assign_name)
        bone_name_2 = edit_bone_2.name

        # Copy edit bone attributes
        edit_bone_2.layers = list(edit_bone_1.layers)
        edit_bone_2.head = Vector(edit_bone_1.head)
        edit_bone_2.tail = Vector(edit_bone_1.tail)
        edit_bone_2.roll = edit_bone_1.roll
        print("copy_bone_simple:  End creating simple bone.")
        return bone_name_2
    else:
        raise utilities.MetarigError("Cannot copy bones outside of edit mode")

def flip_bone(armature, bone_name):
    if bone_name not in armature.data.bones:
        raise utilities.MetarigError('flip_bone(): bone "%s" not found, cannot copy it' % bone_name)
    if armature == bpy.context.active_object and bpy.context.mode == 'EDIT_ARMATURE':
        bone = armature.data.edit_bones[bone_name]
        head = mathutils.Vector(bone.head)
        tail = mathutils.Vector(bone.tail)
        bone.tail = head + tail
        bone.head = tail
        bone.tail = head
    else:
        raise utilities.MetarigError('Cannot flip bones outside of edit mode')

def align_bone_roll(armature, bone1, bone2):
    """ Aligns the roll of two bones.
    """
    bone1_e = armature.data.edit_bones[bone1]
    bone2_e = armature.data.edit_bones[bone2]

    bone1_e.roll = 0.0

    # Get the directions the bones are pointing in, as vectors
    y1 = bone1_e.y_axis
    x1 = bone1_e.x_axis
    y2 = bone2_e.y_axis
    x2 = bone2_e.x_axis

    # Get the shortest axis to rotate bone1 on to point in the same direction as bone2
    axis = y1.cross(y2)
    axis.normalize()

    # Angle to rotate on that shortest axis
    angle = y1.angle(y2)

    # Create rotation matrix to make bone1 point in the same direction as bone2
    rot_mat = Matrix.Rotation(angle, 3, axis)

    # Roll factor
    x3 = rot_mat @ x1
    dot = x2 @ x3
    if dot > 1.0:
        dot = 1.0
    elif dot < -1.0:
        dot = -1.0
    roll = math.acos(dot)

    # Set the roll
    bone1_e.roll = roll

    # Check if we rolled in the right direction
    x3 = rot_mat @ bone1_e.x_axis
    check = x2 @ x3

    # If not, reverse
    if check < 0.9999:
        bone1_e.roll = -roll

def align_bone_x_axis(obj, bone, vec):
    """ Rolls the bone to align its x-axis as closely as possible to
        the given vector.
        Must be in edit mode.
    """
    bone_e = obj.data.edit_bones[bone]

    vec = vec.cross(bone_e.y_axis)
    vec.normalize()

    dot = max(-1.0, min(1.0, bone_e.z_axis.dot(vec)))
    angle = math.acos(dot)

    bone_e.roll += angle

    dot1 = bone_e.z_axis.dot(vec)

    bone_e.roll -= angle * 2

    dot2 = bone_e.z_axis.dot(vec)

    if dot1 > dot2:
        bone_e.roll += angle * 2


def align_bone_z_axis(obj, bone, vec):
    """ Rolls the bone to align its z-axis as closely as possible to
        the given vector.
        Must be in edit mode.
    """
    bone_e = obj.data.edit_bones[bone]

    vec = bone_e.y_axis.cross(vec)
    vec.normalize()

    dot = max(-1.0, min(1.0, bone_e.x_axis.dot(vec)))
    angle = math.acos(dot)

    bone_e.roll += angle

    dot1 = bone_e.x_axis.dot(vec)

    bone_e.roll -= angle * 2

    dot2 = bone_e.x_axis.dot(vec)

    if dot1 > dot2:
        bone_e.roll += angle * 2


def align_bone_y_axis(obj, bone, vec):
    """ Matches the bone y-axis to
        the given vector.
        Must be in edit mode.
    """

    bone_e = obj.data.edit_bones[bone]
    vec.normalize()
    vec = vec * bone_e.length

    bone_e.tail = bone_e.head + vec
import bpy
import mathutils
from . import constants, cc_collections

def import_armature(rig):
    try:
        bpy.ops.wm.collada_import(filepath=rig, find_chains=True,auto_connect=True)
        armature = bpy.data.objects['Armature']
        #bpy.context.scene.objects.active = armature
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
    original_context = bpy.context.mode
    bpy.ops.object.mode_set(mode='POSE')
    for bone in armature.data.bones:
        if bone.name not in constants.control_bones:
            bone.layers[1] = True
            bone.layers[0] = False
    bpy.ops.object.mode_set(mode=original_context)

def obj_to_bone(obj, rig, bone_name):
    if bpy.context.mode == 'EDIT_ARMATURE':
        raise MetarigError('obj_to_bone(): does not work while in edit mode')
    bone = rig.data.bones[bone_name]
    #mat = rig.matrix_world * bone.matrix_local
    mat = rig.matrix_world @ bone.matrix_local
    obj.location = mat.to_translation()
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler = mat.to_euler()
    scl = mat.to_scale()
    scl_avg = (scl[0] + scl[1] + scl[2]) / 3
    obj.scale = (bone.length * scl_avg), (bone.length * scl_avg), (bone.length * scl_avg)

def copy_bone(obj, bone_name, assign_name=''):
    if bone_name not in obj.data.edit_bones:
        raise MetarigError('copy_bone(): bone "%s" not found, cannot copy it' % bone_name)
    if obj == bpy.context.active_object and bpy.context.mode == 'EDIT_ARMATURE':
        if assign_name == '':
            assign_name = bone_name
        # Copy the edit bone
        edit_bone_1 = obj.data.edit_bones[bone_name]
        edit_bone_2 = obj.data.edit_bones.new(assign_name)
        bone_name_1 = bone_name
        bone_name_2 = edit_bone_2.name
        edit_bone_2.parent = edit_bone_1.parent
        edit_bone_2.use_connect = edit_bone_1.use_connect
        # Copy edit bone attributes
        edit_bone_2.layers = list(edit_bone_1.layers)
        edit_bone_2.head = mathutils.Vector(edit_bone_1.head)
        edit_bone_2.tail = mathutils.Vector(edit_bone_1.tail)
        edit_bone_2.roll = edit_bone_1.roll
        edit_bone_2.head_radius = edit_bone_1.head_radius
        edit_bone_2.envelope_distance = edit_bone_1.envelope_distance
        edit_bone_2.use_inherit_rotation = edit_bone_1.use_inherit_rotation
        edit_bone_2.use_inherit_scale = edit_bone_1.use_inherit_scale
        edit_bone_2.use_local_location = edit_bone_1.use_local_location
        edit_bone_2.use_deform = edit_bone_1.use_deform
        edit_bone_2.bbone_segments = edit_bone_1.bbone_segments
        edit_bone_2.bbone_rollin = edit_bone_1.bbone_rollin
        edit_bone_2.bbone_rollout = edit_bone_1.bbone_rollout
        edit_bone_2.bbone_easein = edit_bone_1.bbone_easein
        edit_bone_2.bbone_easeout = edit_bone_1.bbone_easeout
        bpy.ops.object.mode_set(mode='OBJECT')
        # Get the pose bones
        pose_bone_1 = obj.pose.bones[bone_name_1]
        pose_bone_2 = obj.pose.bones[bone_name_2]
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
            if key != '_RNA_UI' \
            and key != 'rigify_parameters' \
            and key != 'rigify_type':
                prop1 = rna_idprop_ui_prop_get(pose_bone_1, key, create=False)
                prop2 = rna_idprop_ui_prop_get(pose_bone_2, key, create=True)
                pose_bone_2[key] = pose_bone_1[key]
                for key in prop1.keys():
                    prop2[key] = prop1[key]

        bpy.ops.object.mode_set(mode='EDIT')
        return bone_name_2
    else:
        raise MetarigError('Cannot copy bones outside of edit mode')

def flip_bone(obj, bone_name):
    if bone_name not in obj.data.bones:
        raise MetarigError('flip_bone(): bone "%s" not found, cannot copy it' % bone_name)
    if obj == bpy.context.active_object and bpy.context.mode == 'EDIT_ARMATURE':
        bone = obj.data.edit_bones[bone_name]
        head = mathutils.Vector(bone.head)
        tail = mathutils.Vector(bone.tail)
        bone.tail = head + tail
        bone.head = tail
        bone.tail = head
    else:
        raise MetarigError('Cannot flip bones outside of edit mode')

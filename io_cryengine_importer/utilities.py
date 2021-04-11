import os

import bpy
import mathutils
from . import constants

def get_scaling_factor(o):
    local_bbox_center = 0.125 * sum((mathutils.Vector(b) for b in o.bound_box), mathutils.Vector())
    global_bbox_center = o.matrix_world @ local_bbox_center
    return global_bbox_center[2]/7.4

def convert_to_rotation(rotation):
    tmp = rotation.split(',')
    w = float(tmp[0])
    x = float(tmp[1])
    y = float(tmp[2])
    z = float(tmp[3])
    return mathutils.Quaternion((w,x,y,z))

def convert_to_location(location):
    tmp = location.split(',')
    x = float(tmp[0])
    y = float(tmp[1])
    z = float(tmp[2])
    return mathutils.Vector((x,y,z))

def convert_to_rgba(color):
    temp = color.split(',')
    r = float(temp[0])
    g = float(temp[1])
    b = float(temp[2])
    a = 1.0
    return (r,g,b,a)

def convert_to_rgb(color):
    temp = color.split(',')
    r = float(temp[0])
    g = float(temp[1])
    b = float(temp[2])
    return (r,g,b)

def get_transform_matrix(rotation, location):
    mat_location = mathutils.Matrix.Translation(location)
    mat_rotation = mathutils.Matrix.Rotation(rotation.angle, 4, rotation.axis)
    mat_scale = mathutils.Matrix.Scale(1, 4, (0.0, 0.0, 1.0))  # Identity matrix
    mat_out = mat_location @ mat_rotation @ mat_scale
    return mat_out

def set_mode(new_mode):
    bpy.ops.object.mode_set(mode=new_mode)

def get_filename(texture, material_extension):
    # Don't do relative filenames!  It doesn't work until the .blend file is saved, and even then it doesn't work!
    texturefile = os.path.normpath(os.path.join(constants.basedir, os.path.splitext(texture)[0] + material_extension))
    tex = texturefile.replace("/", "\\\\")
    return tex

#=======================================================================
# Error handling
#=======================================================================
class MetarigError(Exception):
    """ Exception raised for errors.
    """
    def __init__(self, message):
        self.message = message
        print("Metarig Error thrown: " + message)
    def __str__(self):
        return repr(self.message)
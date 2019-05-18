import bpy
# from constants import *
from . import constants

def create_collection(collection_name):
    if collection_name not in bpy.data.collections.keys():
        collection = bpy.data.collections.new(collection_name)
        bpy.context.scene.collection.children.link(collection)

def link_object_to_collection(object, collection_name):
    collection = bpy.data.collections[collection_name]
    collection.objects.link(object)

def get_collection_object(collection_name):
    if collection_name in bpy.data.collections.keys():
        return bpy.data.collections[collection_name]

def set_up_collections():
    create_collection(constants.WGT_LAYER)
    hide_collection(constants.WGT_LAYER)
    create_collection(constants.CTRL_LAYER)
    create_collection(constants.GEO_LAYER)

def hide_collection(collection_name):
    collection = get_collection_object(collection_name)
    collection.hide_viewport = True

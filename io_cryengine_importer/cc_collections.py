import bpy
from . import constants

def create_collection(collection_name):
    if collection_name not in bpy.data.collections.keys():
        return bpy.data.collections.new(collection_name)

def add_collection_to_parent(parent_collection, child_collection):
    parent_collection.children.link(child_collection)

def link_object_to_collection(object, collection_name):
    collection = bpy.data.collections[collection_name]
    if object.name in collection.objects:
        return
    collection.objects.link(object)

def get_collection_object(collection_name):
    if collection_name in bpy.data.collections.keys():
        return bpy.data.collections[collection_name]

def set_up_collections():
    create_collection(constants.WIDGETS_COLLECTION)
    hide_collection(constants.WIDGETS_COLLECTION)
    create_collection(constants.CONTROL_BONES_COLLECTION)
    create_collection(constants.DEFORM_BONES_COLLECTION)
    create_collection(constants.EMPTIES_COLLECTION)
    create_collection(constants.WEAPONS_COLLECTION)
    create_collection(constants.DAMAGED_PARTS_COLLECTION)

def set_up_asset_collections():
    create_collection(constants.WIDGETS_COLLECTION)
    hide_collection(constants.WIDGETS_COLLECTION)
    create_collection(constants.CONTROL_BONES_COLLECTION)
    create_collection(constants.DEFORM_BONES_COLLECTION)
    create_collection(constants.EMPTIES_COLLECTION)

def hide_collection(collection_name):
    collection = get_collection_object(collection_name)
    collection.hide_viewport = True

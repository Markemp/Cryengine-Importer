import os
import bpy
from . import constants

def create_collection(collection_name, as_child_of=""):
    if collection_name not in bpy.data.collections.keys():
        collection = bpy.data.collections.new(collection_name)
        if as_child_of != "":
            if as_child_of in bpy.data.collections.keys():
                col = bpy.data.collections[as_child_of]
                col.children.link(collection)
        return collection

def add_collection_to_parent(parent_collection, child_collection):
    parent_collection.children.link(child_collection)

def link_object_to_collection(object, collection_name):
    collection = bpy.data.collections[collection_name]
    if object.name in [o.name for o in collection.objects]:
        return
    collection.objects.link(object)

def unlink_object_except_from_collection(object, collection_name):
    for collection in object.users_collection:
        if collection.name != collection_name:
            collection.objects.unlink(object)

def move_object_to_collection(object, collection_name, include_children=True):
    collection = bpy.data.collections[collection_name]
    if object.name not in [o.name for o in collection.objects]:
        collection.objects.link(object)
    unlink_object_except_from_collection(object, collection_name)

def get_collection_object(collection_name):
    if collection_name in bpy.data.collections.keys():
        return bpy.data.collections[collection_name]

def set_up_collections(file_path):
    mech_collection = create_collection(constants.MECH_COLLECTION, "Scene Collection")
    create_collection(constants.WIDGETS_COLLECTION, constants.MECH_COLLECTION)
    create_collection(constants.EMPTIES_COLLECTION, constants.MECH_COLLECTION)
    create_collection(constants.WEAPONS_COLLECTION, constants.MECH_COLLECTION)
    create_collection(constants.DAMAGED_PARTS_COLLECTION, constants.MECH_COLLECTION)
    create_collection(constants.VARIANTS_COLLECTION, constants.MECH_COLLECTION)
    variants = get_variant_names(file_path)
    for variant in variants:
        create_collection(variant, constants.VARIANTS_COLLECTION)
    bpy.data.scenes[0].collection.children.link(mech_collection)

def set_up_asset_collections():
    create_collection(constants.WIDGETS_COLLECTION)
    create_collection(constants.EMPTIES_COLLECTION)

def get_variant_names(file_path):
    mdf_files = []
    directory = os.path.dirname(file_path)
    for file in os.listdir(directory):
        if file.endswith(".mdf"):
            file_name_without_extension = os.path.splitext(file)[0].upper()
            mdf_files.append(file_name_without_extension)
    return mdf_files
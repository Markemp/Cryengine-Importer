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


def _find_layer_collection(layer_collection, name):
    if layer_collection.collection.name == name:
        return layer_collection
    for child in layer_collection.children:
        result = _find_layer_collection(child, name)
        if result is not None:
            return result
    return None


def hide_in_view_layer(collection_name):
    """Close the outliner eyeball for a collection in the active view layer
    without disabling it (so the eye stays clickable, not greyed out)."""
    root = bpy.context.view_layer.layer_collection
    layer = _find_layer_collection(root, collection_name)
    if layer is not None:
        layer.hide_viewport = True

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
    widgets_collection = create_collection(constants.WIDGETS_COLLECTION, constants.MECH_COLLECTION)
    empties_collection = create_collection(constants.EMPTIES_COLLECTION, constants.MECH_COLLECTION)
    weapons_collection = create_collection(constants.WEAPONS_COLLECTION, constants.MECH_COLLECTION)
    damaged_parts_collection = create_collection(constants.DAMAGED_PARTS_COLLECTION, constants.MECH_COLLECTION)
    variants_collection = create_collection(constants.VARIANTS_COLLECTION, constants.MECH_COLLECTION)
    cockpit_collection = create_collection(constants.COCKPIT_COLLECTION, constants.MECH_COLLECTION)

    variants = get_variant_names(file_path)
    for variant in variants:
        create_collection(variant, constants.VARIANTS_COLLECTION)

    # Link Mech to the scene FIRST so the LayerCollection tree gets populated
    # for every child collection.  hide_in_view_layer() walks that tree and is
    # a no-op for collections that aren't in the view layer yet.
    bpy.data.scenes[0].collection.children.link(mech_collection)

    # Hide collections that hold "showcase" geometry by default.  Per-object
    # eyeballs stay open; clicking a Variants/<VARIANT> eyeball reveals only
    # that variant's linked weapons (one-click loadout preview).
    #
    # We set the LayerCollection's hide_viewport (the outliner eyeball) so
    # the user can re-enable with one click.  Setting Collection.hide_viewport
    # would "Disable in Viewport" instead, which greys out the eyeball.
    #
    # The Variants parent stays visible — a parent's hide propagates to
    # all descendants, which would defeat per-variant toggling.
    for name in (constants.WIDGETS_COLLECTION, constants.EMPTIES_COLLECTION,
                 constants.WEAPONS_COLLECTION, constants.DAMAGED_PARTS_COLLECTION,
                 constants.COCKPIT_COLLECTION):
        hide_in_view_layer(name)
    for variant in variants:
        hide_in_view_layer(variant)

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

import os
import glob
import bpy
from .CryXmlB.CryXmlReader import CryXmlSerializer


def get_skeleton_name_from_cdf(cdf_path):
    """Parse a CDF file to extract the skeleton name.
    The CDF's Model File attribute references the .chr skeleton file,
    e.g. 'objects/characters/animals/hen/skeleton_hen_01.chr' → 'skeleton_hen_01'
    """
    cry_xml = CryXmlSerializer()
    cdf = cry_xml.read_file(cdf_path)
    model = cdf.find(".//Model")
    if model is not None and "File" in model.attrib:
        chr_path = model.attrib["File"]
        return os.path.splitext(os.path.basename(chr_path))[0]
    return None


def discover_animation_files(directory, skeleton_name):
    """Find all animation USDA files for a given skeleton in a directory.
    Animation files follow the pattern: {skeleton_name}_anim_*.usda
    Returns a list of file paths.
    """
    pattern = os.path.join(directory, f"{skeleton_name}_anim_*.usda")
    return sorted(glob.glob(pattern))


def import_animation(anim_file, main_armature):
    """Import a single animation USDA, extract the Action, assign it to the
    main armature, and clean up the imported skeleton.
    Returns the Action, or None on failure.
    """
    print(f"Importing animation: {anim_file}")
    objects_before = set(bpy.data.objects)
    actions_before = set(bpy.data.actions)

    bpy.ops.wm.usd_import(
        filepath=anim_file,
        import_skeletons=True,
        import_meshes=False
    )

    objects_after = set(bpy.data.objects)
    actions_after = set(bpy.data.actions)

    new_objects = objects_after - objects_before
    new_actions = actions_after - actions_before

    if not new_actions:
        print(f"  No action created from {anim_file}")
        # Clean up any imported objects
        for obj in new_objects:
            bpy.data.objects.remove(obj, do_unlink=True)
        return None

    action = new_actions.pop()

    # Rename action from USD prim name to filename-derived name
    action_name = os.path.splitext(os.path.basename(anim_file))[0]
    action.name = action_name
    action.use_fake_user = True
    print(f"  Action: {action.name}")

    # Delete all imported objects (skeleton, empties)
    for obj in new_objects:
        bpy.data.objects.remove(obj, do_unlink=True)

    return action


def import_all_animations(directory, skeleton_name, main_armature):
    """Discover and import all animations for a skeleton.
    Returns a list of imported Actions.
    """
    anim_files = discover_animation_files(directory, skeleton_name)
    if not anim_files:
        print(f"No animation files found for {skeleton_name} in {directory}")
        return []

    print(f"Found {len(anim_files)} animation files for {skeleton_name}")
    actions = []
    for anim_file in anim_files:
        action = import_animation(anim_file, main_armature)
        if action:
            actions.append(action)

    print(f"Imported {len(actions)} animations")
    return actions

import os
import glob
import xml.etree.ElementTree as ET
import bpy
from .CryXmlB.CryXmlReader import CryXmlSerializer

# Names in chrparams AnimationList that are metadata, not animation files
_CHRPARAMS_SPECIAL_NAMES = frozenset({
    "$AnimEventDatabase", "$TracksDatabase", "$facelib", "$Include"
})


def get_skeleton_name_from_chrparams(chrparams_path):
    """Return the skeleton name from a chrparams file path.
    The filename stem IS the skeleton name.
    """
    return os.path.splitext(os.path.basename(chrparams_path))[0]


def parse_chrparams(chrparams_path, game_root, _depth=0, _max_depth=5):
    """Parse a chrparams file and follow $Include directives to collect
    the animation base filepath and wildcard patterns.

    Returns dict with:
        filepath: str or None — the #filepath base path (relative to game root)
        patterns: list[str] — wildcard glob patterns for animation files
    """
    result = {"filepath": None, "patterns": []}

    if _depth >= _max_depth:
        print(f"  chrparams include depth limit reached at {chrparams_path}")
        return result

    cry_xml = CryXmlSerializer()
    tree = cry_xml.read_file(chrparams_path)
    if tree is None:
        return result

    # CryXmlSerializer returns ElementTree for text XML, or an Element for binary
    root = tree.getroot() if isinstance(tree, ET.ElementTree) else tree
    anim_list = root.find("AnimationList")
    if anim_list is None:
        return result

    for anim in anim_list.findall("Animation"):
        name = anim.get("name", "")
        path = anim.get("path", "")

        if name == "$Include":
            include_path = os.path.join(game_root, path.replace("\\", os.sep))
            if os.path.isfile(include_path):
                included = parse_chrparams(include_path, game_root,
                                           _depth + 1, _max_depth)
                if included["filepath"] and not result["filepath"]:
                    result["filepath"] = included["filepath"]
                result["patterns"].extend(included["patterns"])
            else:
                print(f"  chrparams $Include not found: {include_path}")

        elif name == "#filepath":
            result["filepath"] = path.replace("\\", "/")

        elif name.startswith("$") or name.startswith("#"):
            # Skip other special directives
            continue

        elif name == "Comment":
            continue

        else:
            # Wildcard pattern entry like name="*" path="*/*.caf"
            result["patterns"].append(path.replace("\\", "/"))

    return result


def discover_animations_from_chrparams(chrparams_path, game_root, skeleton_name):
    """Discover animation USDA files using chrparams information.

    Searches both the chrparams directory (where the converter places files)
    and any resolved #filepath directory from the chrparams.
    Returns a sorted list of unique file paths.
    """
    parsed = parse_chrparams(chrparams_path, game_root)
    search_dirs = set()

    # Always search the directory containing the chrparams
    search_dirs.add(os.path.dirname(chrparams_path))

    # Also search the resolved #filepath directory
    if parsed["filepath"]:
        resolved = os.path.join(game_root, parsed["filepath"].replace("/", os.sep))
        if os.path.isdir(resolved):
            search_dirs.add(os.path.normpath(resolved))

    # Collect matching USDA files from all search directories
    found = set()
    pattern_name = f"{skeleton_name}_anim_*.usda"
    for search_dir in search_dirs:
        for f in glob.glob(os.path.join(search_dir, pattern_name)):
            found.add(os.path.normpath(f))

    return sorted(found)


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


def import_all_animations_from_files(anim_files, main_armature):
    """Import a list of animation USDA files.
    Returns a list of imported Actions.
    """
    if not anim_files:
        print("No animation files to import")
        return []

    print(f"Importing {len(anim_files)} animation files")
    actions = []
    for anim_file in anim_files:
        action = import_animation(anim_file, main_armature)
        if action:
            actions.append(action)

    print(f"Imported {len(actions)} animations")
    return actions


def import_all_animations(directory, skeleton_name, main_armature):
    """Discover and import all animations for a skeleton.
    Returns a list of imported Actions.
    """
    anim_files = discover_animation_files(directory, skeleton_name)
    return import_all_animations_from_files(anim_files, main_armature)

import os
import bpy
import mathutils

from . import collections, constants, utilities
from .CryXmlB.CryXmlReader import CryXmlSerializer


def find_cockpit_attachment(cdf_geometry):
    for geo in cdf_geometry.iter("Attachment"):
        if geo.attrib.get("AName") == "cockpit":
            return geo
    return None


def _resolve_usda_path(basedir, binding):
    binding_norm = binding.replace("\\", "/")
    if binding_norm.lower().endswith(".cdf"):
        return os.path.normpath(os.path.join(basedir, binding_norm))
    stem, _ = os.path.splitext(binding_norm)
    return os.path.normpath(os.path.join(basedir, stem + ".usda"))


def _import_usda(usda_path):
    if not os.path.isfile(usda_path):
        return []
    try:
        objects_before = set(bpy.data.objects)
        bpy.ops.wm.usd_import(filepath=usda_path, import_skeletons=True, import_meshes=True,
                              import_materials=True, import_usd_preview=True)
        objects_after = set(bpy.data.objects)
        new_objects = list(objects_after - objects_before)
        return utilities.cleanup_usd_import(new_objects)
    except Exception as e:
        print(f"Error importing cockpit USD file: {usda_path} ({e})")
        return []


def _apply_cockpit_material(obj, material_name):
    if material_name not in bpy.data.materials:
        return
    material = bpy.data.materials[material_name]
    if len(obj.data.materials) == 0:
        obj.data.materials.append(material)
    else:
        obj.data.materials[0] = material


def _pick_cockpit_material_name():
    # cockpit_materials is keyed by material name from the cockpit .mtl.
    # Most cockpits expose a single primary material; pick the first deterministically.
    for name in constants.cockpit_materials.keys():
        return name
    return None


def import_cockpit(parent_attachment, basedir, mechname, armature, report=None):
    """Import the interior cockpit referenced by the parent CDF's `cockpit`
    attachment. Places everything in the Cockpit collection, hidden by default,
    parented to a single empty attached to the mech's COCKPIT bone.
    """
    binding = parent_attachment.attrib.get("Binding", "")
    if not binding:
        if report is not None:
            report.add_warning("Cockpit attachment has no Binding")
        return

    cockpit_cdf_path = os.path.normpath(os.path.join(basedir, binding.replace("\\", "/")))
    if not os.path.isfile(cockpit_cdf_path):
        if report is not None:
            report.add_skipped("cockpit", f"CDF not found: {cockpit_cdf_path}")
        return

    parent_rotation = utilities.convert_to_quaternion(parent_attachment.attrib["Rotation"])
    parent_location = utilities.convert_to_vector(parent_attachment.attrib["Position"])
    parent_bonename = parent_attachment.attrib["BoneName"].replace(' ', '_')
    parent_matrix = utilities.get_transform_matrix(parent_rotation, parent_location)

    cockpit_root = bpy.data.objects.new(f"{mechname}_cockpit_root", None)
    cockpit_root.empty_display_type = 'PLAIN_AXES'
    collections.link_object_to_collection(cockpit_root, constants.COCKPIT_COLLECTION)
    cockpit_root.rotation_mode = 'QUATERNION'
    cockpit_root.parent = armature
    cockpit_root.parent_bone = parent_bonename
    cockpit_root.parent_type = 'BONE'
    cockpit_root.matrix_world = parent_matrix

    cockpit_basedir = os.path.dirname(cockpit_cdf_path)
    material_name = _pick_cockpit_material_name()

    cry_xml = CryXmlSerializer()
    cockpit_xml = cry_xml.read_file(cockpit_cdf_path)

    for sub in cockpit_xml.iter("Attachment"):
        sub_name = sub.attrib.get("AName", sub.attrib.get("Binding", "<unnamed>"))
        sub_binding = sub.attrib.get("Binding", "")
        if not sub_binding:
            if report is not None:
                report.add_skipped(sub_name, "no Binding attribute")
            continue
        usda_path = _resolve_usda_path(constants.basedir, sub_binding)
        if not os.path.isfile(usda_path):
            if report is not None:
                report.add_skipped(sub_name, f"USD file not found: {usda_path}")
            continue
        imported = _import_usda(usda_path)
        if not imported:
            if report is not None:
                report.add_skipped(sub_name, "USD import returned no objects")
            continue
        if report is not None:
            report.add_imported(f"cockpit/{sub_name}")

        sub_rotation = utilities.convert_to_quaternion(sub.attrib["Rotation"])
        sub_location = utilities.convert_to_vector(sub.attrib["Position"])
        sub_matrix = utilities.get_transform_matrix(sub_rotation, sub_location)

        meshes = [obj for obj in imported if obj.type == 'MESH']
        for obj in [o for o in imported if o.type == 'ARMATURE']:
            bpy.data.objects.remove(obj, do_unlink=True)

        for index, obj in enumerate(meshes):
            collections.move_object_to_collection(obj, constants.COCKPIT_COLLECTION)
            if index == 0:
                obj.matrix_world = mathutils.Matrix.Identity(4)
                obj.rotation_mode = 'QUATERNION'
                obj.parent = cockpit_root
                obj.matrix_local = sub_matrix
            if material_name:
                _apply_cockpit_material(obj, material_name)

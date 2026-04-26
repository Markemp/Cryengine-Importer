"""Import Cryengine PrefabsLibrary XML files (.xml) into Blender.

The parser layer (parse_prefabs_library + ParsedObject/ParsedPrefab dataclasses)
has no Blender dependencies and can be tested standalone. The Blender layer
(import_prefab_library + handlers) consumes the parsed model and instantiates
Blender objects.

To support a different container format later (e.g. Star Citizen .soc files),
write a new parser that emits the same ParsedPrefab/ParsedObject structure and
reuse the dispatch + handlers here. New object types can be plugged in by
extending _HANDLERS or _LIGHT_ENTITY_CLASSES.
"""

import math
import os
from dataclasses import dataclass, field
from typing import Optional

import bpy
import mathutils

from . import collections, utilities
from .CryXmlB.CryXmlReader import CryXmlSerializer


# ---------------------------------------------------------------------------
# Pure parsing layer (no Blender deps)
# ---------------------------------------------------------------------------

@dataclass
class ParsedObject:
    id: str
    name: str
    type: str                              # "Brush" / "Group" / "GeomEntity" / "Entity" / etc.
    entity_class: Optional[str] = None     # for Entity objects
    geometry_path: Optional[str] = None    # .cgf/.cga path from the XML
    parent_id: Optional[str] = None        # GUID of parent (sibling reference)
    pos: Optional[tuple] = None            # (x, y, z)
    rotate: Optional[tuple] = None         # (w, x, y, z)
    scale: Optional[tuple] = None          # (x, y, z)
    properties: dict = field(default_factory=dict)   # nested <Properties> as dict tree
    children: list = field(default_factory=list)     # populated for Groups


@dataclass
class ParsedPrefab:
    id: str
    name: str
    library: str
    objects: list                           # top-level ParsedObjects (Groups carry their own children)


def _parse_vec(s):
    if not s:
        return None
    return tuple(float(x) for x in s.split(","))


def _parse_properties(elem):
    """Flatten a <Properties> subtree into nested dicts. Children with their
    own attributes/elements become sub-dicts; leaf attributes become strings."""
    result = dict(elem.attrib)
    for child in elem:
        result[child.tag] = _parse_properties(child)
    return result


def _parse_object(elem):
    obj_type = elem.attrib.get("Type", "")
    geometry = None
    properties = {}

    if obj_type == "Brush":
        geometry = elem.attrib.get("Prefab")
    elif obj_type == "GeomEntity":
        geometry = elem.attrib.get("Geometry")
    elif obj_type == "Entity":
        props_elem = elem.find("Properties")
        if props_elem is not None:
            properties = _parse_properties(props_elem)
        # Entity may carry a model in Properties (objModel / object_Model)
        geometry = properties.get("objModel") or properties.get("object_Model")

    children = []
    if obj_type == "Group":
        objs_elem = elem.find("Objects")
        if objs_elem is not None:
            for child_elem in objs_elem.findall("Object"):
                children.append(_parse_object(child_elem))

    return ParsedObject(
        id=elem.attrib.get("Id", ""),
        name=elem.attrib.get("Name", ""),
        type=obj_type,
        entity_class=elem.attrib.get("EntityClass"),
        geometry_path=geometry,
        parent_id=elem.attrib.get("Parent"),
        pos=_parse_vec(elem.attrib.get("Pos")),
        rotate=_parse_vec(elem.attrib.get("Rotate")),
        scale=_parse_vec(elem.attrib.get("Scale")),
        properties=properties,
        children=children,
    )


def parse_prefabs_library(xml_path):
    """Returns (library_name, list[ParsedPrefab])."""
    tree_or_root = CryXmlSerializer().read_file(xml_path)
    root = tree_or_root.getroot() if hasattr(tree_or_root, "getroot") else tree_or_root
    library_name = root.attrib.get("Name", "Prefabs")

    prefabs = []
    for prefab_elem in root.findall("Prefab"):
        objects = []
        objs_elem = prefab_elem.find("Objects")
        if objs_elem is not None:
            for obj_elem in objs_elem.findall("Object"):
                objects.append(_parse_object(obj_elem))
        prefabs.append(ParsedPrefab(
            id=prefab_elem.attrib.get("Id", ""),
            name=prefab_elem.attrib.get("Name", ""),
            library=prefab_elem.attrib.get("Library", library_name),
            objects=objects,
        ))
    return library_name, prefabs


# ---------------------------------------------------------------------------
# Blender execution layer
# ---------------------------------------------------------------------------

# Tunable: Cryengine's fDiffuseMultiplier (typically 1-8) doesn't map 1:1 to
# Blender Watts. 100 is a starting baseline; iterate after visual review.
LIGHT_ENERGY_SCALE = 100.0

# EntityClass values handled as Blender lights.
_LIGHT_ENTITY_CLASSES = {"Light", "DestroyableLight", "EnvironmentLight"}


def _resolve_usda_path(basedir, geometry):
    if not geometry:
        return None
    norm = geometry.replace("\\", "/")
    stem, _ = os.path.splitext(norm)
    return os.path.normpath(os.path.join(basedir, stem + ".usda"))


def _import_usda(usd_path):
    """Import a USDA file, strip USD hierarchy empties, return new objects."""
    if not os.path.isfile(usd_path):
        return None
    try:
        objects_before = set(bpy.data.objects)
        bpy.ops.wm.usd_import(filepath=usd_path, import_meshes=True,
                              import_materials=True, import_usd_preview=True)
        objects_after = set(bpy.data.objects)
        new_objects = list(objects_after - objects_before)
        return utilities.cleanup_usd_import(new_objects)
    except Exception as e:
        print(f"  USD import failed: {usd_path} ({e})")
        return None


def _link_to_collection(obj, collection):
    """Ensure obj is in `collection` and remove it from any others (incl.
    the default Scene Collection where USD imports land)."""
    if obj.name not in collection.objects:
        collection.objects.link(obj)
    for other in list(obj.users_collection):
        if other != collection:
            other.objects.unlink(obj)


def _apply_local_transform(blender_obj, parsed):
    """Apply pos/rotate/scale from the parsed XML as LOCAL transforms.
    For top-level objects parent_obj is None, so local==world."""
    blender_obj.rotation_mode = 'QUATERNION'
    matrix = mathutils.Matrix.Identity(4)
    if parsed.pos is not None:
        matrix = mathutils.Matrix.Translation(mathutils.Vector(parsed.pos))
    if parsed.rotate is not None:
        w, x, y, z = parsed.rotate
        matrix = matrix @ mathutils.Quaternion((w, x, y, z)).to_matrix().to_4x4()
    if parsed.scale is not None:
        sx, sy, sz = (s if abs(s) > 1e-6 else 1.0 for s in parsed.scale)
        scale_mat = mathutils.Matrix.Diagonal((sx, sy, sz, 1.0))
        matrix = matrix @ scale_mat
    blender_obj.matrix_local = matrix


def _handle_geometry(parsed, parent_obj, basedir, geom_collection, id_map, report):
    """Brush, GeomEntity, or Entity-with-model: import the USD, link, parent."""
    usd_path = _resolve_usda_path(basedir, parsed.geometry_path)
    if usd_path is None:
        report.add_skipped(parsed.name, f"{parsed.type} has no geometry path")
        return None
    if not os.path.isfile(usd_path):
        report.add_skipped(parsed.name, f"USD not found: {usd_path}")
        return None

    new_objects = _import_usda(usd_path)
    if not new_objects:
        report.add_skipped(parsed.name, "USD import returned no objects")
        return None

    meshes = [o for o in new_objects if o.type == 'MESH']
    if not meshes:
        report.add_skipped(parsed.name, "USD import had no mesh")
        return None

    if len(meshes) == 1:
        # Single-mesh model: rename the mesh and apply the brush transform.
        primary = meshes[0]
        primary.name = parsed.name
        _link_to_collection(primary, geom_collection)
        if parent_obj is not None:
            primary.parent = parent_obj
        _apply_local_transform(primary, parsed)
        anchor = primary
    else:
        # Multi-mesh model (e.g. mechbay_armhousing01.usda has Object003 +
        # Object005 sub-meshes).  cleanup_usd_import deleted the parent Xform
        # empties, leaving each mesh at its model-local position with no parent.
        # Create a container Empty named after the brush, parent every mesh to
        # it preserving their model-local positions, then apply the brush
        # transform to the container.
        container = bpy.data.objects.new(parsed.name, None)
        container.empty_display_type = 'PLAIN_AXES'
        _link_to_collection(container, geom_collection)
        for mesh in meshes:
            saved_world = mesh.matrix_world.copy()  # = model-local after cleanup
            mesh.parent = container
            mesh.matrix_parent_inverse = mathutils.Matrix.Identity(4)
            mesh.matrix_local = saved_world
            _link_to_collection(mesh, geom_collection)
        if parent_obj is not None:
            container.parent = parent_obj
        _apply_local_transform(container, parsed)
        anchor = container

    id_map[parsed.id] = anchor
    report.add_imported(parsed.name)
    return anchor


def _handle_group(parsed, parent_obj, basedir, geom_collection, lights_collection, id_map, report):
    """Create an Empty for the group, parent it, then dispatch nested children."""
    empty = bpy.data.objects.new(parsed.name, None)
    empty.empty_display_type = 'PLAIN_AXES'
    _link_to_collection(empty, geom_collection)

    if parent_obj is not None:
        empty.parent = parent_obj
    _apply_local_transform(empty, parsed)

    id_map[parsed.id] = empty

    for child in parsed.children:
        _dispatch_object(child, empty, basedir, geom_collection, lights_collection, id_map, report)

    return empty


def _handle_entity_light(parsed, parent_obj, basedir, geom_collection, lights_collection, id_map, report):
    props = parsed.properties or {}
    color_block = props.get("Color", {}) if isinstance(props.get("Color"), dict) else {}
    projector = props.get("Projector", {}) if isinstance(props.get("Projector"), dict) else {}

    diffuse_str = color_block.get("clrDiffuse", "1,1,1")
    multiplier = float(color_block.get("fDiffuseMultiplier", "1") or "1")
    radius = float(props.get("Radius", "10") or "10")

    project_in_all_dirs = projector.get("bProjectInAllDirs", "1") == "1"
    fov = float(projector.get("fProjectorFov", "0") or "0")
    light_type = 'POINT' if (project_in_all_dirs or fov <= 0) else 'SPOT'

    light_data = bpy.data.lights.new(parsed.name, type=light_type)
    light_obj = bpy.data.objects.new(parsed.name, light_data)

    rgb = tuple(float(c) for c in diffuse_str.split(","))[:3]
    if len(rgb) == 3:
        light_data.color = rgb

    light_data.energy = multiplier * LIGHT_ENERGY_SCALE
    light_data.shadow_soft_size = max(radius * 0.05, 0.1)

    if light_type == 'SPOT':
        light_data.spot_size = math.radians(min(fov, 180.0))

    _link_to_collection(light_obj, lights_collection)
    if parent_obj is not None:
        light_obj.parent = parent_obj
    _apply_local_transform(light_obj, parsed)

    id_map[parsed.id] = light_obj
    report.add_imported(f"Light/{parsed.name}")
    return light_obj


_HANDLERS = {
    "Brush": lambda parsed, parent, basedir, geo, lights, ids, rep:
        _handle_geometry(parsed, parent, basedir, geo, ids, rep),
    "GeomEntity": lambda parsed, parent, basedir, geo, lights, ids, rep:
        _handle_geometry(parsed, parent, basedir, geo, ids, rep),
    "Group": _handle_group,
}


def _dispatch_object(parsed, parent_obj, basedir, geom_collection, lights_collection, id_map, report):
    handler = _HANDLERS.get(parsed.type)
    if handler is not None:
        return handler(parsed, parent_obj, basedir, geom_collection, lights_collection, id_map, report)

    if parsed.type == "Entity":
        if parsed.entity_class in _LIGHT_ENTITY_CLASSES:
            return _handle_entity_light(parsed, parent_obj, basedir,
                                        geom_collection, lights_collection, id_map, report)
        if parsed.geometry_path:
            return _handle_geometry(parsed, parent_obj, basedir,
                                    geom_collection, id_map, report)
        report.add_skipped(parsed.name, f"Entity class not supported: {parsed.entity_class}")
        return None

    report.add_skipped(parsed.name, f"Object type not supported: {parsed.type}")
    return None


def _ensure_collection(name, parent_name=None):
    """create_collection returns None when the collection already exists; this
    wrapper guarantees we always return the Collection."""
    coll = collections.create_collection(name, parent_name or "")
    if coll is None:
        coll = bpy.data.collections[name]
    return coll


def import_prefab_library(xml_path, basedir, report):
    """Top-level entry: parse a PrefabsLibrary XML and import every <Prefab>
    into its own collection under a library-named root collection. Each prefab
    gets a 'Lights' sub-collection.

    Returns the library name on success, None if parsing failed.
    """
    if not os.path.isfile(xml_path):
        report.add_warning(f"Prefab file not found: {xml_path}")
        return None

    try:
        library_name, parsed_prefabs = parse_prefabs_library(xml_path)
    except Exception as e:
        report.add_warning(f"Prefab XML parse failed: {e}")
        return None

    root_coll = _ensure_collection(library_name)
    scene_root = bpy.context.scene.collection
    if library_name not in [c.name for c in scene_root.children]:
        scene_root.children.link(root_coll)

    for prefab in parsed_prefabs:
        if not prefab.objects:
            # Empty prefab stub (e.g. mechlab_entirety in mechlab.xml); create
            # an empty collection so the user sees it exists.
            _ensure_collection(prefab.name, library_name)
            report.add_warning(f"Prefab '{prefab.name}' has no objects")
            continue

        prefab_coll = _ensure_collection(prefab.name, library_name)
        lights_coll = _ensure_collection(f"{prefab.name} Lights", prefab.name)

        id_map = {}
        for obj in prefab.objects:
            _dispatch_object(obj, None, basedir, prefab_coll, lights_coll, id_map, report)

    return library_name

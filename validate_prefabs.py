"""Validate prefabs.py parsing on a real PrefabsLibrary file.

Walks every <Prefab>, every <Object>, and reports counts by type/entity_class
plus any obvious problems (missing geometry path, missing USD file).

Usage:
    python validate_prefabs.py [prefab_xml] [game_root]
Defaults: prefab_xml=D:/depot/mwo/Prefabs/mechlab.xml, game_root=D:/depot/mwo
"""

import importlib.util
import os
import sys
import types
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def _load(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Stub Blender-only modules so prefabs.py imports cleanly outside Blender.
sys.modules.setdefault("bpy", types.ModuleType("bpy"))
sys.modules.setdefault("mathutils", types.ModuleType("mathutils"))

# Stub the package + CryXmlB subpackage so prefabs.py's relative import works
# and io_cryengine_importer/__init__.py (which imports bpy) is bypassed.
pkg = types.ModuleType("io_cryengine_importer")
pkg.__path__ = [os.path.join(HERE, "io_cryengine_importer")]
sys.modules["io_cryengine_importer"] = pkg

cryxml_pkg = types.ModuleType("io_cryengine_importer.CryXmlB")
cryxml_pkg.__path__ = [os.path.join(HERE, "io_cryengine_importer", "CryXmlB")]
sys.modules["io_cryengine_importer.CryXmlB"] = cryxml_pkg

_load("io_cryengine_importer.CryXmlB.CryXmlReader",
      os.path.join(HERE, "io_cryengine_importer", "CryXmlB", "CryXmlReader.py"))

# Stub the .collections and .utilities modules (prefabs.py imports them at top
# but only uses them in the Blender-side functions, which we don't call here).
for stub in ("collections", "utilities"):
    sys.modules[f"io_cryengine_importer.{stub}"] = types.ModuleType(f"io_cryengine_importer.{stub}")

prefabs = _load("io_cryengine_importer.prefabs",
                os.path.join(HERE, "io_cryengine_importer", "prefabs.py"))


def walk(parsed_obj):
    """Yield (parsed_obj, depth) for parsed_obj and all nested Group children."""
    yield (parsed_obj, 0)
    stack = [(c, 1) for c in parsed_obj.children]
    while stack:
        node, depth = stack.pop()
        yield (node, depth)
        for child in node.children:
            stack.append((child, depth + 1))


def main():
    xml_path = sys.argv[1] if len(sys.argv) > 1 else r"D:\depot\mwo\Prefabs\mechlab.xml"
    game_root = sys.argv[2] if len(sys.argv) > 2 else r"D:\depot\mwo"

    if not os.path.isfile(xml_path):
        print(f"Not found: {xml_path}")
        return 1

    library_name, parsed_prefabs = prefabs.parse_prefabs_library(xml_path)
    print(f"Library: {library_name}")
    print(f"Prefabs: {len(parsed_prefabs)}")

    grand_type_counts = Counter()
    grand_entity_classes = Counter()
    grand_geometry = []
    grand_missing_geom = []
    grand_missing_usd = []

    for prefab in parsed_prefabs:
        type_counts = Counter()
        entity_classes = Counter()
        for top in prefab.objects:
            for obj, _depth in walk(top):
                type_counts[obj.type] += 1
                if obj.type == "Entity":
                    entity_classes[obj.entity_class or "<none>"] += 1
                if obj.geometry_path:
                    grand_geometry.append(obj.geometry_path)
                    usd = prefabs._resolve_usda_path(game_root, obj.geometry_path)
                    if usd and not os.path.isfile(usd):
                        grand_missing_usd.append((obj.name, usd))
                elif obj.type in ("Brush", "GeomEntity"):
                    grand_missing_geom.append((obj.type, obj.name))

        grand_type_counts.update(type_counts)
        grand_entity_classes.update(entity_classes)

        print(f"\n  Prefab: {prefab.name!r}  objects(top)={len(prefab.objects)}  recursive={sum(type_counts.values())}")
        for typ, count in type_counts.most_common():
            print(f"      {typ:14s} {count}")
        if entity_classes:
            print(f"      EntityClass breakdown:")
            for cls, count in entity_classes.most_common():
                print(f"        {cls:24s} {count}")

    print(f"\n--- Library totals ---")
    for typ, count in grand_type_counts.most_common():
        print(f"  {typ:14s} {count}")
    print(f"\nUnique geometry paths referenced: {len(set(grand_geometry))}")
    print(f"Brush/GeomEntity missing geometry attribute: {len(grand_missing_geom)}")
    print(f"Geometry paths with no .usda on disk: {len(grand_missing_usd)}")

    if grand_missing_usd:
        print(f"\nFirst 10 missing USDs:")
        for name, path in grand_missing_usd[:10]:
            print(f"  {name}  ->  {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

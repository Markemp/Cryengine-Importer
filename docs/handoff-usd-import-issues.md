# Handoff: USD Import Core — Open Issues

## Context
We're on branch `feature/usd-import-core` (off `release/4.0`) upgrading the Cryengine Importer Blender addon from Collada to USD for Blender 5.0+. The core USD import swap is done and committed. The mech import (adder) runs end-to-end — armature imports, components import, materials create, custom bone shapes apply. The AssetImporter operator has been restored for single-file USD imports (tested with KCD2 hen_brown model).

## What Was Done
- All `bpy.ops.wm.collada_import()` replaced with `bpy.ops.wm.usd_import()`
- `.dae` → `.usda` throughout
- `bpy.data.objects['Armature']` → `bones.find_armature_in_objects()` (finds by `obj.type == 'ARMATURE'`)
- New object tracking via set diff (`objects_before`/`objects_after`) instead of `bpy.context.selected_objects`
- Fixed Blender 5.0 deprecations: `show_axes`, `ShaderNodeSeparateRGB/CombineRGB/MixRGB`
- **USD hierarchy cleanup**: `utilities.cleanup_usd_import()` deletes all EMPTY objects (root, _materials, Armature/SkelRoot) after each USD import. Component imports also delete redundant per-component skeletons.
- **AssetImporter restored**: Simple single-file `.usda` import operator using native USD materials (no `.mtl` pipeline). Registered in File > Import menu.
- `import_asset()` simplified — USD handles materials natively via `import_usd_preview=True`

## Resolved Issues

### Issue 1: Orphan `_materials` empties — FIXED
`utilities.cleanup_usd_import()` removes all EMPTY objects after each USD import, including `_materials` scope nodes.

### Issue 3: Orphan `root` objects — FIXED
Same cleanup function handles `root` Xform containers. Component imports also delete the redundant per-component `Skeleton` (armature). Mesh objects are explicitly moved to the Mech collection.

## Open Issues

### Issue 2: Mech component positioning/orientation is wrong
Components are offset and rotated incorrectly. The CDF file specifies world-space position and rotation for each component (confirmed — toe at z=0.599m matches visual origin).

**What we know:**
- CDF transforms ARE needed — they specify correct world-space positions and rotations
- Removing CDF transforms entirely makes positioning worse (components explode outward)
- The original `matrix_world` approach (parent to bone, then set matrix_world from CDF) worked with Collada but not USD
- Likely cause: after deleting USD hierarchy empties and component skeleton, the mesh has residual transforms that weren't present with Collada imports
- Current code attempts to clear residual transforms with `matrix_world = Identity(4)` before parenting — untested

**Approaches tried:**
1. Remove CDF transform entirely → worse, components explode out
2. Apply CDF rotation/location first, then parent to bone (no matrix_parent_inverse) → components all over the place
3. Apply CDF rotation/location first, then parent with matrix_parent_inverse → same issue as original
4. Clear to identity, then parent + matrix_world → untested (current state of code)

**Investigation ideas:**
- Compare a single component's transform state after USD import vs after Collada import (use Blender MCP to inspect)
- Try parenting to bone BEFORE deleting USD hierarchy (preserve original transform context)
- Check if the component skeleton deletion is stripping transform info the mesh needs
- The mesh may need its armature modifier removed (from USD skinning) before rigid bone parenting works correctly

## Key Files
- `io_cryengine_importer/Cryengine_Importer.py` — `import_mech_geometry()`, `import_geometry()`, `import_asset()`
- `io_cryengine_importer/bones.py` — `import_armature()`, `find_armature_in_objects()`
- `io_cryengine_importer/utilities.py` — `cleanup_usd_import()`
- `io_cryengine_importer/__init__.py` — `AssetImporter`, `MechImporter`, `PrefabImporter` operators

## Test Data
- Adder mech: `d:\depot\mwo\Objects\mechs\adder\adder.cdf`
- Hen model (asset import): `d:\depot\KCD2\objects\characters\animals\hen\hen_brown.usda`
- Hen animations: `d:\depot\KCD2\objects\characters\animals\hen\hen_brown_anim_*.usda`

## What's Next
1. Fix mech component positioning (Issue 2)
2. Animation import — new `animations.py` module
3. Material strategy refinement (native USD vs MTL override for special shaders)

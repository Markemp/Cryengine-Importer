# Handoff: USD Import Core — Open Issues

## Context
We're on branch `feature/usd-import-core` (off `release/4.0`) upgrading the Cryengine Importer Blender addon from Collada to USD for Blender 5.0+. The core USD import swap is done and committed. The mech import (adder) runs end-to-end now — armature imports, components import, materials create, custom bone shapes apply. But there are cleanup issues from how USD import differs from Collada import.

## What Was Done
- All `bpy.ops.wm.collada_import()` replaced with `bpy.ops.wm.usd_import()`
- `.dae` → `.usda` throughout
- `bpy.data.objects['Armature']` → `bones.find_armature_in_objects()` (finds by `obj.type == 'ARMATURE'`)
- New object tracking via set diff (`objects_before`/`objects_after`) instead of `bpy.context.selected_objects`
- Fixed Blender 5.0 deprecations: `show_axes`, `ShaderNodeSeparateRGB/CombineRGB/MixRGB`
- 3 commits on branch so far

## Known Issues To Fix

### Issue 1: Orphan `_materials` empties polluting the scene
Each USD import creates a hierarchy: `root` → `Armature` (empty/SkelRoot) → `Skeleton` (armature) + mesh, plus `root` → `_materials` (empty). The `_materials` empty is a USD scope node — it's the container for material definitions in the USDA file. Blender imports it as an empty object. Since we import ~30+ components, we get `_materials`, `_materials.001`, ..., `_materials.035`, etc.

**Fix needed:** After each component import, delete the `_materials` empty from the newly imported objects. In `import_mech_geometry()` and `import_geometry()`, filter the `new_objects` set and delete any empties named `_materials*`. Or more broadly, delete ALL empties from the USD import since we only want the mesh geometry from component imports.

### Issue 2: Component positioning/orientation is wrong
Feet and legs are pointing backwards. Components are parented to the skeleton and influenced by bones, but they're offset. This is likely because:

- **Collada import** created objects already positioned at the bone locations with correct orientation. The old code then applied additional transforms from the CDF file (rotation, position) on top.
- **USD import** brings in geometry with its own transform hierarchy (the `root` → `Armature` → mesh nesting). The geometry may already be in the correct world-space position from the USD file, but then the CDF transforms are being applied on top, causing double-transformation.

**Investigation needed:**
1. Check `import_mech_geometry()` in `Cryengine_Importer.py` around lines 420-470 where it applies rotation/position from CDF attribs
2. The USD components may already be in their correct positions relative to the skeleton. If so, the CDF transform application may need to be skipped or adjusted.
3. Compare: import a single component USDA manually in Blender and check its position vs what the addon produces.
4. Key code path: after import, the code does `bones.obj_to_bone()` and applies quaternion rotation + position offset from CDF. This was needed for Collada but may not be for USD.

### Issue 3: Orphan `root` objects polluting the scene
Each USD import creates a `root` Xform container (empty). With 30+ component imports, we get `root`, `root.001`, ..., `root.124`. These are the USD scene graph root nodes imported as Blender empties.

**Fix needed:** Same approach as Issue 1 — after each component import, identify and delete the `root` empty from `new_objects`. We only want the mesh (and possibly armature) objects, not the USD hierarchy containers.

### Broader Cleanup Strategy
The pattern for both Issue 1 and 3 is the same: USD import creates a hierarchy of empties + the actual data objects. For component imports (not the main armature import), we should:
1. Import USD file
2. From `new_objects`, extract only the MESH objects we care about
3. Delete all EMPTYs (root, _materials, Armature/SkelRoot containers)
4. Return only the mesh objects for further processing

This could be a helper function like `import_usd_mesh_only()` that wraps the import + cleanup.

## Key Files
- `io_cryengine_importer/Cryengine_Importer.py` — main import logic, `import_mech_geometry()` ~line 380, `import_geometry()` ~line 370
- `io_cryengine_importer/bones.py` — `import_armature()`, `find_armature_in_objects()`
- `io_cryengine_importer/materials.py` — material node creation (deprecated nodes already fixed)
- `docs/v4.0-upgrade-plan.md` — full upgrade plan with verified findings

## Test Data
- Adder mech: `d:\depot\mwo\Objects\mechs\adder\adder.cdf`
- Body dir with USDA components: `d:\depot\mwo\Objects\mechs\adder\body\`
- 55 animation files: `d:\depot\mwo\Objects\mechs\adder\body\adder_anim_*.usda`

## What's Next After These Fixes
1. Finish cleaning up USD import issues (this doc)
2. Merge `feature/usd-import-core` into `release/4.0`
3. Branch `feature/restore-asset-importer` — bring back AssetImporter operator
4. Branch `feature/animation-import` — new `animations.py` module for importing animation USDs
5. Branch `feature/usd-materials` — material strategy (native USD vs MTL override)

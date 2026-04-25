# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cryengine Importer is a Blender Add-on (Python) that imports Cryengine game assets converted to Collada format. It supports Blender 4.0+. The addon provides three main importers:

1. **Cryengine Asset Importer** - Converts directories of Cryengine assets (converted with Cryengine Converter) into Blender files with custom Cycles node materials
2. **Mech Importer** - Imports MechWarrior Online mechs with full armature rigging and animation support
3. **Cryengine Prefab Importer** - Imports Cryengine Prefab XML files (not yet fully implemented)

## Development Commands

### Deployment
Deploy the addon to Blender using PowerShell:
```powershell
.\Deploy-Addon.ps1 -BlenderVersion "4.0"
```

This script:
- Creates a zip file of `io_cryengine_importer` directory
- Extracts it to `%APPDATA%\Blender Foundation\Blender\{version}\scripts\addons`
- Use `-Force` flag to override version checks

### Testing
Run unit tests:
```bash
python test_cryxmlreader.py
```

## Code Architecture

### Module Structure

The addon is organized in the `io_cryengine_importer` directory:

- **`__init__.py`** - Blender addon registration, defines operator classes (`MechImporter`, `PrefabImporter`, `MessageOperator`)
- **`Cryengine_Importer.py`** - Main import logic with `import_mech()` and `import_prefab()` functions
- **`materials.py`** - Material creation from Cryengine material XML files, shader node setup for different material types
- **`bones.py`** - Armature import, IK bone creation, bone collection management
- **`collections.py`** - Blender collection hierarchy setup (Mech, Widgets, Empties, Weapons, etc.)
- **`utilities.py`** - Helper functions for coordinate conversions, color parsing, file path handling
- **`constants.py`** - Global constants including collection names, weapon keywords, control bone names
- **`widgets.py`** - Custom bone widget creation for animation controls
- **`CryXmlB/CryXmlReader.py`** - Binary CryXML parser that handles both binary and text XML formats

### Key Workflows

**Mech Import Process** (see `Cryengine_Importer.py`):
1. Parse `.cdf` character definition file
2. Set up collection hierarchy via `collections.set_up_collections()`
3. Import armature from `.chr` file using `bones.import_armature()`
4. Import body parts from directory
5. Create IK bones if `add_control_bones` enabled via `create_IKs()`
6. Set up bone collections and colors via `bones.set_bone_collections()`
7. Process materials from `.mtl` files using `materials.create_materials()`
8. Auto-save if enabled

**Material Creation** (see `materials.py`):
- Reads Cryengine `.mtl` XML files (binary or text format via `CryXmlReader`)
- Creates Blender materials with node trees
- Supports shader types: Nodraw, MechCockpit, Mech, Illum, Glass
- Handles texture maps: Diffuse, Specular, Normal, Height
- Configurable for DDS or TIF texture formats

**Bone System** (see `bones.py`):
- Two bone collections: "Control Bones" (visible, THEME02 color) and "Deform Bones" (hidden, THEME09 color)
- Control bones include IK targets for hands, feet, knees, elbows, shoulders
- Root bone is `Bip01` per `constants.ROOT_NAME`
- Special handling for chicken-walker vs regular knee configurations

### Important Patterns

**Base Directory Resolution**: The `get_base_dir()` function recursively walks up from file path until it finds a directory named "objects" or "prefabs" - this is the game asset root. Only import single directories (non-recursive) to prevent loading thousands of objects.

**CryXML Handling**: The `CryXmlSerializer` auto-detects binary vs text XML by checking first byte. Binary format uses offset tables for nodes, references, and data.

**Error Reporting**: Use `MessageOperator` (id: "wm.display_message") to display errors/warnings to users via `bpy.ops.wm.display_message(message=..., severity=...)`.

**Texture Path Construction**: Textures are resolved using `utilities.get_filename()` which joins `constants.basedir` with the relative path from material XML and swaps extension to `.dds` or `.tif`.

**Collection Organization**: All imported objects go into hierarchical collections. Mechs use: Mech → [Widgets, Empties, Weapons, Damaged Parts, Variants]. Each variant (from `.mdf` files) gets its own sub-collection.

## Important Constraints

- Only supports Blender 2.80+ (current version targets 4.0+)
- Assets must be pre-converted to Collada (.dae) using Cryengine Converter
- Single-directory imports only (not recursive)
- Must import from paths under "Objects" or "Prefabs" directories
- Texture files must exist on disk (DDS or TIF formats)
- Addon uses GPL v2 license

## Code Conventions

- Uses Blender Python API (`bpy`)
- PEP8 compliant
- Edit mode operations require explicit mode switching via `bpy.ops.object.mode_set(mode='EDIT')`
- Material nodes use Blender's Principled BSDF shader
- Bone manipulation requires checking/setting active object and mode context

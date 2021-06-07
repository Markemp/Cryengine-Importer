# Cryengine-Importer

**Note:  Blender 2.80 has been released, and has a number of compatibility breaking updates.  This project is being updated to support these new features, as a 2.0 release.  If you would like to continue to use the old versions of Blender with this tool, please use the 1.1 version.  The latest release will only be supported for Blender 2.80 and newer.**

Cryengine Importer is a Blender Add-on tool that allows you to import Cryengine game assets converted to the Collada format using the Cryengine Converter program.

There are 3 different components to this tool:
* Cryengine Asset Importer
* Mech Importer
* Cryengine Prefab Importer. (NYI)

### Cryengine Asset Importer

This tool will allow you to convert a directory of assets that have been converted with the Cryengine Converter tool into a Blender file.  This allows for the bulk conversion of Cryengine game assets into a library that can be used separately, or with the Cryengine Prefab Importer to create scenes for your machinima.  The importer creates custom node layout groups in the Cycles engine to allow for realistic rendering.

Tutorial video:  pending

### Mech Importer

This tool allows you to import MechWarrior Online mechs into Blender, along with their armature, fully rigged and ready for animation.  By using the MWO Camo .blend file (courtesy of Andreas80) that is included in the release, you can even apply custom camo patterns and colors to the mechs!

Tutorial video:  pending

### Cryengine Prefab Importer (NEW!)

This tool was created to help import Cryengine Prefabs (located in the /Prefabs directory) into Blender.  It grabs the prefab XML file and locates the relevant asset converted with Asset Importer, and places it at the appropriate location in the scene with custom made Cycles materials.  It takes advantage of Blender's linked assets, so that if you need to update a particular asset in the scene, you can change it in the source .blend file and it will automatically be applied to any Prefab or scene that references it.

Tutorial video:  pending

## Installation

* Download the Cryengine Importer package from [Heffay Presents](https://www.heffaypresents.com/GitHub) or from the [Release tab](https://github.com/Markemp/Cryengine-Importer/releases/latest) on GitHub.
* In Blender, go to Edit -> Preferences, then click on the "Install" button on the bottom.
* Locate the io_cryengine_importer.zip file you downloaded and select the "Install Add-on" button.
* Back on the Add-ons tab, click on the Community tab, find "Import-Export: Cryengine Importer" entry and enable it.

## Usage

Watch the tutorial videos!  There are important caveats that you need to consider as you import assets into your scene.  If you don't pay attention to what you are doing, there is a good chance that you may overwrite some of the work you've done.

Thank you for using this tool, and please use the [Issues tab](https://github.com/Markemp/Cryengine-Importer/issues) at GitHub to report any issues that you may have with the Importer.  Thanks!

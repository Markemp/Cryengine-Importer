import unittest
import tempfile
import os
import shutil
import sys
from unittest.mock import MagicMock

# Mock Blender modules so we can import animations without Blender
bpy_mock = MagicMock()
# Ensure bpy.types classes can be used as base classes without metaclass conflicts
bpy_mock.types.Operator = type("Operator", (), {})
bpy_mock.types.Panel = type("Panel", (), {})
sys.modules["bpy"] = bpy_mock
sys.modules["bpy.types"] = bpy_mock.types
sys.modules["bpy.utils"] = bpy_mock.utils
sys.modules["bpy.props"] = MagicMock()
bpy_extras_mock = MagicMock()
bpy_extras_mock.io_utils.ImportHelper = type("ImportHelper", (), {})
bpy_extras_mock.io_utils.orientation_helper = lambda **kw: lambda cls: cls
sys.modules["bpy_extras"] = bpy_extras_mock
sys.modules["bpy_extras.io_utils"] = bpy_extras_mock.io_utils
sys.modules["mathutils"] = MagicMock()
sys.modules["rna_prop_ui"] = MagicMock()


class TestGetSkeletonNameFromChrparams(unittest.TestCase):
    def test_returns_filename_stem(self):
        from io_cryengine_importer.animations import get_skeleton_name_from_chrparams
        path = r"D:\depot\Game\Objects\characters\skeleton_player.chrparams"
        self.assertEqual(get_skeleton_name_from_chrparams(path), "skeleton_player")

    def test_handles_nested_path(self):
        from io_cryengine_importer.animations import get_skeleton_name_from_chrparams
        path = r"D:\depot\Game\Objects\chars\human\generic\skeleton_player_generic.chrparams"
        self.assertEqual(get_skeleton_name_from_chrparams(path), "skeleton_player_generic")


class TestParseChrparams(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_xml(self, relative_path, content):
        full_path = os.path.join(self.test_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        return full_path

    def test_simple_chrparams_no_animations(self):
        """A chrparams with only IK_Definition and no AnimationList."""
        from io_cryengine_importer.animations import parse_chrparams
        path = self._write_xml("Objects/chars/skeleton.chrparams", """<?xml version="1.0" ?>
<Params>
    <IK_Definition/>
</Params>""")
        result = parse_chrparams(path, self.test_dir)
        self.assertEqual(result["filepath"], None)
        self.assertEqual(result["patterns"], [])

    def test_chrparams_with_filepath_and_patterns(self):
        """A chrparams with #filepath and wildcard patterns."""
        from io_cryengine_importer.animations import parse_chrparams
        path = self._write_xml("animations/human/player.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="#filepath" path="animations/human/male"/>
        <Animation name="*" path="*/*.caf"/>
        <Animation name="*" path="*/*.bspace"/>
    </AnimationList>
</Params>""")
        result = parse_chrparams(path, self.test_dir)
        self.assertEqual(result["filepath"], "animations/human/male")
        self.assertEqual(result["patterns"], ["*/*.caf", "*/*.bspace"])

    def test_chrparams_with_include(self):
        """A chrparams that $Includes another chrparams file."""
        from io_cryengine_importer.animations import parse_chrparams
        self._write_xml("animations/human/male/player.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="#filepath" path="animations/human/male"/>
        <Animation name="*" path="*/*.caf"/>
    </AnimationList>
</Params>""")
        root_path = self._write_xml("Objects/chars/skeleton.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="$AnimEventDatabase" path="animations/human/male/events.animevents"/>
        <Animation name="$Include" path="animations/human/male/player.chrparams"/>
        <Animation name="$facelib" path="Objects/chars/skeleton.fxl"/>
    </AnimationList>
</Params>""")
        result = parse_chrparams(root_path, self.test_dir)
        self.assertEqual(result["filepath"], "animations/human/male")
        self.assertEqual(result["patterns"], ["*/*.caf"])

    def test_include_missing_file_skipped_gracefully(self):
        """An $Include pointing to a nonexistent file should not crash."""
        from io_cryengine_importer.animations import parse_chrparams
        path = self._write_xml("Objects/chars/skeleton.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="$Include" path="animations/nonexistent.chrparams"/>
        <Animation name="#filepath" path="animations/human"/>
        <Animation name="*" path="*.caf"/>
    </AnimationList>
</Params>""")
        result = parse_chrparams(path, self.test_dir)
        self.assertEqual(result["filepath"], "animations/human")
        self.assertEqual(result["patterns"], ["*.caf"])

    def test_depth_limit_prevents_infinite_recursion(self):
        """Circular includes should be stopped by the depth limit."""
        from io_cryengine_importer.animations import parse_chrparams
        # File A includes File B, File B includes File A
        self._write_xml("a.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="$Include" path="b.chrparams"/>
    </AnimationList>
</Params>""")
        self._write_xml("b.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="$Include" path="a.chrparams"/>
    </AnimationList>
</Params>""")
        path_a = os.path.join(self.test_dir, "a.chrparams")
        # Should not raise, just stop recursing
        result = parse_chrparams(path_a, self.test_dir)
        self.assertIsInstance(result, dict)

    def test_special_names_are_skipped(self):
        """$AnimEventDatabase, $TracksDatabase, $facelib should not appear in patterns."""
        from io_cryengine_importer.animations import parse_chrparams
        path = self._write_xml("skeleton.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="$AnimEventDatabase" path="events.animevents"/>
        <Animation name="$TracksDatabase" path="animations/*.dba"/>
        <Animation name="$facelib" path="skeleton.fxl"/>
        <Animation name="*" path="*.caf"/>
    </AnimationList>
</Params>""")
        result = parse_chrparams(path, self.test_dir)
        self.assertEqual(result["patterns"], ["*.caf"])

    def test_multiple_includes_merged(self):
        """Multiple $Include directives should all be followed."""
        from io_cryengine_importer.animations import parse_chrparams
        self._write_xml("inc1.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="#filepath" path="animations/set1"/>
        <Animation name="*" path="*.caf"/>
    </AnimationList>
</Params>""")
        self._write_xml("inc2.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="*" path="*.bspace"/>
    </AnimationList>
</Params>""")
        root_path = self._write_xml("root.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="$Include" path="inc1.chrparams"/>
        <Animation name="$Include" path="inc2.chrparams"/>
    </AnimationList>
</Params>""")
        result = parse_chrparams(root_path, self.test_dir)
        self.assertEqual(result["filepath"], "animations/set1")
        self.assertIn("*.caf", result["patterns"])
        self.assertIn("*.bspace", result["patterns"])


class TestDiscoverAnimationsFromChrparams(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_xml(self, relative_path, content):
        full_path = os.path.join(self.test_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        return full_path

    def _touch(self, relative_path):
        full_path = os.path.join(self.test_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write("")
        return full_path

    def test_discovers_usda_files_in_skeleton_directory(self):
        """Should find animation USDs alongside the chrparams file."""
        from io_cryengine_importer.animations import discover_animations_from_chrparams
        chrparams = self._write_xml("Objects/chars/skeleton.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="$Include" path="animations/player.chrparams"/>
    </AnimationList>
</Params>""")
        self._write_xml("animations/player.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="#filepath" path="animations"/>
        <Animation name="*" path="*.caf"/>
    </AnimationList>
</Params>""")
        # Create USDA animation files alongside the chrparams
        skeleton_dir = os.path.dirname(chrparams)
        self._touch("Objects/chars/skeleton_anim_idle.usda")
        self._touch("Objects/chars/skeleton_anim_run.usda")
        self._touch("Objects/chars/skeleton.usda")  # Not an anim file

        files = discover_animations_from_chrparams(chrparams, self.test_dir, "skeleton")
        self.assertEqual(len(files), 2)
        basenames = [os.path.basename(f) for f in files]
        self.assertIn("skeleton_anim_idle.usda", basenames)
        self.assertIn("skeleton_anim_run.usda", basenames)

    def test_discovers_usda_in_resolved_animation_directory(self):
        """Should also search in the resolved #filepath directory."""
        from io_cryengine_importer.animations import discover_animations_from_chrparams
        chrparams = self._write_xml("Objects/chars/skeleton.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="#filepath" path="animations/human"/>
        <Animation name="*" path="*.caf"/>
    </AnimationList>
</Params>""")
        # Animations in the resolved filepath dir, not alongside chrparams
        self._touch("animations/human/skeleton_anim_walk.usda")
        self._touch("animations/human/skeleton_anim_jump.usda")

        files = discover_animations_from_chrparams(chrparams, self.test_dir, "skeleton")
        self.assertEqual(len(files), 2)

    def test_no_duplicates_when_same_directory(self):
        """Should not return duplicates if chrparams dir and filepath dir overlap."""
        from io_cryengine_importer.animations import discover_animations_from_chrparams
        chrparams = self._write_xml("animations/skeleton.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="#filepath" path="animations"/>
        <Animation name="*" path="*.caf"/>
    </AnimationList>
</Params>""")
        self._touch("animations/skeleton_anim_idle.usda")

        files = discover_animations_from_chrparams(chrparams, self.test_dir, "skeleton")
        self.assertEqual(len(files), 1)

    def test_returns_empty_when_no_animations_found(self):
        """Should return empty list when no matching USDA files exist."""
        from io_cryengine_importer.animations import discover_animations_from_chrparams
        chrparams = self._write_xml("Objects/chars/skeleton.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="#filepath" path="animations"/>
    </AnimationList>
</Params>""")
        files = discover_animations_from_chrparams(chrparams, self.test_dir, "skeleton")
        self.assertEqual(files, [])


class TestDiscoverAssetAnimations(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        # Structure: test_dir/Objects/chars/ is the asset dir
        # test_dir is the game root (parent of Objects)
        self.objects_dir = os.path.join(self.test_dir, "Objects", "chars")
        os.makedirs(self.objects_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _write_file(self, relative_path, content=""):
        full_path = os.path.join(self.test_dir, relative_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)
        return full_path

    def test_discovers_via_chrparams(self):
        """Should find animations when chrparams exists alongside the asset."""
        from unittest.mock import patch
        from io_cryengine_importer.Cryengine_Importer import discover_asset_animations

        # Create the chrparams and animation files
        self._write_file("Objects/chars/skeleton.chrparams", """<?xml version="1.0" ?>
<Params>
    <AnimationList>
        <Animation name="#filepath" path="animations"/>
        <Animation name="*" path="*.caf"/>
    </AnimationList>
</Params>""")
        self._write_file("Objects/chars/skeleton_anim_idle.usda")
        self._write_file("Objects/chars/skeleton_anim_run.usda")
        asset_path = os.path.join(self.objects_dir, "skeleton.usda")
        self._write_file("Objects/chars/skeleton.usda")

        mock_armature = MagicMock()
        with patch("io_cryengine_importer.bones.find_armature_in_objects",
                   return_value=mock_armature):
            anim_files, armature = discover_asset_animations(asset_path)

        self.assertEqual(len(anim_files), 2)
        self.assertIs(armature, mock_armature)

    def test_returns_empty_when_no_armature(self):
        """Should return empty list when no armature is found."""
        from unittest.mock import patch
        from io_cryengine_importer.Cryengine_Importer import discover_asset_animations

        self._write_file("Objects/chars/skeleton.chrparams", """<?xml version="1.0" ?>
<Params><AnimationList/></Params>""")
        asset_path = os.path.join(self.objects_dir, "skeleton.usda")
        self._write_file("Objects/chars/skeleton.usda")

        with patch("io_cryengine_importer.bones.find_armature_in_objects",
                   return_value=None):
            anim_files, armature = discover_asset_animations(asset_path)

        self.assertEqual(anim_files, [])
        self.assertIsNone(armature)

    def test_returns_empty_when_no_cdf_or_chrparams(self):
        """Should return empty when neither CDF nor chrparams exists."""
        from unittest.mock import patch
        from io_cryengine_importer.Cryengine_Importer import discover_asset_animations

        asset_path = os.path.join(self.objects_dir, "skeleton.usda")
        self._write_file("Objects/chars/skeleton.usda")

        mock_armature = MagicMock()
        with patch("io_cryengine_importer.bones.find_armature_in_objects",
                   return_value=mock_armature):
            anim_files, armature = discover_asset_animations(asset_path)

        self.assertEqual(anim_files, [])


if __name__ == "__main__":
    unittest.main()

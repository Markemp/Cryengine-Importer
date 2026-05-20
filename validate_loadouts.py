"""Validate loadouts.py resolution against real MWO data.

Walks every variant for a list of test mechs, resolves each variant to
its expected weapon ANames, then verifies each AName exists as an
<Attachment> in the parent mech CDF (i.e. the mech importer would have
already imported it).

Usage:
    python validate_loadouts.py [game_root] [mech1 mech2 ...]
Defaults: game_root=D:/depot/mwo, mechs=adder atlas
"""

import importlib.util
import os
import sys
import types

# Load loadouts.py and CryXmlReader directly so we don't trip on the addon's
# bpy import in io_cryengine_importer/__init__.py.
HERE = os.path.dirname(os.path.abspath(__file__))


def _load(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Stub a minimal package + CryXmlB subpackage so loadouts.py's relative import works.
pkg = types.ModuleType("io_cryengine_importer")
pkg.__path__ = [os.path.join(HERE, "io_cryengine_importer")]
sys.modules["io_cryengine_importer"] = pkg

cryxml_pkg = types.ModuleType("io_cryengine_importer.CryXmlB")
cryxml_pkg.__path__ = [os.path.join(HERE, "io_cryengine_importer", "CryXmlB")]
sys.modules["io_cryengine_importer.CryXmlB"] = cryxml_pkg

_load("io_cryengine_importer.CryXmlB.CryXmlReader",
      os.path.join(HERE, "io_cryengine_importer", "CryXmlB", "CryXmlReader.py"))
loadouts = _load("io_cryengine_importer.loadouts",
                 os.path.join(HERE, "io_cryengine_importer", "loadouts.py"))
CryXmlSerializer = sys.modules["io_cryengine_importer.CryXmlB.CryXmlReader"].CryXmlSerializer


def cdf_attachment_names(cdf_path):
    root = CryXmlSerializer().read_file(cdf_path)
    return {att.attrib["AName"] for att in root.iter("Attachment") if att.attrib.get("AName")}


def report_mech(game_root, mech):
    mech_dir = os.path.join(game_root, "objects", "mechs", mech)
    cdf_path = os.path.join(mech_dir, mech + ".cdf")
    if not os.path.isfile(cdf_path):
        print(f"[{mech}] SKIP — no {cdf_path}")
        return 0, 0, 0

    cdf_anames = cdf_attachment_names(cdf_path)
    variants = sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(mech_dir)
        if f.endswith(".mdf")
    )
    if not variants:
        print(f"[{mech}] no variants")
        return 0, 0, 0

    total_resolved = 0
    total_unresolved = 0
    total_missing = 0

    for variant in variants:
        result = loadouts.resolve_variant(variant, game_root, mech_dir)
        if result is None:
            print(f"  {variant}: SKIP (missing required file)")
            continue

        resolved_count = sum(len(v["attachments"]) for v in result.values())
        unresolved_pairs = [(c, w) for c, v in result.items() for w in v["unresolved"]]
        missing_in_cdf = []
        for comp, v in result.items():
            for aname in v["attachments"]:
                if aname not in cdf_anames:
                    missing_in_cdf.append((comp, aname))

        total_resolved += resolved_count
        total_unresolved += len(unresolved_pairs)
        total_missing += len(missing_in_cdf)

        status = "OK" if not unresolved_pairs and not missing_in_cdf else "ISSUES"
        print(f"  {variant}: {status}  resolved={resolved_count} "
              f"unresolved={len(unresolved_pairs)} missing_in_cdf={len(missing_in_cdf)}")
        for comp, (wid, name) in unresolved_pairs:
            print(f"      UNRESOLVED  {comp}: weapon {wid} ({name})")
        for comp, aname in missing_in_cdf:
            print(f"      NOT IN CDF  {comp}: {aname}")

    return total_resolved, total_unresolved, total_missing


def main():
    game_root = sys.argv[1] if len(sys.argv) > 1 else r"D:\depot\mwo"
    mechs = sys.argv[2:] if len(sys.argv) > 2 else ["adder", "atlas"]

    grand_resolved = grand_unresolved = grand_missing = 0
    for mech in mechs:
        print(f"\n=== {mech} ===")
        r, u, m = report_mech(game_root, mech)
        grand_resolved += r
        grand_unresolved += u
        grand_missing += m

    print(f"\n--- TOTAL ---")
    print(f"resolved      : {grand_resolved}")
    print(f"unresolved    : {grand_unresolved}")
    print(f"missing in CDF: {grand_missing}")
    return 0 if grand_unresolved == 0 and grand_missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

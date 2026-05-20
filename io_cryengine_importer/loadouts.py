"""Resolve per-variant weapon attachments for MWO mechs.

Pure parsers + resolver — no Blender dependencies. Reads the MWO data files
and produces, for a given variant loadout, the set of attachment names
(ANames from the parent CDF) that represent the visible weapons.

Lookup chain:
    Libs/MechLoadout/<variant>.xml         per-component Weapons + OmniPods
    Libs/Items/Weapons/Weapons.xml         ItemID -> name + HardpointAliases
    Libs/Items/OmniPods.xml                OmniPod ItemID -> (chassis, set, component)
    objects/mechs/<m>/<m>-omnipods.xml     per set/component -> Hardpoint IDs   (omnimechs)
    objects/mechs/<m>/<variant>.mdf        per component -> Hardpoint IDs       (battlemechs)
    objects/mechs/<m>/<m>-hardpoints.xml   Hardpoint ID -> ordered WeaponSlots
"""

import os

from .CryXmlB.CryXmlReader import CryXmlSerializer


def _read_xml(path):
    return CryXmlSerializer().read_file(path)


def parse_loadout_file(loadout_path):
    """Return {component_name: {"weapons": [item_id], "omnipod": id_or_None,
                                 "ammo": [item_id], "modules": [item_id]}}."""
    root = _read_xml(loadout_path)
    components = {}
    for comp in root.iter("component"):
        name = comp.attrib.get("Name")
        if not name:
            continue
        entry = {"weapons": [], "omnipod": None, "ammo": [], "modules": []}
        omni = comp.attrib.get("OmniPod")
        if omni:
            entry["omnipod"] = int(omni)
        for child in comp:
            tag = child.tag
            item_id = child.attrib.get("ItemID")
            if not item_id:
                continue
            item_id = int(item_id)
            if tag == "Weapon":
                entry["weapons"].append(item_id)
            elif tag == "Ammo":
                entry["ammo"].append(item_id)
            elif tag == "Module":
                entry["modules"].append(item_id)
        components[name] = entry
    return components


def parse_weapons_db(weapons_path):
    """Return {item_id: {"name": str, "aliases": [str]}}."""
    root = _read_xml(weapons_path)
    out = {}
    for w in root.iter("Weapon"):
        wid = w.attrib.get("id")
        if not wid:
            continue
        aliases = w.attrib.get("HardpointAliases", "")
        out[int(wid)] = {
            "name": w.attrib.get("name", ""),
            "aliases": [a.strip() for a in aliases.split(",") if a.strip()],
        }
    return out


def parse_omnipods_db(omnipods_path):
    """Return {item_id: (chassis, set_name, component)}."""
    root = _read_xml(omnipods_path)
    out = {}
    for pod in root.iter("OmniPod"):
        pid = pod.attrib.get("id")
        if not pid:
            continue
        out[int(pid)] = (
            pod.attrib.get("chassis", ""),
            pod.attrib.get("set", ""),
            pod.attrib.get("component", ""),
        )
    return out


def parse_mech_omnipods(path):
    """Return {set_name: {component_name: [hp_id]}}."""
    if not os.path.isfile(path):
        return {}
    root = _read_xml(path)
    out = {}
    for set_el in root.iter("Set"):
        set_name = set_el.attrib.get("name", "")
        comps = {}
        for comp in set_el.iter("component"):
            cname = comp.attrib.get("name", "")
            hp_ids = []
            for hp in comp.iter("Hardpoint"):
                hpid = hp.attrib.get("ID")
                if hpid:
                    hp_ids.append(int(hpid))
            comps[cname] = hp_ids
        out[set_name] = comps
    return out


def parse_mech_mdf_hardpoints(mdf_path):
    """Return {component_name: {"hardpoints": [hp_id], "omnipod": id_or_None}}.
    Battlemechs use `hardpoints`. OmniMechs may carry per-component `OmniPod`
    defaults used when the variant loadout doesn't specify one explicitly."""
    root = _read_xml(mdf_path)
    out = {}
    for comp in root.iter("Component"):
        name = comp.attrib.get("Name")
        if not name:
            continue
        hp_ids = []
        for hp in comp.iter("Hardpoint"):
            hpid = hp.attrib.get("ID")
            if hpid:
                hp_ids.append(int(hpid))
        omnipod = comp.attrib.get("OmniPod")
        out[name] = {
            "hardpoints": hp_ids,
            "omnipod": int(omnipod) if omnipod else None,
        }
    return out


def parse_mech_hardpoints(path):
    """Return {hp_id: [WeaponSlot]} where WeaponSlot is [(search_alias, AName), ...]
    in document order. Multiple WeaponSlot blocks under the same Hardpoint represent
    distinct mounting points (eh1, eh2, ...) for the same hardpoint type."""
    root = _read_xml(path)
    out = {}
    for hp in root.iter("Hardpoint"):
        hpid = hp.attrib.get("id")
        if not hpid:
            continue
        slots = []
        for ws in hp.iter("WeaponSlot"):
            entries = []
            for att in ws.iter("Attachment"):
                search = att.attrib.get("search", "")
                aname = att.attrib.get("AName", "")
                if search and aname:
                    entries.append((search, aname))
            slots.append(entries)
        out[int(hpid)] = slots
    return out


def _component_hardpoint_ids(component_name, comp_loadout, variant_name,
                              mech_omnipods, mdf_hardpoints, omnipods_db):
    """Resolve which hardpoint IDs apply to a component.

    Resolution order:
      1. Loadout's explicit `<OmniPod ItemID>` -> omnipods_db -> mech_omnipods[set][comp].
      2. MDF component's `OmniPod` default attribute (same lookup).
      3. Variant name matches an omnipod set (`adr-a` -> `<Set name="adr-a">`).
      4. MDF component's `<Hardpoint>` entries (battlemech path).
    """
    def _from_pod(pid):
        if pid is None or pid not in omnipods_db:
            return None
        _chassis, set_name, pod_component = omnipods_db[pid]
        return mech_omnipods.get(set_name, {}).get(pod_component)

    hp_ids = _from_pod(comp_loadout.get("omnipod"))
    if hp_ids is not None:
        return hp_ids

    mdf_entry = mdf_hardpoints.get(component_name, {})
    hp_ids = _from_pod(mdf_entry.get("omnipod"))
    if hp_ids is not None:
        return hp_ids

    if variant_name in mech_omnipods:
        return mech_omnipods[variant_name].get(component_name, [])

    return mdf_entry.get("hardpoints", [])


def _match_weapon_to_slot(weapon_aliases, slot_entries):
    """Walk slot's Attachment list in order, return AName of first whose search
    keyword is in weapon_aliases. None if no match."""
    alias_set = set(weapon_aliases)
    for search, aname in slot_entries:
        if search in alias_set:
            return aname
    return None


def resolve_variant_attachments(variant_name, loadout, weapons_db, omnipods_db,
                                 mech_omnipods, mdf_hardpoints, mech_hardpoints):
    """Given a parsed loadout and all DBs, return:
        {component_name: {
            "attachments": [AName, ...],     # resolved weapon ANames
            "unresolved": [(item_id, name)], # weapons we couldn't place
        }}
    Slot consumption: weapons in loadout order each take the next available
    compatible WeaponSlot from the component's hardpoints (in hardpoint order,
    then slot order within each hardpoint).
    """
    result = {}
    for comp_name, comp in loadout.items():
        attachments = []
        unresolved = []
        if not comp["weapons"]:
            result[comp_name] = {"attachments": attachments, "unresolved": unresolved}
            continue

        hp_ids = _component_hardpoint_ids(comp_name, comp, variant_name,
                                          mech_omnipods, mdf_hardpoints, omnipods_db)

        # Flat ordered list of (hp_id, slot_index, slot_entries) for slot consumption.
        slots = []
        for hp_id in hp_ids:
            for slot_idx, slot_entries in enumerate(mech_hardpoints.get(hp_id, [])):
                slots.append((hp_id, slot_idx, slot_entries))
        consumed = [False] * len(slots)

        for wid in comp["weapons"]:
            wmeta = weapons_db.get(wid)
            if wmeta is None:
                unresolved.append((wid, "<unknown weapon>"))
                continue
            aliases = wmeta["aliases"]
            placed = False
            for i, (_hp, _idx, slot_entries) in enumerate(slots):
                if consumed[i]:
                    continue
                aname = _match_weapon_to_slot(aliases, slot_entries)
                if aname:
                    attachments.append(aname)
                    consumed[i] = True
                    placed = True
                    break
            if not placed:
                unresolved.append((wid, wmeta["name"]))

        result[comp_name] = {"attachments": attachments, "unresolved": unresolved}
    return result


def resolve_variant(variant_name, basedir, mech_dir):
    """Convenience: resolve a single variant by name (e.g. "adr-a"), returning
    the {component: {attachments, unresolved}} dict, or None if any required
    file is missing.

    basedir: game root (parent of `objects/`).
    mech_dir: absolute path to the mech directory containing the .cdf and .mdf files.
    """
    loadout_path = os.path.join(basedir, "Libs", "MechLoadout", variant_name + ".xml")
    weapons_path = os.path.join(basedir, "Libs", "Items", "Weapons", "Weapons.xml")
    omnipods_db_path = os.path.join(basedir, "Libs", "Items", "OmniPods.xml")
    mech_omnipods_path = os.path.join(mech_dir, os.path.basename(mech_dir) + "-omnipods.xml")
    mech_hardpoints_path = os.path.join(mech_dir, os.path.basename(mech_dir) + "-hardpoints.xml")
    mdf_path = os.path.join(mech_dir, variant_name + ".mdf")

    for required in (loadout_path, weapons_path, omnipods_db_path, mech_hardpoints_path, mdf_path):
        if not os.path.isfile(required):
            return None

    loadout = parse_loadout_file(loadout_path)
    weapons_db = parse_weapons_db(weapons_path)
    omnipods_db = parse_omnipods_db(omnipods_db_path)
    mech_omnipods = parse_mech_omnipods(mech_omnipods_path)
    mdf_hardpoints = parse_mech_mdf_hardpoints(mdf_path)
    mech_hardpoints = parse_mech_hardpoints(mech_hardpoints_path)

    return resolve_variant_attachments(
        variant_name, loadout, weapons_db, omnipods_db,
        mech_omnipods, mdf_hardpoints, mech_hardpoints,
    )

import array
import glob
import math
import os
import os.path
import time
import types
import xml.etree as etree
import xml.etree.ElementTree as ET
from math import radians

schema = "{http://www.collada.org/2005/11/COLLADASchema}"

dir_path = os.path.dirname(os.path.realpath(__file__))
dir_path2 = os.getcwd()

mech_list = GetAllMechNames()
print("Found " + str(len(mech_list)) + " mechs.")

for mech in mech_list:
    bone_count = CountBonesBetweenShoulderAndHand(mech)
    print(mech + ": Found " + bone_count + " between shoulder and hand bone.")

adder_geo = GetElementTreeByMechName("adder")
geometry = ET.parse(adder_geo)

root = geometry.getroot()
print(root.tag)
print(root.attrib)

for geo in geometry.iter(schema + "visual_scene"):
    print(geo.attrib["id"])
    print(geo.tag)

for node in geometry.iter(schema + "node"):
    print(node.attrib["id"])


def GetLeftShoulderNode(element):
    for node in element.iter(schema + "node"):
        if node.attrib["name"] == "Bip01_L_Clavicle":
            print(node.attrib["name"])
            return node


def GetElementTreeByMechName(name):
    source = "d:\\depot\\mwo\\objects\\mechs\\" + name + "\\body\\" + name + ".dae"
    elementTree = ET.parse(source)
    return elementTree


def GetChildNodeByName(element, name):
    for node in element.iter(schema + "node"):
        if node.attrib["name"] == name:
            print("Found " + node.attrib["name"])
            return node
    raise Exception("Unable to find bone " + name)


def GetAllMechNames():
    mech_dir = "d:\\depot\\mwo\\objects\\mechs"
    mech_list = next(os.walk(mech_dir))[1]
    mech_list.remove("_mech_templates")
    mech_list.remove("skins")
    mech_list.remove("generic")
    return mech_list


def GetAllChildBones(element):
    bones = element.findall("node")
    return bones


def CountBonesBetweenShoulderAndHand(mech):
    mech_tree = GetElementTreeByMechName(mech)
    shoulder_bone = GetChildNodeByName(mech_tree, "Bip01_L_Clavicle")
    depth = 0
    count = find_hand_bone(shoulder_bone, depth)
    return count


def find_hand_bone(bone, depth):

    return depth


def GetParentMap(tree):
    parent_map = {c: p for p in tree.iter() for c in p}
    return parent_map

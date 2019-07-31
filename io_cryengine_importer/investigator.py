import array
import glob
import math
import os, os.path
import time
import types
import xml.etree as etree
import xml.etree.ElementTree as ET
from math import radians

dir_path = os.path.dirname(os.path.realpath(__file__))
dir_path2 = os.getcwd()

mech_dir = "d:\\depot\\mwo\\objects\\mechs"
mech_list = next(os.walk(mech_dir))[1]
mech_list.remove("_mech_templates")
mech_list.remove("skins")
mech_list.remove("generic")
print(mech_list)
print("Found " + str(len(mech_list)) + " mechs.")

adder_geo = "d:\\depot\\mwo\\objects\\mechs\\adder\\body\\adder.dae"
geometry = ET.parse(adder_geo)

root = geometry.getroot()
print(root.tag)
print(root.attrib)

for geo in geometry.iter("visual_scene"):
    print("Found visual_scene")
    print(geo.attrib["id"])

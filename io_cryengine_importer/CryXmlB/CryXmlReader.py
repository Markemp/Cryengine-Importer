import os, os.path
import xml.etree.ElementTree as ET
from dataclasses import dataclass

@dataclass
class CryXmlNode:
    node_id: int
    node_name_offset: int
    item_type: int
    attribute_count: int
    child_count: int
    parent_node_id: int
    first_attribute_index: int
    first_child_index: int
    reserved: int

@dataclass
class CryXmlReference:
    name_offset: int
    value_offset: int

@dataclass
class CryXmlValue:
    offset: int
    value: str

class CryXmlSerializer:
    def read_file(self, file):
        with open(file, "rb") as f:
            c = f.peek(1)
            if not c:
                print("End of file")
                return
            if c == '<':
                f.close
                xmlFile = ET.parse(file)
                return xmlFile
            elif c != 'C':
                raise "Not a Cryengine Binary XML File."
            #header = f.


    def DeserializeFile(self, file):
        pass




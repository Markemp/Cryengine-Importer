import os, os.path
import struct
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
            c = f.peek(1)[:1].decode("utf-8")
            print(c)
            if not c:
                print("End of file")
                return
            if c == '<':
                f.close
                xmlFile = ET.parse(file)
                return xmlFile
            elif c != "C":
                print("Not a Cryengine Binary XML File.")
                return
            header = self.read_c_string(f)
            print(header)
            header_length = f.tell()
            file_length = self.read_int32(f)
            node_table_offset = self.read_int32(f)
            node_table_count = self.read_int32(f)
            node_table_size = 28

            reference_table_offset = self.read_int32(f)
            reference_table_count = self.read_int32(f)
            reference_table_size = 8

            offset3 = self.read_int32(f)
            count3 = self.read_int32(f)
            length3 = 4

            content_offset = self.read_int32(f)
            content_length = self.read_int32(f)
            f.close
    
    def read_c_string(self, binary_reader):
        chars = []
        while True:
            c = binary_reader.read(1).decode("utf-8")
            if c == chr(0):
                return "".join(chars)
            chars.append(c)
    
    def read_int32(self, binary_reader):
        val = struct.unpack('<i', binary_reader.read(4))[0]
        return val
    
    def read_int16(self, binary_reader):
        val = struct.unpack('<i', binary_reader.read(2))[0]
        return val

    


cry = CryXmlSerializer()
#cry.read_file("C:\\Users\Geoff\Source\Repos\Cryengine Importer\io_cryengine_importer\CryXmlB\\adder-common.xml")
cry.read_file("C:\\Users\Geoff\Source\Repos\Cryengine Importer\io_cryengine_importer\CryXmlB\\asteroid_hangar_landingpad_medium.xmla")

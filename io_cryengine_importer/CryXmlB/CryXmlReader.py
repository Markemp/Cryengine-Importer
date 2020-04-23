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
            # Node Table section
            node_table = []
            f.seek(node_table_offset)
            node_id = 0
            while f.tell() < node_table_offset + node_table_count * node_table_size:
                position = f.tell()
                node_id = node_id + 1
                node_name_offset = self.read_int32(f)
                item_type = self.read_int32(f)
                attribute_count = self.read_int16(f)
                child_count = self.read_int16(f)
                parent_node_id = self.read_int32(f)
                first_attribute_index = self.read_int32(f)
                first_child_index = self.read_int32(f)
                reserved = self.read_int32(f)
                node = CryXmlNode(node_id, node_name_offset, item_type, attribute_count, child_count, parent_node_id, first_attribute_index, first_child_index, reserved)
                node_table.append(node)

            # Reference Table section
            attribute_table = []
            f.seek(reference_table_offset)
            while f.tell() < reference_table_offset + reference_table_count * reference_table_size:
                position = f.tell()
                name_offset = self.read_int32(f)
                value_offset = self.read_int32(f)
                attribute_node = CryXmlReference(name_offset, value_offset)
                attribute_table.append(attribute_node)
            
            # Order Table section
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
        val = struct.unpack('<h', binary_reader.read(2))[0]
        return val

    


cry = CryXmlSerializer()
#cry.read_file("C:\\Users\Geoff\Source\Repos\Cryengine Importer\io_cryengine_importer\CryXmlB\\adder-common.xml")
cry.read_file("C:\\Users\Geoff\Source\Repos\Cryengine Importer\io_cryengine_importer\CryXmlB\\asteroid_hangar_landingpad_medium.xmla")

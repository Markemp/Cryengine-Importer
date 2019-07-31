import os, os.path
import xml.etree.ElementTree as ET

class CryXmlNode:
    pass

class CryXmlReference:
    pass

class CryXmlValue:
    pass

class CryXmlSerializer:
    def ReadFile(self, file, write_log):
        with open(file) as f:
            c = f.read(1)
            if not c:
                print("End of file")
                return
            if c == '<':
                f.close
                xmlFile = ET.parse(file)
                return xmlFile
            elif c != 'C':
                raise "Not a Cryengine Binary XML File."
            else:
                pass
            
    def DeserializeFile(self, file):
        pass




import unittest
from io_cryengine_importer.CryXmlB.CryXmlReader import CryXmlSerializer, CryXmlNode, CryXmlReference, CryXmlValue
from unittest.mock import patch, mock_open

class CryXmlReaderTests(unittest.TestCase):
    def test_readfile(self):
        #cry_serializer = CryXmlSerializer();
        # with patch("builtins.open", mock_open(read_data="data")) as mock_file:
        #     assert open("path/to/open").read() == "data"
        #     mock_file.assert_called_with("path/to/open")
        #cry_serializer.read_file("path/to/open")
        pass


# def create_test_file(self):
#     return "<Material></Material>"
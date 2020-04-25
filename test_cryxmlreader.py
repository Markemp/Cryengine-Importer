import unittest

def test_canAssertTrue():
    assert True

def create_test_file():
    return "<PrefabsLibrary Name=\"asteroid_hangar_landingpad_medium\"> \
        <Prefab Category=\"\" Description=\"\" Footprint=\"32,32,8\" Id=\"{900040F6-F2DF-4D5A-A4F3-54B823B2D3AB}\" Library=\"asteroid_hangar_landingpad_medium\" Name=\"asteroid_hangar.medium\"> \
        <Objects> \
        <Object ColorRGB=\"65535\" EntityClass=\"CharacterAttachHelper\" FloorNumber=\"-1\" Id=\"{2900FA6B-BE74-4254-B20F-B930A86E7631}\" Layer=\"Main\" Name=\"attach_helper\" Pos=\"0,0,0\" Rotate=\"1,0,0,0\" Type=\"CharAttachHelper\"> \
        <Properties BoneName=\"Bip01 Head\" /> \
        </Object></Objects></Prefab></PrefabsLibrary>"

import os, os.path
import bpy
from . import utilities
from .CryXmlB.CryXmlReader import CryXmlSerializer
from . import constants

default_texture_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets\\default_mat_warning.png")

def fix_submaterials(mats_raw):
    submats = mats_raw.findall("SubMaterials")
    if submats:
        print("Has Submats")
        return submats
    else:
        print("Does not have Submats")
        return mats_raw

def create_materials(matfile, basedir, use_dds=True, use_tif=False):
    # Identify material format
    materials = {}  # All the materials found for the asset
    if use_dds == True:
        file_extension = ".dds"
    elif use_tif == True:
        file_extension = ".tif"
    cry_xml = CryXmlSerializer()
    mats = cry_xml.read_file(matfile)
    # mats = fix_submaterials(mats_raw)
    # Find if it has submaterial element
    print(mats)
    for material_xml in mats.iter("Material"):
        if "Shader" in material_xml.attrib:
            if "Name" in material_xml.attrib:
                mat_name = material_xml.attrib["Name"]
            else:
                mat_name = os.path.splitext(matfile)[0]
            print("Processing material " + mat_name)
            # An actual material.  Create the material, set to nodes, clear and rebuild using the info from the material XML file.
            # TODO:  Make sure the material doesn't already exist.  Figure out how to handle if so.
            material = bpy.data.materials.new(mat_name)
            materials[mat_name] = material
            material.use_nodes = True
            shader = material_xml.attrib["Shader"]
            if shader == "Nodraw":
                create_nodraw_shader_material(material_xml, material, file_extension)
            elif shader == "MechCockpit":
                create_mechcockpit_shader_material(material_xml, material, file_extension)
            elif shader == "Mech":
                create_mechcockpit_shader_material(material_xml, material, file_extension)
            elif shader == "Illum":
                create_illum_shader_material(material_xml, material, file_extension)

            else:
                tree_nodes = material.node_tree
                links = tree_nodes.links
                for n in tree_nodes.nodes:
                    tree_nodes.nodes.remove(n)
                # Every material will have a PrincipledBSDF and Material output.  Add, place, and link.
                shaderPrincipledBSDF = tree_nodes.nodes.new('ShaderNodeBsdfPrincipled')
                shaderPrincipledBSDF.location =  200,500
                #print(mat["Diffuse"])
                if "Diffuse" in material_xml.keys():
                    diffuseColor = utilities.convert_to_rgba(str(material_xml.attrib["Diffuse"]))
                    shaderPrincipledBSDF.inputs[0].default_value = (diffuseColor[0], diffuseColor[1], diffuseColor[2], diffuseColor[3])
                if "Specular" in material_xml.keys():
                    specColor = utilities.convert_to_rgba(str(material_xml.attrib["Specular"]))
                    shaderPrincipledBSDF.inputs[5].default_value = specColor[0]    # Specular always seems to be one value repeated 3 times.
                if "IndirectColor" in material_xml.keys():
                    indirectColor = utilities.convert_to_rgba(str(material_xml.attrib["IndirectColor"]))
                    shaderPrincipledBSDF.inputs[3].default_value = (indirectColor[0], indirectColor[1], indirectColor[2], indirectColor[3])
                if "Opacity" in material_xml.keys():
                    transmission = material_xml.attrib["Opacity"]
                    shaderPrincipledBSDF.inputs[15].default_value = float(transmission)
                if "Shininess" in material_xml.keys():
                    clearcoat = material_xml.attrib["Shininess"]
                    shaderPrincipledBSDF.inputs[12].default_value = float(clearcoat) / 255
                if material_xml.attrib["Shader"] == "Glass":
                    # Glass material.  Make a Glass node layout.
                    create_glass_material(material_xml, tree_nodes, shaderPrincipledBSDF, file_extension)
                else:
                    shaderPrincipledBSDF.inputs[15].default_value = 0.0         # If it's not glass, the transmission should be 0.
                    shout=tree_nodes.nodes.new('ShaderNodeOutputMaterial')
                    shout.location = 500,500
                    links.new(shaderPrincipledBSDF.outputs[0], shout.inputs[0])
                    # For each Texture element, add the file and plug in to the appropriate slot on the PrincipledBSDF shader
                    for texture in material_xml.iter("Texture"):
                        if texture.attrib["Map"] == "Diffuse":
                            texturefile = utilities.get_filename(texture.attrib["File"], file_extension)
                            print("Texturefile: " + str(texturefile))
                            if os.path.isfile(texturefile):
                                matDiffuse = bpy.data.images.load(filepath=texturefile, check_existing=True)
                                shaderDiffImg = tree_nodes.nodes.new('ShaderNodeTexImage')
                                shaderDiffImg.image=matDiffuse
                                shaderDiffImg.location = 0,600
                                links.new(shaderDiffImg.outputs[0], shaderPrincipledBSDF.inputs[0])
                        if texture.attrib["Map"] == "Specular":
                            texturefile = utilities.get_filename(texture.attrib["File"], file_extension)
                            if os.path.isfile(texturefile):
                                matSpec=bpy.data.images.load(filepath=texturefile, check_existing=True)
                                matSpec.colorspace_settings.name = 'Non-Color'
                                shaderSpecImg=tree_nodes.nodes.new('ShaderNodeTexImage')
                                #shaderSpecImg.colorspace_settings.name = 'Non-Color'
                                shaderSpecImg.image=matSpec
                                shaderSpecImg.location = 0,325
                                links.new(shaderSpecImg.outputs[0], shaderPrincipledBSDF.inputs[5])
                        if texture.attrib["Map"] == "Bumpmap":
                            if os.path.isfile(texturefile):
                                texturefile = utilities.get_filename(texture.attrib["File"], file_extension)
                                matNormal=bpy.data.images.load(filepath=texturefile, check_existing=True)
                                matNormal.colorspace_settings.name = 'Non-Color'
                                shaderNormalImg=tree_nodes.nodes.new('ShaderNodeTexImage')
                                #shaderNormalImg.colorspace_settings.name = 'Non-Color'
                                shaderNormalImg.image=matNormal
                                shaderNormalImg.location = -100,0
                                converterNormalMap=tree_nodes.nodes.new('ShaderNodeNormalMap')
                                converterNormalMap.location = 100,0
                                links.new(shaderNormalImg.outputs[0], converterNormalMap.inputs[1])
                                links.new(converterNormalMap.outputs[0], shaderPrincipledBSDF.inputs[19])
    return materials

def create_nodraw_shader_material(material_xml, material, file_extension):
    print("Nodraw shader")
    tree_nodes = material.node_tree
    links = tree_nodes.links
    for n in tree_nodes.nodes:
        tree_nodes.nodes.remove(n)
    # Every material will have a PrincipledBSDF and Material output.  Add, place, and link.
    shaderPrincipledBSDF = create_principle_bsdf_root_node(material_xml, tree_nodes)
    output_node = create_output_node(tree_nodes)
    links.new(shaderPrincipledBSDF.outputs[0], output_node.inputs[0])
    for texture in material_xml.iter("Texture"):
        texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
        links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs[0])
    pass

def create_mechcockpit_shader_material(material_xml, material, file_extension):
    print("MechCockpit shader")
    tree_nodes = material.node_tree
    links = tree_nodes.links
    for n in tree_nodes.nodes:
        tree_nodes.nodes.remove(n)
    # Every material will have a PrincipledBSDF and Material output.  Add, place, and link.
    shaderPrincipledBSDF = create_principle_bsdf_root_node(material_xml, tree_nodes)
    output_node = create_output_node(tree_nodes)
    links.new(shaderPrincipledBSDF.outputs[0], output_node.inputs[0])
    for texture in material_xml.iter("Texture"):
        map = texture.attrib["Map"]
        if map == "Diffuse":
            print("Adding Diffuse Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = 0, 600
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs[0])
        if map == "Specular":
            print("Adding Specular Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = 0, 300
                texture_node.image.colorspace_settings.name = "Non-Color"
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs[5])
        if map == "Bumpmap":
            print("Adding Bump Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = -300, 0
                texture_node.image.colorspace_settings.name = "Non-Color"
                normal_map_node = tree_nodes.nodes.new('ShaderNodeNormalMap')
                normal_map_node.location = 50, 0
                links.new(normal_map_node.outputs[0], shaderPrincipledBSDF.inputs[19])
                links.new(texture_node.outputs[0], normal_map_node.inputs[1])
    pass

def create_illum_shader_material(material_xml, material, file_extension):
    print("Illum shader")
    material.blend_method = "CLIP"
    tree_nodes = material.node_tree
    links = tree_nodes.links
    for n in tree_nodes.nodes:
        tree_nodes.nodes.remove(n)
    # Every material will have a PrincipledBSDF and Material output.  Add, place, and link.
    shaderPrincipledBSDF = create_principle_bsdf_root_node(material_xml, tree_nodes)
    output_node = create_output_node(tree_nodes)
    links.new(shaderPrincipledBSDF.outputs[0], output_node.inputs[0])
    for texture in material_xml.iter("Texture"):
        map = texture.attrib["Map"]
        if map == "Diffuse" or map == "TexSlot1":
            print("Adding Diffuse Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = 0, 600
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs[0])
                links.new(texture_node.outputs[1], shaderPrincipledBSDF.inputs[18])
        if map == "Specular" or map == "TexSlot4":
            print("Adding Specular Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = 0, 300
                texture_node.image.colorspace_settings.name = "Non-Color"
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs[5])
        if map == "Bumpmap" or map == "TexSlot2":
            print("Adding Bump Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = -300, 0
                texture_node.image.colorspace_settings.name = "Non-Color"
                normal_map_node = tree_nodes.nodes.new('ShaderNodeNormalMap')
                normal_map_node.location = 50, 0
                links.new(normal_map_node.outputs[0], shaderPrincipledBSDF.inputs[19])
                links.new(texture_node.outputs[0], normal_map_node.inputs[1])
    pass

def create_mech_shader_material(material_xml, material, file_extension):
    print("Mech shader")
    tree_nodes = material.node_tree
    links = tree_nodes.links
    for n in tree_nodes.nodes:
        tree_nodes.nodes.remove(n)
    # Every material will have a PrincipledBSDF and Material output.  Add, place, and link.
    shaderPrincipledBSDF = create_principle_bsdf_root_node(material_xml, tree_nodes)
    output_node = create_output_node(tree_nodes)
    links.new(shaderPrincipledBSDF.outputs[0], output_node.inputs[0])
    for texture in material_xml.iter("Texture"):
        map = texture.attrib["Map"]
        if map == "Diffuse" or map == "TexSlot1":
            print("Adding Diffuse Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = 0, 600
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs[0])
        if map == "Specular" or map == "TexSlot4":
            print("Adding Specular Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = 0, 300
                texture_node.image.colorspace_settings.name = "Non-Color"
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs[5])
        if map == "Bumpmap" or map == "TexSlot2":
            print("Adding Bump Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = -300, 0
                texture_node.image.colorspace_settings.name = "Non-Color"
                normal_map_node = tree_nodes.nodes.new('ShaderNodeNormalMap')
                normal_map_node.location = 50, 0
                links.new(normal_map_node.outputs[0], shaderPrincipledBSDF.inputs[19])
                links.new(texture_node.outputs[0], normal_map_node.inputs[1])
    pass

def create_image_texture_node(tree_nodes, texture, file_extension):
    texturefile = utilities.get_filename(texture.attrib["File"], file_extension)
    texture_image = bpy.data.images.load(texturefile, check_existing=True) if os.path.isfile(texturefile) else bpy.data.images.load(default_texture_file)
    texture_node = tree_nodes.nodes.new('ShaderNodeTexImage')
    texture_node.image = texture_image
    return texture_node

def create_output_node(tree_nodes):
    shout = tree_nodes.nodes.new('ShaderNodeOutputMaterial')
    shout.location = 600, 600
    return shout

def create_glass_material(mat, tree_nodes, shaderPrincipledBSDF, material_extension):
    print("Glass shader for " + mat.attrib["Name"])
    links = tree_nodes.links
    shaderPrincipledBSDF.inputs[14].default_value = 1.001
    shout=tree_nodes.nodes.new('ShaderNodeOutputMaterial')
    shout.location = 500,500
    links.new(shaderPrincipledBSDF.outputs[0], shout.inputs[0])
    for texture in mat.iter('Texture'):
        if texture.attrib['Map'] == 'Diffuse':
            texturefile = utilities.get_filename(texture.attrib["File"], material_extension)
            if os.path.isfile(texturefile):
                matDiffuse = bpy.data.images.load(filepath=texturefile, check_existing=True)
                shaderDiffImg = tree_nodes.nodes.new('ShaderNodeTexImage')
                shaderDiffImg.image=matDiffuse
                shaderDiffImg.location = 0,600
                links.new(shaderDiffImg.outputs[0], shaderPrincipledBSDF.inputs[0])
                links.new(shaderDiffImg.outputs[1], shaderPrincipledBSDF.inputs[18])
        if texture.attrib['Map'] == 'Specular':
            texturefile = utilities.get_filename(texture.attrib["File"], material_extension)
            if os.path.isfile(texturefile):
                matSpec=bpy.data.images.load(filepath=texturefile, check_existing=True)
                matSpec.colorspace_settings.name = 'Non-Color'
                shaderSpecImg=tree_nodes.nodes.new('ShaderNodeTexImage')
                #shaderSpecImg.colorspace_settings.name = 'Non-Color'
                shaderSpecImg.image=matSpec
                shaderSpecImg.location = 0,325
                links.new(shaderSpecImg.outputs[0], shaderPrincipledBSDF.inputs[5])
        if texture.attrib['Map'] == 'Bumpmap':
            if os.path.isfile(texturefile):
                texturefile = utilities.get_filename(texture.attrib["File"], material_extension)
                matNormal=bpy.data.images.load(filepath=texturefile, check_existing=True)
                matNormal.colorspace_settings.name = 'Non-Color'
                shaderNormalImg=tree_nodes.nodes.new('ShaderNodeTexImage')
                # shaderNormalImg.colorspace_settings.name = 'Non-Color'
                shaderNormalImg.image=matNormal
                shaderNormalImg.location = -100,0
                converterNormalMap=tree_nodes.nodes.new('ShaderNodeNormalMap')
                converterNormalMap.location = 100,0
                links.new(shaderNormalImg.outputs[0], converterNormalMap.inputs[1])
                links.new(converterNormalMap.outputs[0], shaderPrincipledBSDF.inputs[19])

def create_principle_bsdf_root_node(material_xml, tree_nodes):
    shaderPrincipledBSDF = tree_nodes.nodes.new('ShaderNodeBsdfPrincipled')
    shaderPrincipledBSDF.location = 300, 600
    if "Diffuse" in material_xml.keys():
        diffuseColor = utilities.convert_to_rgba(str(material_xml.attrib["Diffuse"]))
        shaderPrincipledBSDF.inputs[0].default_value = (diffuseColor[0], diffuseColor[1], diffuseColor[2], diffuseColor[3])
    if "Specular" in material_xml.keys():
        specColor = utilities.convert_to_rgba(str(material_xml.attrib["Specular"]))
        shaderPrincipledBSDF.inputs[5].default_value = specColor[0]  # Specular always seems to be one value repeated 3 times.
    if "IndirectColor" in material_xml.keys():
        indirectColor = utilities.convert_to_rgba(str(material_xml.attrib["IndirectColor"]))
        shaderPrincipledBSDF.inputs[3].default_value = (indirectColor[0], indirectColor[1], indirectColor[2], indirectColor[3])
    if "Opacity" in material_xml.keys():
        transmission = material_xml.attrib["Opacity"]
        shaderPrincipledBSDF.inputs[15].default_value = float(transmission)
    if "Shininess" in material_xml.keys():
        clearcoat = material_xml.attrib["Shininess"]
        shaderPrincipledBSDF.inputs[12].default_value = float(clearcoat) / 255.0
    return shaderPrincipledBSDF

import os, os.path
import xml.etree.ElementTree as ET
import bpy
from . import utilities
from .CryXmlB.CryXmlReader import CryXmlSerializer

def create_materials(matfile, basedir, use_dds=True, use_tif=False):
    # Identify material format
    materials = {}  # All the materials found for the asset
    if use_dds == True:
        file_extension = ".dds"
    elif use_tif == True:
        file_extension = ".tif"
    cry_xml = CryXmlSerializer()
    mats = cry_xml.read_file(matfile)
    # Find if it has submaterial element
    print(mats)
    for material_xml in mats.iter("Material"):
        if "Name" in material_xml.attrib:
            # An actual material.  Create the material, set to nodes, clear and rebuild using the info from the material XML file.
            name = material_xml.attrib["Name"]
            # TODO:  Make sure the material doesn't already exist.  Figure out how to handle if so.
            material = bpy.data.materials.new(material_xml.attrib["Name"])
            materials[name] = material
            material.use_nodes = True
            if material_xml.attrib["Shader"] == "Nodraw":
                create_nodraw_shader_material(material_xml, material, file_extension)
            else:
                tree_nodes = material.node_tree
                links = tree_nodes.links
                for n in tree_nodes.nodes:
                    tree_nodes.nodes.remove(n)
                # Every material will have a PrincipledBSDF and Material output.  Add, place, and link.
                shaderPrincipledBSDF = tree_nodes.nodes.new('ShaderNodeBsdfPrincipled')
                shaderPrincipledBSDF.location =  300,500
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
                    create_glass_material(material_xml, basedir, tree_nodes, shaderPrincipledBSDF, file_extension)
                else:
                    shaderPrincipledBSDF.inputs[15].default_value = 0.0         # If it's not glass, the transmission should be 0.
                    shout=tree_nodes.nodes.new('ShaderNodeOutputMaterial')
                    shout.location = 500,500
                    links.new(shaderPrincipledBSDF.outputs[0], shout.inputs[0])
                    # For each Texture element, add the file and plug in to the appropriate slot on the PrincipledBSDF shader
                    for texture in material_xml.iter("Texture"):
                        if texture.attrib["Map"] == "Diffuse":
                            texturefile = utilities.get_relative_filename(texture.attrib["File"], file_extension)
                            print("Texturefile: " + str(texturefile))
                            if os.path.isfile(texturefile):
                                matDiffuse = bpy.data.images.load(filepath=texturefile, check_existing=True)
                                shaderDiffImg = tree_nodes.nodes.new('ShaderNodeTexImage')
                                shaderDiffImg.image=matDiffuse
                                shaderDiffImg.location = 0,600
                                links.new(shaderDiffImg.outputs[0], shaderPrincipledBSDF.inputs[0])
                        if texture.attrib["Map"] == "Specular":
                            texturefile = utilities.get_relative_filename(texture.attrib["File"], file_extension)
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
                                texturefile = utilities.get_relative_filename(texture.attrib["File"], file_extension)
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

def create_nodraw_shader_material(material_xml, material, material_extension):
    print("Nodraw shader for " + material_xml.attrib["Name"])
    tree_nodes = material.node_tree
    links = tree_nodes.links
    for n in tree_nodes.nodes:
        tree_nodes.nodes.remove(n)
    # Every material will have a PrincipledBSDF and Material output.  Add, place, and link.
    shaderPrincipledBSDF = create_principle_bsdf_root_node(material, tree_nodes)
    output_node = create_output_node(tree_nodes)
    links.new(shaderPrincipledBSDF.outputs[0], output_node.inputs[0])
    for texture in material_xml.iter("Texture"):
        texture_node = create_image_texture_node(tree_nodes, texture, material_extension)
        links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs[0])
    pass

def create_image_texture_node(tree_nodes, texture, material_extension):
    if texture.attrib["Map"] == "Diffuse":
        tex = utilities.get_relative_filename(texture.attrib["File"], material_extension)
        if os.path.isfile(tex):
            matDiffuse = bpy.data.images.load(filepath=tex, check_existing=True)
            shaderDiffImg = tree_nodes.nodes.new('ShaderNodeTexImage')
            shaderDiffImg.image = matDiffuse
            shaderDiffImg.location = 0, 600
    return shaderDiffImg

def create_output_node(tree_nodes):
    shout = tree_nodes.nodes.new('ShaderNodeOutputMaterial')
    shout.location = 600, 600
    return shout

def create_glass_material(mat, basedir, tree_nodes, shaderPrincipledBSDF, material_extension):
    print("Glass shader for " + mat.attrib["Name"])
    links = tree_nodes.links
    shaderPrincipledBSDF.inputs[14].default_value = 1.001
    shout=tree_nodes.nodes.new('ShaderNodeOutputMaterial')
    shout.location = 500,500
    links.new(shaderPrincipledBSDF.outputs[0], shout.inputs[0])
    for texture in mat.iter('Texture'):
        if texture.attrib['Map'] == 'Diffuse':
            texturefile = utilities.get_relative_filename(texture, material_extension)
            if os.path.isfile(texturefile):
                matDiffuse = bpy.data.images.load(filepath=texturefile, check_existing=True)
                shaderDiffImg = tree_nodes.nodes.new('ShaderNodeTexImage')
                shaderDiffImg.image=matDiffuse
                shaderDiffImg.location = 0,600
                links.new(shaderDiffImg.outputs[0], shaderPrincipledBSDF.inputs[0])
        if texture.attrib['Map'] == 'Specular':
            texturefile = utilities.get_relative_filename(texture, material_extension)
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
                texturefile = utilities.get_relative_filename(texture, material_extension)
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

def create_illum_material(mat):
    pass

def create_principle_bsdf_root_node(material_xml, tree_nodes):
    shaderPrincipledBSDF = tree_nodes.nodes.new('ShaderNodeBsdfPrincipled')
    shaderPrincipledBSDF.location = 300, 500
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
        shaderPrincipledBSDF.inputs[12].default_value = float(clearcoat) / 255
    return shaderPrincipledBSDF

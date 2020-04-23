import os, os.path
import xml.etree.ElementTree as ET
import bpy
from . import utilities

def create_materials(matfile, basedir, use_dds=True, use_tif=False):
    materials = {}
    # Identify material format
    if use_dds == True:
        material_extension = ".dds"
    elif use_tif == True:
        material_extension = ".tif"
    # TODO:  Replace this with CryXmlB
    mats = ET.parse(matfile)
    for mat in mats.iter("Material"):
        if "Name" in mat.attrib:
            # An actual material.  Create the material, set to nodes, clear and rebuild using the info from the material XML file.
            name = mat.attrib["Name"]
            matname = bpy.data.materials.new(mat.attrib["Name"])
            materials[name] = matname
            #print("Found material: " + matname.name)
            matname.use_nodes = True
            tree_nodes = matname.node_tree
            links = tree_nodes.links
            for n in tree_nodes.nodes:
                tree_nodes.nodes.remove(n)
            # Every material will have a PrincipledBSDF and Material output.  Add, place, and link.
            shaderPrincipledBSDF = tree_nodes.nodes.new('ShaderNodeBsdfPrincipled')
            shaderPrincipledBSDF.location =  300,500
            #print(mat["Diffuse"])
            if "Diffuse" in mat.keys():
                diffuseColor = utilities.convert_to_rgba(str(mat.attrib["Diffuse"]))
                shaderPrincipledBSDF.inputs[0].default_value = (diffuseColor[0], diffuseColor[1], diffuseColor[2], diffuseColor[3])
            if "Specular" in mat.keys():
                specColor = utilities.convert_to_rgba(str(mat.attrib["Specular"]))
                shaderPrincipledBSDF.inputs[5].default_value = specColor[0]    # Specular always seems to be one value repeated 3 times.
            if "IndirectColor" in mat.keys():
                indirectColor = utilities.convert_to_rgba(str(mat.attrib["IndirectColor"]))
                shaderPrincipledBSDF.inputs[3].default_value = (indirectColor[0], indirectColor[1], indirectColor[2], indirectColor[3])
            if "Opacity" in mat.keys():
                transmission = mat.attrib["Opacity"]
                shaderPrincipledBSDF.inputs[15].default_value = float(transmission)
            if "Shininess" in mat.keys():
                clearcoat = mat.attrib["Shininess"]
                shaderPrincipledBSDF.inputs[12].default_value = float(clearcoat) / 255
            if mat.attrib["Shader"] == "Glass":
                # Glass material.  Make a Glass node layout.
                create_glass_material(mat, basedir, tree_nodes, shaderPrincipledBSDF, material_extension)
            else:
                shaderPrincipledBSDF.inputs[15].default_value = 0.0         # If it's not glass, the transmission should be 0.
                shout=tree_nodes.nodes.new('ShaderNodeOutputMaterial')
                shout.location = 500,500
                links.new(shaderPrincipledBSDF.outputs[0], shout.inputs[0])
                # For each Texture element, add the file and plug in to the appropriate slot on the PrincipledBSDF shader
                for texture in mat.iter("Texture"):
                    if texture.attrib["Map"] == "Diffuse":
                        texturefile = os.path.normpath(os.path.join(basedir, os.path.splitext(texture.attrib["File"])[0] + material_extension))
                        if os.path.isfile(texturefile):
                            matDiffuse = bpy.data.images.load(filepath=texturefile, check_existing=True)
                            shaderDiffImg = tree_nodes.nodes.new('ShaderNodeTexImage')
                            shaderDiffImg.image=matDiffuse
                            shaderDiffImg.location = 0,600
                            links.new(shaderDiffImg.outputs[0], shaderPrincipledBSDF.inputs[0])
                    if texture.attrib["Map"] == "Specular":
                        texturefile = os.path.normpath(os.path.join(basedir, os.path.splitext(texture.attrib["File"])[0] + material_extension))
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
                            texturefile = os.path.normpath(os.path.join(basedir, os.path.splitext(texture.attrib["File"])[0] + material_extension))
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

def create_glass_material(mat, basedir, tree_nodes, shaderPrincipledBSDF, material_extension):
    print('Glass material')
    links = tree_nodes.links
    shaderPrincipledBSDF.inputs[14].default_value = 1.001
    shout=tree_nodes.nodes.new('ShaderNodeOutputMaterial')
    shout.location = 500,500
    links.new(shaderPrincipledBSDF.outputs[0], shout.inputs[0])
    for texture in mat.iter('Texture'):
        if texture.attrib['Map'] == 'Diffuse':
            texturefile = os.path.normpath(os.path.join(basedir, os.path.splitext(texture.attrib['File'])[0] + material_extension))
            if os.path.isfile(texturefile):
                matDiffuse = bpy.data.images.load(filepath=texturefile, check_existing=True)
                shaderDiffImg = tree_nodes.nodes.new('ShaderNodeTexImage')
                shaderDiffImg.image=matDiffuse
                shaderDiffImg.location = 0,600
                links.new(shaderDiffImg.outputs[0], shaderPrincipledBSDF.inputs[0])
        if texture.attrib['Map'] == 'Specular':
            texturefile = os.path.normpath(os.path.join(basedir, os.path.splitext(texture.attrib['File'])[0] + material_extension))
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
                texturefile = os.path.normpath(os.path.join(basedir, os.path.splitext(texture.attrib['File'])[0] + material_extension))
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

import os, os.path
import bpy
from . import utilities
from .CryXmlB.CryXmlReader import CryXmlSerializer

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
        print("Using DDS")
        file_extension = ".dds"
    elif use_tif == True:
        print("Using TIF")
        file_extension = ".tif"
    cry_xml = CryXmlSerializer()
    mats = cry_xml.read_file(matfile)
    # Find if it has submaterial element
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
                shaderPrincipledBSDF.inputs['Metallic'].default_value = 1.0
                shaderPrincipledBSDF.location =  200,500
                if "Diffuse" in material_xml.keys():
                    diffuseColor = utilities.convert_to_rgba(str(material_xml.attrib["Diffuse"]))
                    shaderPrincipledBSDF.inputs['Base Color'].default_value = (diffuseColor[0], diffuseColor[1], diffuseColor[2], diffuseColor[3])
                if "Specular" in material_xml.keys():
                    specColor = utilities.convert_to_rgba(str(material_xml.attrib["Specular"]))
                    shaderPrincipledBSDF.inputs['Specular Tint'].default_value = specColor
                if "IndirectColor" in material_xml.keys():
                    indirectColor = utilities.convert_to_rgba(str(material_xml.attrib["IndirectColor"]))
                    shaderPrincipledBSDF.inputs['IOR'].default_value = (indirectColor[0], indirectColor[1], indirectColor[2], indirectColor[3])
                if "Opacity" in material_xml.keys():
                    transmission = float(material_xml.attrib["Opacity"])
                    shaderPrincipledBSDF.inputs['Transmission Weight'].default_value = 1.0 - transmission                
                if "Shininess" in material_xml.keys():
                    clearcoat = material_xml.attrib["Shininess"]
                    shaderPrincipledBSDF.inputs['Specular IOR Level'].default_value = float(clearcoat) / 255
                if material_xml.attrib["Shader"] == "Glass":
                    # Glass material.  Make a Glass node layout.
                    create_glass_material(material_xml, tree_nodes, shaderPrincipledBSDF, file_extension)
                else:
                    shaderPrincipledBSDF.inputs['Transmission Weight'].default_value = 0.0         # If it's not glass, the transmission should be 0.
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
                                links.new(shaderDiffImg.outputs[0], shaderPrincipledBSDF.inputs['Base Color'])
                        if texture.attrib["Map"] == "Specular":
                            texturefile = utilities.get_filename(texture.attrib["File"], file_extension)
                            if os.path.isfile(texturefile):
                                matSpec=bpy.data.images.load(filepath=texturefile, check_existing=True)
                                matSpec.colorspace_settings.name = 'Non-Color'
                                shaderSpecImg=tree_nodes.nodes.new('ShaderNodeTexImage')
                                #shaderSpecImg.colorspace_settings.name = 'Non-Color'
                                shaderSpecImg.image=matSpec
                                shaderSpecImg.location = 0,325
                                links.new(shaderSpecImg.outputs[0], shaderPrincipledBSDF.inputs['Specular Tint'])
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
                                links.new(converterNormalMap.outputs[0], shaderPrincipledBSDF.inputs['Coat Normal'])
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
        links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs['Base Color'])
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
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs['Base Color'])
        if map == "Specular":
            print("Adding Specular Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = 0, 300
                texture_node.image.colorspace_settings.name = "Non-Color"
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs['Specular Tint'])
                
                # If the material uses gloss in alpha channel, connect it to Roughness inverted
                if "StringGenMask" in material_xml.keys() and "%SPECULARPOW_GLOSSALPHA%" in material_xml.attrib["StringGenMask"]:
                    invert_node = tree_nodes.nodes.new('ShaderNodeInvert')
                    invert_node.location = 150, 200
                    links.new(texture_node.outputs[1], invert_node.inputs[1])
                    links.new(invert_node.outputs[0], shaderPrincipledBSDF.inputs['Roughness'])
        if map == "Bumpmap":
            print("Adding Bump Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = -300, 0
                texture_node.image.colorspace_settings.name = "Non-Color"
                normal_map_node = tree_nodes.nodes.new('ShaderNodeNormalMap')
                normal_map_node.location = 50, 0
                links.new(normal_map_node.outputs[0], shaderPrincipledBSDF.inputs['Coat Normal'])
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
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs['Base Color'])
                links.new(texture_node.outputs[1], shaderPrincipledBSDF.inputs['Coat Weight'])
        if map == "Specular" or map == "TexSlot4":
            print("Adding Specular Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = 0, 300
                texture_node.image.colorspace_settings.name = "Non-Color"
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs['Specular Tint'])
        if map == "Bumpmap" or map == "TexSlot2":
            print("Adding Bump Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = -300, 0
                texture_node.image.colorspace_settings.name = "Non-Color"
                normal_map_node = tree_nodes.nodes.new('ShaderNodeNormalMap')
                normal_map_node.location = 50, 0
                links.new(normal_map_node.outputs[0], shaderPrincipledBSDF.inputs['Coat Normal'])
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
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs['Base Color'])
        if map == "Specular" or map == "TexSlot4":
            print("Adding Specular Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = 0, 300
                texture_node.image.colorspace_settings.name = "Non-Color"
                links.new(texture_node.outputs[0], shaderPrincipledBSDF.inputs['Specular Tint'])
        if map == "Bumpmap" or map == "TexSlot2":
            print("Adding Bump Map")
            texture_node = create_image_texture_node(tree_nodes, texture, file_extension)
            if texture_node:
                texture_node.location = -300, 0
                texture_node.image.colorspace_settings.name = "Non-Color"
                normal_map_node = tree_nodes.nodes.new('ShaderNodeNormalMap')
                normal_map_node.location = 50, 0
                links.new(normal_map_node.outputs[0], shaderPrincipledBSDF.inputs['Coat Normal'])
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
    shaderPrincipledBSDF.inputs['Anisotropic'].default_value = 1.001
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
                links.new(shaderDiffImg.outputs[0], shaderPrincipledBSDF.inputs['Base Color'])
                links.new(shaderDiffImg.outputs[1], shaderPrincipledBSDF.inputs['Coat Weight'])
        if texture.attrib['Map'] == 'Specular':
            texturefile = utilities.get_filename(texture.attrib["File"], material_extension)
            if os.path.isfile(texturefile):
                matSpec=bpy.data.images.load(filepath=texturefile, check_existing=True)
                matSpec.colorspace_settings.name = 'Non-Color'
                shaderSpecImg=tree_nodes.nodes.new('ShaderNodeTexImage')
                #shaderSpecImg.colorspace_settings.name = 'Non-Color'
                shaderSpecImg.image=matSpec
                shaderSpecImg.location = 0,325
                links.new(shaderSpecImg.outputs[0], shaderPrincipledBSDF.inputs['Specular Tint'])
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
                links.new(converterNormalMap.outputs[0], shaderPrincipledBSDF.inputs['Coat Normal'])

def create_principle_bsdf_root_node(material_xml, tree_nodes):
    shaderPrincipledBSDF = tree_nodes.nodes.new('ShaderNodeBsdfPrincipled')
    shaderPrincipledBSDF.inputs['Metallic'].default_value = 1.0
    shaderPrincipledBSDF.location = 300, 600
    
    # Map CryEngine Diffuse to Blender Base Color
    if "Diffuse" in material_xml.keys():
        diffuseColor = utilities.convert_to_rgba(str(material_xml.attrib["Diffuse"]))
        shaderPrincipledBSDF.inputs['Base Color'].default_value = (diffuseColor[0], diffuseColor[1], diffuseColor[2], diffuseColor[3])
    
    # Map CryEngine Specular to Blender Specular IOR Level
    if "Specular" in material_xml.keys():
        specColor = utilities.convert_to_rgba(str(material_xml.attrib["Specular"]))
        specValue = (specColor[0] + specColor[1] + specColor[2]) / 3.0
        # Set Specular IOR Level (still a float)
        shaderPrincipledBSDF.inputs['Specular IOR Level'].default_value = specValue
        
        # In Blender 4.4, Specular Tint is now a color (RGB) not a float
        # Set it to the original specular color to maintain tint
        shaderPrincipledBSDF.inputs['Specular Tint'].default_value = (specColor[0], specColor[1], specColor[2], 1.0)
    
    # Map CryEngine IndirectColor to Blender Emission
    if "IndirectColor" in material_xml.keys():
        indirectColor = utilities.convert_to_rgba(str(material_xml.attrib["IndirectColor"]))
        averageIndirect = (indirectColor[0] + indirectColor[1] + indirectColor[2]) / 3.0
        # Use correct emission inputs
        shaderPrincipledBSDF.inputs['Emission'].default_value = (indirectColor[0], indirectColor[1], indirectColor[2], indirectColor[3])
        shaderPrincipledBSDF.inputs['Emission Strength'].default_value = averageIndirect * 0.5  # Reduce emission strength
    
    # Map CryEngine Opacity to Blender Alpha and Transmission Weight
    if "Opacity" in material_xml.keys():
        transmission = float(material_xml.attrib["Opacity"])  # Fix variable name to match usage
        # For typical opacity/transparency handling (0=transparent, 1=opaque)
        shaderPrincipledBSDF.inputs['Alpha'].default_value = transmission
        
        # For glass-like transmission (1=fully transmissive)
        # In Blender 4.4, "Transmission" is renamed to "Transmission Weight"
        shaderPrincipledBSDF.inputs['Transmission Weight'].default_value = 1.0 - transmission
    
    # Improved roughness handling from Shininess
    # CryEngine uses 0-255 for shininess, where 255 is very glossy (0 roughness in PBR)
    if "Shininess" in material_xml.keys():
        shininess = float(material_xml.attrib["Shininess"])
        # Convert shininess to roughness (inverse relationship)
        # For CryEngine, higher values (255) mean less roughness
        # Map 0-255 to 1-0 (inverted) with a curve adjustment for better results
        normalized_shininess = shininess / 255.0
        # Apply a curve for better visual results - this gives a more balanced conversion
        roughness = 1.0 - (normalized_shininess ** 0.5)  # Square root for a better curve
        shaderPrincipledBSDF.inputs['Roughness'].default_value = roughness
    else:
        # Default to a medium roughness if not specified
        shaderPrincipledBSDF.inputs['Roughness'].default_value = 0.5
    
    # Check for shader flags in GenMask to make further adjustments
    if "StringGenMask" in material_xml.keys():
        genMask = material_xml.attrib["StringGenMask"]
        
        # Lower the metallic value for more realistic metals if not specifically set to be very metallic
        if "%METAL%" not in genMask:
            shaderPrincipledBSDF.inputs['Metallic'].default_value = 0.7  # Less extreme metallic value
        
        # Reduce specular for non-metal materials
        if "%GLOSS_MAP%" in genMask and "%METAL%" not in genMask:
            shaderPrincipledBSDF.inputs['Specular IOR Level'].default_value = 0.3
    
    return shaderPrincipledBSDF
    
def remove_unlinked_materials():
    for material in bpy.data.materials:
        if material.users == 0:
            bpy.data.materials.remove(material)

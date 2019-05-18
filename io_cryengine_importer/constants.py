WGT_PREFIX = 'WGT-'  # Prefix for widget objects
ROOT_NAME = 'Bip01'  # Name of the root bone.
WGT_LAYER = 'Widget Layer'
CTRL_LAYER = "Control Bones Layer"
GEO_LAYER = "Deform Bones Layer"

# store keymaps here to access after registration
addon_keymaps = []

# There are misspelled words (missle).  Just a FYI.
weapons = ['hero', 'missile', 'missle', 'narc', 'uac', 'uac2', 'uac5', 'uac10', 'uac20', 'rac', '_lty',
           'ac2', 'ac5', 'ac10', 'ac20', 'gauss', 'ppc', 'flamer', '_mg', '_lbx', 'damaged', '_mount', '_rl20',
           '_rl10', '_rl15', 'laser', 'ams', '_phoenix', 'blank', 'invasion', 'hmg', 'lmg', 'lams', 'hand', 'barrel']
		   
control_bones = ['Hand_IK.L', 'Hand_IK.R', 'Bip01', 'Hip_Root', 'Bip01_Pitch', 'Bip01_Pelvis',
                 'Knee_IK.R', 'Knee_IK.L', 'Foot_IK.R', 'Foot_IK.L', 'Elbow_IK.R', 'Elbow_IK.L']
				 
materials = {} # All the materials found for the mech
cockpit_materials = {}
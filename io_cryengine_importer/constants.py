WIDGET_PREFIX = 'WGT-'  # Prefix for widget objects
ROOT_NAME = 'Bip01'  # Name of the root bone.
WIDGETS_COLLECTION = 'Widgets'
CONTROL_BONES_COLLECTION = "Control Bones"
DEFORM_BONES_COLLECTION = "Deform Bones"
EMPTIES_COLLECTION = "Empties"
WEAPONS_COLLECTION = "Weapons"
DAMAGED_PARTS_COLLECTION = "Damaged Parts"
VARIANTS_COLLECTION = "Variants"
MECH_COLLECTION = "Mech"

basedir = ""

# store keymaps here to access after registration
addon_keymaps = []

# There are misspelled words (missle).
weapons = ['hero', 'missile', 'missle', 'narc', 'uac', 'uac2', 'uac5', 'uac10', 'uac20', 'rac', '_lty', 'mount',
           'ac2', 'ac5', 'ac10', 'ac20', 'gauss', 'ppc', 'flamer', '_mg', '_lbx', 'damaged', '_mount', '_rl20',
           '_rl10', '_rl15', 'laser', 'ams', '_phoenix', 'blank', 'invasion', 'hmg', 'lmg', 'lams', 'hand', 'barrel']

control_bones = ['Hand_IK.L', 'Hand_IK.R', 'Bip01', 'Hip_Root', 'Bip01_Pitch', 'Bip01_Pelvis', 'Knee_IK.R', 
                 'Knee_IK.L', 'Foot_IK.R', 'Foot_IK.L', 'Elbow_IK.R', 'Elbow_IK.L', 'Shoulder.L', 'Shoulder.R']

materials = {} # All the materials found for the mech
cockpit_materials = {}

shoulder_only_mechs = ["catapult", "cicada", "locust", "jenner", "flea", "urbanmech", "stalker", "jagermech", "jagermechiic",
    "rifleman", "riflemaniic", "raven", "jenneriic", "blackjack", "firefly"]

# Fixes mappings when the bone names don't have standard capitalization.
bad_bonename_map = { "mad_left_leg_toe0": "Bip01_L_toe0", 
    "mad_left_leg_toe1": "Bip01_L_toe1", 
    "mad_right_leg_toe0": "Bip01_R_toe0", 
    "mad_right_leg_toe1": "Bip01_R_toe1",
    "as7_left_arm_elbow": "Bip01_L_elbow", 
    "as7_right_arm_elbow": "Bip01_R_elbow", 
    "drg_left_leg_knee": "Bip01_L_knee", 
    "drg_right_leg_knee": "Bip01_R_knee" }
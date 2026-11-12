"""The animation body's woman made ready for the face work: eyes, teeth, tongue and eyelashes from MPFB's CC0 system assets, and the 52 ARKit shapes from Faceunits 01 (CC0),
as the mouth-fader character was made (initiative animation-face). Run with --blend on a clean_body.py file. Args: out.blend"""
import os, sys
import addon_utils, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

a = hb.args()
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.faceservice import ARKIT_FACEUNITS, FaceService
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.locationservice import LocationService

ASSETS = {"Eyes": "eyes/high-poly/high-poly.mhclo", "Teeth": "teeth/teeth_base/teeth_base.mhclo", "Tongue": "tongue/tongue01/tongue01.mhclo", "Eyelashes": "eyelashes/eyelashes02/eyelashes02.mhclo"}
body = bpy.data.objects["HM_body"]
data = LocationService.get_user_data()
for label, rel in ASSETS.items():
    obj = HumanService.add_mhclo_asset(os.path.join(data, *rel.split("/")), body, asset_type=label, subdiv_levels=1, material_type="MAKESKIN")
    obj.name = f"HM_{label.lower()}"
FaceService.load_targets(body, load_microsoft_visemes=False, load_arkit_faceunits=True)
FaceService.interpolate_targets(body)
units = set(ARKIT_FACEUNITS)
counts = {o.name: sum(k.name in units for k in o.data.shape_keys.key_blocks) for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys}
bpy.ops.wm.save_as_mainfile(filepath=a[0])
print("RESULT arkit shapes per object", counts)

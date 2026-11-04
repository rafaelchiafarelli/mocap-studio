"""Reads an MPFB human edited by hand in Blender back into a recipe, so its sliders can be rebuilt with every layer. Args: body_object name sex out.json. Run with --blend."""
import json, sys
import addon_utils, bpy
a = sys.argv[sys.argv.index("--") + 1:]
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.targetservice import TargetService
body = bpy.data.objects[a[0]]
macros = TargetService.get_macro_info_dict_from_basemesh(body)
keys = body.data.shape_keys.key_blocks if body.data.shape_keys else []
targets = {}
for k in keys:
    if k.name == "Basis" or k.name.startswith(("F_", "B_")) or k.value == 0.0:
        continue
    name = TargetService.decode_shapekey_name(k.name) if k.name.startswith("$") else k.name  # MPFB may encode slider names
    # macro detail targets come back through the macros, so they aren't listed again
    if name.startswith(("male-", "female-", "universal-", "african-", "asian-", "caucasian-")) or "$" in name:
        continue
    if TargetService.target_full_path(name):
        targets[name] = round(k.value, 4)
json.dump({"name": a[1], "sex": a[2], "macros": macros, "targets": targets, "assets": {"eyes": "eyes/high-poly/high-poly.mhclo", "teeth": "teeth/teeth_base/teeth_base.mhclo", "tongue": "tongue/tongue01/tongue01.mhclo"}}, open(a[3], "w"), indent=1)
print("targets", len(targets), list(targets)[:12])

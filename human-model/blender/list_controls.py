"""Lists everything a built model offers to a person or a script. Args: out.json. Run with --blend."""
import json, sys
import bpy
out = sys.argv[sys.argv.index("--") + 1]
ctrl = bpy.data.objects["HM_controls"]
props = {}
for k in ctrl.keys():
    if isinstance(ctrl[k], float):
        ui = ctrl.id_properties_ui(k).as_dict()
        props[k] = {"min": ui.get("min"), "max": ui.get("max")}
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
rig = bpy.data.objects["HM_rig"]
keys = [k.name for k in skin.data.shape_keys.key_blocks]
res = {"objects": sorted(o.name for o in bpy.data.objects if o.type != "MESH" or o.parent_type != "BONE")[:40], "collections": {c.name: len(c.objects) for c in bpy.data.collections}, "controls": props,
       "shape_keys_muscle": [k for k in keys if k.startswith(("F_", "B_"))], "shape_keys_other": [k for k in keys if not k.startswith(("F_", "B_", "$"))], "rig_bones": len(rig.data.bones), "hm_bones": [b.name for b in rig.data.bones if b.name.startswith("hm_")],
       "limits": {b.name: list(b["hm_limit_deg"]) for b in rig.pose.bones if "hm_limit_deg" in b}, "sex": rig.get("hm_sex")}
json.dump(res, open(out, "w"), indent=1)
print("controls", len(props), "keys", len(keys))

"""Opened on the character .blend, never saved. Proves the asset moves: head turn, arm pose and ARKit face units."""
import sys
import addon_utils, bpy
args = sys.argv[sys.argv.index("--") + 1:]
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.faceservice import FaceService, ARKIT_FACEUNITS
from mathutils import Euler
import math
body = bpy.data.objects["character.body"]
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("RESULT arkit_defined", len(ARKIT_FACEUNITS))
try:
    FaceService.load_targets(body, load_microsoft_visemes=False, load_arkit_faceunits=True)
    keys = {k.name: k for k in body.data.shape_keys.key_blocks}
    loaded = [t for t in keys if any(u.lower() in t.lower() for u in ARKIT_FACEUNITS)]
    print("RESULT arkit_loaded", len(loaded), loaded[:6])
    FaceService.interpolate_targets(body)
    for name, val in (("mouthSmileLeft", 0.65), ("mouthSmileRight", 0.65), ("jawOpen", 0.25), ("browInnerUp", 0.5), ("eyeSquintLeft", 0.25), ("eyeSquintRight", 0.25)):
        for o in [body] + [c for c in bpy.data.objects if c.type == "MESH" and c.parent in (rig, body) and c.data.shape_keys]:
            kb = o.data.shape_keys.key_blocks if o.data.shape_keys else {}
            for k in kb:
                if name.lower() in k.name.lower():
                    k.value = val
    print("RESULT expression_set", [k.name for k in keys.values() if k.value and "mouthSmile" in k.name][:4])
except Exception as e:
    print("RESULT arkit_error", repr(e)[:400])
# A seated-at-the-bench pose: head down and turned a little, elbows bent, hands forward.
for n, rot in {"spine.006": (0.12, 0.0, 0.1), "spine.005": (0.08, 0.0, 0.05), "upper_arm.R": (0.0, 0.0, -0.85), "upper_arm.L": (0.0, 0.0, 0.85),
               "forearm.R": (1.0, 0.0, 0.0), "forearm.L": (1.0, 0.0, 0.0)}.items():
    b = rig.pose.bones.get(n)
    if b is None:
        print("RESULT missing_bone", n); continue
    b.rotation_mode = "XYZ"; b.rotation_euler = Euler(rot, "XYZ")
bpy.context.view_layer.update()
print("RESULT hair_parent", [(o.name, o.parent_type, o.parent_bone) for o in bpy.data.objects if o.type == "CURVES"])

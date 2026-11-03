"""A real contraction: measures how far the insertion moves and how much the muscle shortens and thickens. Args: out.json. Run with --blend."""
import json, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
out = hb.args()[0]
ctrl = bpy.data.objects["HM_controls"]
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
mrig = bpy.data.objects["HM_muscle_rig"]
res = {}


def evaluate():
    ctrl.update_tag()
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    dg = bpy.context.evaluated_depsgraph_get()
    return dg


for name in ("frontalis_lateral_L", "zygomaticus_major_L"):
    prop = f"m_{name}"
    dg = evaluate()
    pb = mrig.evaluated_get(dg).pose.bones[f"{name}.0"]
    L0 = (pb.tail - pb.head).length
    s0 = pb.matrix.to_scale()
    v0 = hb.evaluated_verts(skin)
    ctrl[prop] = 1.0
    dg = evaluate()
    pb = mrig.evaluated_get(dg).pose.bones[f"{name}.0"]
    L1 = (pb.tail - pb.head).length
    s1 = pb.matrix.to_scale()
    v1 = hb.evaluated_verts(skin)
    ctrl[prop] = 0.0
    res[name] = {"length_mm": [L0 * 1000, L1 * 1000], "shortening_pct": (1 - L1 / L0) * 100, "width_scale": [s0.x, s1.x], "peak_skin_mm": float(np.linalg.norm(v1 - v0, axis=1).max() * 1000)}
    print(name, res[name])
json.dump(res, open(out, "w"), indent=0)

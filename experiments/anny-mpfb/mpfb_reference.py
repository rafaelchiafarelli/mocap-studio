"""Exports MPFB 2.0.18 meshes for a set of macro and target settings, to compare with Anny. Runs in Blender. Args: OUT.npz OUT.json
Vertices are the basemesh's shape-key mix, all of them (helpers included), in MPFB's order and Blender's axes, metres."""
import json, sys
import bpy
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService

D = {"gender": 0.5, "age": 0.5, "muscle": 0.5, "weight": 0.5, "proportions": 0.5, "height": 0.5, "cupsize": 0.5, "firmness": 0.5,
     "race": {"asian": 1 / 3, "caucasian": 1 / 3, "african": 1 / 3}}


def m(**kw):
    d = json.loads(json.dumps(D))
    for k, v in kw.items():
        if k in ("asian", "caucasian", "african"):
            d["race"] = {"asian": 0.0, "caucasian": 0.0, "african": 0.0}
            d["race"][k] = v
        else:
            d[k] = v
    return d


CASES = {
    "default": (m(), {}),
    "female": (m(gender=0.0), {}),
    "male": (m(gender=1.0), {}),
    "male_heavy_strong": (m(gender=1.0, weight=1.0, muscle=1.0), {}),
    "female_thin_old": (m(gender=0.0, weight=0.0, age=0.9), {}),
    "female_tall_ideal": (m(gender=0.0, height=0.9, proportions=1.0), {}),
    "female_cup": (m(gender=0.0, cupsize=1.0, firmness=0.0), {}),
    "african_male": (m(gender=1.0, african=1.0), {}),
    "young_age025": (m(age=0.25), {}),
    "waist_hip_targets": (m(gender=0.0), {"measure-waist-circ-decr|incr": 0.6, "measure-hips-circ-decr|incr": -0.4}),
    "nose_target": (m(), {"nose-scale-depth-decr|incr": 0.8}),
}
out, meta = {}, {}
for name, (macros, targets) in CASES.items():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    body = HumanService.create_human(macro_detail_dict=macros, feet_on_ground=False)
    loaded = {}
    for t, v in targets.items():
        side = "incr" if v > 0 else "decr"
        tname = t.replace("decr|incr", side)
        path = TargetService.target_full_path(tname)
        if not path:
            raise SystemExit(f"no target {tname}")
        TargetService.load_target(body, path, weight=abs(v), name=tname)
        loaded[tname] = abs(v)
    dg = bpy.context.evaluated_depsgraph_get()
    keys = body.data.shape_keys.key_blocks
    base = np.array([v.co[:] for v in keys[0].data])
    co = base.copy()
    for k in keys[1:]:
        co += k.value * (np.array([v.co[:] for v in k.data]) - base)
    out[name] = (np.array(body.matrix_world)[:3, :3] @ co.T).T + np.array(body.matrix_world)[:3, 3]
    meta[name] = {"macros": macros, "targets": loaded, "keys": [(k.name, round(k.value, 5)) for k in keys]}
out["faces"] = np.array([[p.vertices[i] for i in range(4)] if len(p.vertices) == 4 else list(p.vertices) + [p.vertices[0]] for p in body.data.polygons])
np.savez_compressed(a[0], **out)
json.dump(meta, open(a[1], "w"), indent=1)
print("cases", len(CASES), "verts", len(body.data.vertices))

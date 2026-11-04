"""Real sizes for MPFB's macro sliders. Args: out.json. Sweeps each macro for both sexes and measures the skin in metres."""
import json, sys
import addon_utils, bpy
import numpy as np
out = sys.argv[sys.argv.index("--") + 1]
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService
BASE = {"age": 0.5, "muscle": 0.5, "weight": 0.5, "height": 0.5, "proportions": 0.5, "cupsize": 0.5, "firmness": 0.5, "race": {"african": 0.33, "asian": 0.33, "caucasian": 0.34}}


def measure(macros):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    body = HumanService.create_human(macro_detail_dict=macros)
    dg = bpy.context.evaluated_depsgraph_get()
    me = body.evaluated_get(dg).to_mesh()
    c = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", c)
    c = c.reshape(-1, 3)
    M = np.array(body.matrix_world)
    c = c @ M[:3, :3].T + M[:3, 3]
    loops = [list(p.vertices) for p in me.polygons if max(p.vertices) < 13380]
    volume = abs(sum(np.dot(c[f[0]], np.cross(c[f[i]], c[f[i + 1]])) for f in loops for i in range(1, len(f) - 1)) / 6)
    c = c[:13380]
    body.evaluated_get(dg).to_mesh_clear()
    h = c[:, 2].max() - c[:, 2].min()
    head = c[c[:, 2] > c[:, 2].max() - 0.25]
    def width(z, band=0.012, gap=0.03):
        x = np.sort(np.abs(c[np.abs(c[:, 2] - z) < band, 0]))
        j = np.flatnonzero(np.diff(x) > gap)
        return float(2 * (x[j[0]] if len(j) else x[-1]))
    def depth(z, band=0.012):
        p = c[(np.abs(c[:, 2] - z) < band) & (np.abs(c[:, 0]) < 0.12)]
        return float(np.ptp(p[:, 1]))
    return {"volume_l": float(volume * 1000), "stature_m": float(h), "waist_w_m": width(c[:, 2].min() + 0.6 * h), "waist_d_m": depth(c[:, 2].min() + 0.6 * h), "hip_w_m": width(c[:, 2].min() + 0.52 * h), "head_w_m": float(np.ptp(head[:, 0]))}


rows = []
for sex, g in (("male", 1.0), ("female", 0.0)):
    for macro in ("height", "weight", "muscle", "age", "proportions"):
        for v in (0.0, 0.25, 0.5, 0.75, 1.0):
            m = json.loads(json.dumps(BASE))
            m["gender"] = g
            m[macro] = v
            rows.append({"sex": sex, "macro": macro, "value": v, **measure(m)})
json.dump(rows, open(out, "w"), indent=0)
print("rows", len(rows))

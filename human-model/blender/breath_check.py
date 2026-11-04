"""Measures the rib cage at rest and at a full breath. Args: out.json. Run with --blend."""
import json, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
out = hb.args()[0]
ctrl = bpy.data.objects["HM_controls"]


def extents():
    ctrl.update_tag()  # a changed property only reaches the drivers once the object is tagged
    bpy.context.scene.frame_set(bpy.context.scene.frame_current)
    dg = bpy.context.evaluated_depsgraph_get()
    pts = []
    for i in (5, 6, 7, 8):
        for s in "LR":
            o = bpy.data.objects[f"rib_{i}_{s}"]
            c = np.empty(len(o.data.vertices) * 3)
            o.data.vertices.foreach_get("co", c)
            M = np.array(o.evaluated_get(dg).matrix_world)
            pts.append(c.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
    p = np.vstack(pts)
    return (p[:, 0].max() - p[:, 0].min(), p[:, 1].max() - p[:, 1].min())


rest = extents()
ctrl["breath"] = 1.0
full = extents()
ctrl["breath"] = 0.0
# Ramanujan's ellipse, for a circumference from width and depth
perim = lambda a, b: np.pi * (3 * (a / 2 + b / 2) - np.sqrt((3 * a / 2 + b / 2) * (a / 2 + 3 * b / 2)))
res = {"width_rest": float(rest[0]), "depth_rest": float(rest[1]), "width_full": float(full[0]), "depth_full": float(full[1]), "expansion_cm": float((perim(*full) - perim(*rest)) * 100)}
json.dump(res, open(out, "w"))
print(res)

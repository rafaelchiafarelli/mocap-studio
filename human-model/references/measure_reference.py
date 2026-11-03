"""Read-only: measures the kept bones of a reference .blend. Args: out.json. World-space bounding boxes and principal lengths."""
import json, sys
import bpy
import numpy as np
out = sys.argv[sys.argv.index("--") + 1]
NAMES = ["Femur.l", "Humerus.l", "Radius.l", "Ulna.l", "Tibia.l", "Fibula.l", "Hip bone.l", "Hip bone.r", "Mandible", "Clavicle.l", "Scapula.l", "Scapula.r", "Sacrum", "Body of sternum", "Manubrium of sternum",
         "Frontal bone", "Occipital bone", "Calcaneus.l", "Zygomatic bone.l", "Zygomatic bone.r", "Parietal bone.l", "Parietal bone.r"]
res = {}
for name in NAMES:
    o = bpy.data.objects.get(name)
    if o is None or o.type != "MESH":
        res[name] = None
        continue
    c = np.empty(len(o.data.vertices) * 3)
    o.data.vertices.foreach_get("co", c)
    c = c.reshape(-1, 3)
    M = np.array(o.matrix_world)
    w = c @ M[:3, :3].T + M[:3, 3]
    v = w - w.mean(0)
    axis = np.linalg.svd(v, full_matrices=False)[2][0]
    d = v @ axis
    res[name] = {"min": w.min(0).tolist(), "max": w.max(0).tolist(), "length": float(d.max() - d.min()), "verts": len(c)}
json.dump(res, open(out, "w"), indent=1)

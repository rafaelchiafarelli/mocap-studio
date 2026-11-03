"""Exports a character that already exists as a .blend, in the same format as export_human.py, so the same fit runs on it. Args: body_object rig_object out.npz out.json. Run with --blend.
The rest shape is Basis plus the identity targets; expression shapes, poses and animation are left out."""
import json, sys
import bpy
import numpy as np
args = sys.argv[sys.argv.index("--") + 1:]
body, rig = bpy.data.objects[args[0]], bpy.data.objects[args[1]]
N_BODY = 13380  # MakeHuman's body vertices come first; clothes helpers and joint cubes follow, masked in the file
keys = body.data.shape_keys.key_blocks
n = len(body.data.vertices)
get = lambda k: (lambda a: (k.data.foreach_get("co", a), a.reshape(-1, 3))[1])(np.empty(n * 3))
basis = get(keys[0])
co = basis.copy()
for k in keys[1:]:
    if k.name.startswith("$") or k.name.startswith("ma-") or "$md" in k.name or k.name.startswith(("detail", "tgt_")):
        co += k.value * (get(k) - basis)
M = np.array(body.matrix_world)
co = co @ M[:3, :3].T + M[:3, 3]
face_v = np.array([len(p.vertices) for p in body.data.polygons])
loops, starts, sizes = [], [], []
for p in body.data.polygons:
    v = list(p.vertices)
    if max(v) < N_BODY:
        starts.append(len(loops))
        sizes.append(len(v))
        loops += v
R = np.array(rig.matrix_world)
bones = {b.name: {"head": (R[:3, :3] @ np.array(b.head_local) + R[:3, 3]).tolist(), "tail": (R[:3, :3] @ np.array(b.tail_local) + R[:3, 3]).tolist(), "parent": b.parent.name if b.parent else None} for b in rig.data.bones}
groups = {g.name: [] for g in body.vertex_groups}
for v in body.data.vertices[:N_BODY]:
    for g in v.groups:
        if g.weight > 0:
            groups[body.vertex_groups[g.group].name].append([v.index, g.weight])
np.savez_compressed(args[2], verts=co[:N_BODY].astype(np.float32), loops=np.array(loops, np.int32), starts=np.array(starts, np.int32), sizes=np.array(sizes, np.int32))
json.dump({"bones": bones, "groups": groups, "macros": {}, "shape_keys": [k.name for k in keys]}, open(args[3], "w"))
print("verts", N_BODY, "polys", len(starts), "bones", len(bones), "keys", [k.name for k in keys if k.value > 0][:12])

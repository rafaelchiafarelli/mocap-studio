"""Reads a keyed character: each expression shape's displacement and its value at every frame. Args: body_object out.npz. Run with --blend."""
import json, sys
import bpy
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
body = bpy.data.objects[a[0]]
keys = body.data.shape_keys.key_blocks
n = len(body.data.vertices)
scene = bpy.context.scene


def co(k):
    x = np.empty(n * 3)
    k.data.foreach_get("co", x)
    return x.reshape(-1, 3)


names = [k.name for k in keys[1:] if not k.name.startswith(("$", "F_", "B_")) and k.name[0].islower() and "-" not in k.name]
basis = co(keys[0])
arrays = {f"S_{nm}": (co(keys[nm]) - basis)[:13380].astype(np.float32) for nm in names}
frames = list(range(scene.frame_start, scene.frame_end + 1))
values = np.zeros((len(frames), len(names)))
for i, f in enumerate(frames):
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg).data.shape_keys.key_blocks
    for j, nm in enumerate(names):
        values[i, j] = ev[nm].value
np.savez_compressed(a[1], values=values, names=np.array(names), **arrays)
print("shapes", len(names), "frames", len(frames), "active", [nm for j, nm in enumerate(names) if values[:, j].max() > 0.01][:60])

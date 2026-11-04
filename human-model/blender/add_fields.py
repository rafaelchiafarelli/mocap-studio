"""Adds muscle fields to an existing character file as shape keys, with HM_controls. Args: body_object rig_object fields.npz muscles.json out.blend. Run with --blend. Existing keys and animation stay; the new keys start at 0."""
import json, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
a = hb.args()
body, rig = bpy.data.objects[a[0]], bpy.data.objects[a[1]]
fields = np.load(a[2])
ctrl = hb.controls_object()
n = len(body.data.vertices)
keys = body.data.shape_keys
basis = np.empty(n * 3)
keys.reference_key.data.foreach_get("co", basis)
basis = basis.reshape(-1, 3)
Minv = np.linalg.inv(np.array(body.matrix_world)[:3, :3])
ids = fields["ids"]
for k in fields.files:
    if not k.startswith("F_"):
        continue
    key = body.shape_key_add(name=k, from_mix=False)
    co = basis.copy()
    co[ids] += fields[k] @ Minv.T
    key.data.foreach_set("co", co.ravel())
    prop = f"m_{k[2:]}"
    hb.add_prop(ctrl, prop)
    hb.drive(key, "value", None, ctrl, prop, "x")
bpy.ops.wm.save_as_mainfile(filepath=a[4], compress=True)
print("added", sum(1 for k in fields.files if k.startswith("F_")))

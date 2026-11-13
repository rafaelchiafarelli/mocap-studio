"""Bakes wave offsets into the walking body, so it plays without simulating. Run with --blend. Args: offsets.npz out.blend [key_prefix fader]
One shape key per frame, moved along the skin's rest normal and played by a plain-expression driver. HM_controls has wave_amount (0 to 3), multiplying them all;
the face's sway (tools/face_tissue.py) uses its own prefix and fader, as face_sway. Frames where nothing moves past 0.01 mm get no key."""
import os, sys
import bpy
import numpy as np
HERE = os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1]))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import hmblender as hb
import posed_mesh as pm
from hmcore import deltamush as dm

a = hb.args()
d = np.load(a[0])
offsets, tris, first = d["offsets"], d["tris"], int(d["first"])
body = bpy.data.objects["HM_body"]
rest = d["rest"].astype(float)
normals = dm.vertex_normals(rest, tris)
ctrl = hb.controls_object("HM_controls")
prefix, fader = (a[2], a[3]) if len(a) > 3 else ("wave", "wave_amount")
hb.add_prop(ctrl, fader, 1.0, 0.0, 3.0)
if body.data.shape_keys is None:
    body.shape_key_add(name="Basis", from_mix=False)
n = len(body.data.vertices)
basis = np.empty(n * 3)
body.data.shape_keys.key_blocks[0].data.foreach_get("co", basis)
basis = basis.reshape(-1, 3)
to_object = np.array(body.matrix_world.inverted())[:3, :3]
for i, offset in enumerate(offsets):
    frame = first + i
    if np.abs(offset).max() < 1e-5:
        continue
    co = basis.copy()
    co[: pm.N_BODY] += ((normals * offset[:, None]) @ to_object.T)
    kb = body.shape_key_add(name=f"{prefix}.{frame:04d}", from_mix=False)
    kb.data.foreach_set("co", co.ravel())
    kb.slider_min, kb.slider_max = 0.0, 3.0
    driver = kb.driver_add("value").driver
    driver.type = "SCRIPTED"
    v = driver.variables.new()
    v.name = "a"
    v.targets[0].id, v.targets[0].data_path = ctrl, f'["{fader}"]'
    driver.expression = f"max(0,1-abs(frame-{frame}))*a"
bpy.ops.wm.save_as_mainfile(filepath=a[1])
print("baked", len(offsets), "frames, largest offset", float(np.abs(offsets).max() * 1000), "mm")

"""Keys one variant of a take onto a file from add_fields.py. Args: body_object activ.npz variant(faders|hybrid|muscle) out.blend [start end]. Run with --blend."""
import json, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
a = hb.args()
body = bpy.data.objects[a[0]]
d = np.load(a[1])
variant, out = a[2], a[3]
scene = bpy.context.scene
ctrl = bpy.data.objects["HM_controls"]
muscles = [str(x) for x in d["muscles"]]
activ = {"hybrid": d["activ_h"], "muscle": d["activ_b"], "faders": None}[variant]
keys = body.data.shape_keys
KEEP = ("jaw", "eyeLook", "tongue", "lipBite", "eyeBlink")
if variant == "muscle":
    # the tracked muscle solve takes over everything but jaw, gaze, tongue and blink
    for k in keys.key_blocks:
        if k.name.startswith(("$", "F_", "B_")) or k.name == "Basis" or not k.name[0].islower() or "-" in k.name or k.name.startswith(KEEP):
            continue
        path = f'key_blocks["{k.name}"].value'
        keys.driver_remove(path)
        fc = keys.driver_add(path)
        fc.driver.type = "SCRIPTED"
        fc.driver.expression = "0"
if activ is not None:
    for j, m in enumerate(muscles):
        prop = f"m_{m}"
        curve = activ[:, j]
        if curve.max() < 0.005:
            continue
        for i, v in enumerate(curve):
            ctrl[prop] = float(v)
            ctrl.keyframe_insert(f'["{prop}"]', frame=scene.frame_start + i)
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
print("keyed", variant)

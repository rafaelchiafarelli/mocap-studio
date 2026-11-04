"""Renders the same character's current smile against the muscle-driven one, on a neutral frame. Args: body_object out_prefix [frame]. Run with --blend: a file from add_fields.py."""
import os, sys
import bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
a = hb.args()
body = bpy.data.objects[a[0]]
prefix = a[1]
scene = bpy.context.scene
ctrl = bpy.data.objects["HM_controls"]
keys = body.data.shape_keys
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 16
scene.render.resolution_x, scene.render.resolution_y = 900, 900
for o in bpy.data.objects:
    if "video_card" in o.name:
        o.hide_render = True
# stop everything that animates the face
if keys.animation_data:
    keys.animation_data.action = None
    for d in list(keys.animation_data.drivers):
        if not d.data_path.split('"')[1].startswith("F_"):
            keys.driver_remove(d.data_path)
for k in keys.key_blocks:
    if not k.name.startswith(("$", "F_")) and k.name != "Basis" and k.name[0].islower():
        k.value = 0.0
scene.frame_set(1)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.endswith("metarig"))
if rig.animation_data:
    rig.animation_data.action = None
for b in rig.pose.bones:
    b.rotation_quaternion = (1, 0, 0, 0)
    b.rotation_euler = (0, 0, 0)
    b.location = (0, 0, 0)
nose = rig.matrix_world @ rig.data.bones["nose.001"].head_local
cam = hb.camera_look("cmp", (nose.x + 0.14, nose.y - 0.70, nose.z), (nose.x, nose.y, nose.z - 0.012), 85)
scene.camera = cam


import json
import numpy as np
results = {}
lips = [v for v, g in [(v.index, [body.vertex_groups[x.group].name for x in v.groups]) for v in body.data.vertices[:13380]] if "lip.T.L.001" in g or "lip.B.L.001" in g]


def shot(name):
    scene.frame_set(1)
    ctrl.update_tag()
    bpy.context.scene.frame_set(1)
    vs = hb.evaluated_verts(body)
    results[name] = vs[:13380]
    scene.render.filepath = f"{prefix}_{name}.png"
    bpy.ops.render.render(write_still=True)


shot("neutral")
for s in ("mouthSmileLeft", "mouthSmileRight"):
    keys.key_blocks[s].value = 1.0
shot("arkit_smile")
for s in ("mouthSmileLeft", "mouthSmileRight"):
    keys.key_blocks[s].value = 0.0
for s in "LR":
    ctrl[f"m_zygomaticus_major_{s}"] = 1.0
    ctrl[f"m_orbicularis_oculi_orbital_{s}"] = 0.6
shot("muscle_smile")
n = results["neutral"]
corner = max(lips, key=lambda i: n[i, 0])
report = {}
for k in ("arkit_smile", "muscle_smile"):
    d = results[k] - n
    report[k] = {"corner_mm": (d[corner] * 1000).round(1).tolist(), "peak_mm": float(np.linalg.norm(d, axis=1).max() * 1000)}
json.dump(report, open(f"{prefix}_metrics.json", "w"))
print(report)
print("done")

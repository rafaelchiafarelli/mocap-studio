"""Skin corrections per joint, generated with tools and nothing sculpted. Run with --blend on a range_of_motion.py file. Args: rom.json out.blend out.json out.npz
Turns Blender's volume-preserving skinning on for the whole body, then tries Delta Mush at each joint and keeps it only where it measurably lowers the skin's collapse there.
Kept corrections become shape keys, one per side, driven by the joint's angle, and go in out.npz so apply_corrections.py can add them to another file of the same body."""
import json, os, sys
import bpy
import numpy as np
HERE = os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1]))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import corrections_common as cc
import hmblender as hb
import posed_mesh as pm
from hmcore import deltamush as dm

a = hb.args()
poses = {p["pose"]: p for p in json.load(open(a[0]))["poses"]}
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
scene = bpy.context.scene
pm.set_display(body, False)
scene.frame_set(1)
before_rest = pm.read(body)
tris = pm.triangles(body)
JOINT_NEAR = {"shoulder": ("upper_arm", 0.16), "elbow": ("forearm", 0.10), "knee": ("shin", 0.12), "hip": ("thigh", 0.20)}
JOINTS = {"shoulder": "bracos_acima_cabeca", "elbow": "cotovelo_dobrado", "knee": "joelho_dobrado", "hip": "quadril_flexionado"}
CANDIDATES = [(10, 0.5, 1.0), (25, 0.5, 1.0), (25, 0.5, 0.5), (50, 0.5, 0.5), (100, 0.5, 0.5)]  # iterations, step, how much of the correction
MAX_MM = 30.0
MIN_GAIN = 0.2  # percentage points of collapsed triangles that a correction must save


def centers(bone):
    M = np.array(rig.matrix_world)
    return [np.array(rig.data.bones[f"{bone}.{s}"].head_local) @ M[:3, :3].T + M[:3, 3] for s in "LR"]


def pose_at(frame):
    scene.frame_set(frame)
    return pm.read(body)


def report_all():
    rest = pose_at(1)
    out = {}
    for name, p in poses.items():
        bone, radius = {"shoulder": ("upper_arm", 0.16), "elbow": ("forearm", 0.10), "wrist": ("hand", 0.08), "knee": ("shin", 0.12), "hip": ("thigh", 0.20), "squat": ("thigh", 0.20), "trunk": (None, 0.25)}[p["joint"]]
        center = centers(bone)[0] if bone else np.array(rig.data.bones["spine.001"].head_local) + np.array(rig.matrix_world)[:3, 3]
        out[name] = pm.collapse(rest, pose_at(p["frame"]), pm_tris, center, radius)
    return out


pm_tris = tris
n_body = pm.N_BODY
baseline = report_all()
cc.preserve_volume(body, rig)
with_dqs = report_all()
rest = pose_at(1)
keep = {}
table = []
for joint, pose_name in JOINTS.items():
    bone, radius = JOINT_NEAR[joint]
    posed = pose_at(poses[pose_name]["frame"])
    near = centers(bone)
    mask = dm.falloff(rest[:n_body], near, radius)
    best = None
    before_share, before_p1 = pm.collapse(rest, posed, tris, near[0], radius)
    for it, step, amount in CANDIDATES:
        in_pose, in_rest = dm.correction(rest[:n_body], posed[:n_body], tris, it, step)
        trial = posed.copy()
        trial[:n_body] += amount * mask[:, None] * in_pose
        size = float(np.linalg.norm(amount * mask[:, None] * in_pose, axis=1).max() * 1000)
        share, p1 = pm.collapse(rest, trial, tris, near[0], radius)
        table.append({"joint": joint, "iterations": it, "amount": amount, "collapsed": share, "p1": p1, "max_mm": size})
        if size <= MAX_MM and (best is None or share < best[0]):
            best = (share, p1, it, amount, amount * mask[:, None] * in_rest)
    kept = best is not None and before_share - best[0] >= MIN_GAIN / 100
    print(f"{joint:9} antes {before_share:.2%}  melhor {best[0] if best else 1:.2%}  {'mantida' if kept else 'descartada'}")
    if kept:
        keep[joint] = best[4]
    table.append({"joint": joint, "before": before_share, "kept": bool(kept)})

scene.frame_set(1)
definitions = cc.drivers_for(rig, keep, poses, JOINTS, scene)
np.savez_compressed(a[3], **{f"delta_{k}": v.astype(np.float32) for k, v in keep.items()}, definitions=json.dumps(definitions), n_body=n_body)
cc.apply(body, rig, {k: v for k, v in keep.items()}, definitions, rest_x=rest[:n_body, 0])
bpy.context.view_layer.update()
after = report_all()
checks = {}
for joint, pose_name in JOINTS.items():
    if joint in keep:
        scene.frame_set(poses[pose_name]["frame"])
        bpy.context.view_layer.update()
        checks[joint] = {s: float(body.data.shape_keys.key_blocks[f"fix.{joint}.{s}"].value) for s in "LR"}
scene.frame_set(1)
pm.set_display(body, True)
bpy.ops.wm.save_as_mainfile(filepath=a[1])
json.dump({"as_built": baseline, "preserve_volume": with_dqs, "with_corrections": after, "kept": list(keep), "driver_values_at_pose": checks, "tried": table, "definitions": definitions}, open(a[2], "w"), indent=1)
print("{:22} {:>10} {:>10} {:>10}".format("pose", "antes", "volume", "correção"))
for name in sorted(baseline, key=lambda n: -baseline[n][0]):
    print(f"{name:22} {baseline[name][0]:10.2%} {with_dqs[name][0]:10.2%} {after[name][0]:10.2%}")
print("drivers", checks)

"""Keys a range-of-motion test on a clean body and reports where its skin collapses. Run with --blend. Args: out.blend out.json
Poses are rotations in the rest pose's axes (blender/posing.py), held for HOLD frames and reached in MOVE frames from the rest pose."""
import json, math, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posed_mesh as pm
import posing as P

a = hb.args()
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
MOVE, HOLD = 16, 8
arm_hang = {s: P.hang_angle(rig, f"upper_arm.{s}", 8.0) for s in "LR"}
leg_hang = {s: P.hang_angle(rig, f"thigh.{s}") for s in "LR"}
sign = {"L": 1, "R": -1}


def arm_down(s):
    return (f"upper_arm.{s}", P.ry(sign[s] * arm_hang[s]))


def forearm_bend(s, degrees):
    """Bends the forearm in the hanging upper arm's plane; its rest axis is first rebuilt straight, as walk.py does."""
    return (f"forearm.{s}", P.rx(-degrees) @ P.ry(sign[s] * (P.hang_angle(rig, f"forearm.{s}", 8.0) - arm_hang[s])))


def shin_bend(s, degrees):
    return (f"shin.{s}", P.rx(degrees) @ P.ry(sign[s] * (P.hang_angle(rig, f"shin.{s}") - leg_hang[s])))


POSES = [
    ("bracos_acima_cabeca", "shoulder", [(f"upper_arm.{s}", P.ry(-sign[s] * 150)) for s in "LR"]),
    ("braco_a_frente", "shoulder", [(f"upper_arm.{s}", P.rx(-85) @ P.ry(sign[s] * arm_hang[s])) for s in "LR"]),
    ("braco_para_tras", "shoulder", [(f"upper_arm.{s}", P.rx(45) @ P.ry(sign[s] * arm_hang[s])) for s in "LR"]),
    ("cotovelo_dobrado", "elbow", [arm_down(s) for s in "LR"] + [forearm_bend(s, 135) for s in "LR"]),
    ("antebraco_torcido", "wrist", [arm_down(s) for s in "LR"] + [(f"forearm.{s}", P.rz(sign[s] * 80)) for s in "LR"]),
    ("joelho_dobrado", "knee", [(f"thigh.{s}", P.rx(-60) @ P.ry(sign[s] * leg_hang[s])) for s in "LR"] + [shin_bend(s, 130) for s in "LR"]),
    ("quadril_flexionado", "hip", [(f"thigh.{s}", P.rx(-95) @ P.ry(sign[s] * leg_hang[s])) for s in "LR"]),
    ("perna_aberta", "hip", [(f"thigh.{s}", P.ry(-sign[s] * 45)) for s in "LR"]),
    ("agachamento", "squat", [(f"thigh.{s}", P.rx(-105) @ P.ry(sign[s] * leg_hang[s])) for s in "LR"] + [shin_bend(s, 115) for s in "LR"] + [(f"foot.{s}", P.rx(25)) for s in "LR"] + [arm_down(s) for s in "LR"]),
    ("tronco_girando", "trunk", [("spine", P.rz(20)), ("spine.001", P.rz(20)), ("spine.002", P.rz(20)), ("spine.003", P.rz(15))]),
    ("tronco_a_frente", "trunk", [("spine", P.rx(15)), ("spine.001", P.rx(15)), ("spine.002", P.rx(15)), ("spine.003", P.rx(10))]),
    ("tronco_de_lado", "trunk", [("spine", P.ry(-15)), ("spine.001", P.ry(-15)), ("spine.002", P.ry(-15)), ("spine.003", P.ry(-10))]),
]
JOINT_POINT = {"shoulder": "upper_arm.L", "elbow": "forearm.L", "wrist": "hand.L", "knee": "shin.L", "hip": "thigh.L", "squat": "thigh.L", "trunk": "spine.001"}
RADIUS = {"shoulder": 0.16, "elbow": 0.10, "wrist": 0.08, "knee": 0.12, "hip": 0.20, "squat": 0.20, "trunk": 0.25}

missing = sorted({b for _, _, rots in POSES for b, _ in rots if b not in rig.pose.bones})
if missing:
    raise SystemExit(f"missing bones: {missing}")

scene = bpy.context.scene
scene.render.fps = 24
pm.set_display(body, False)
P.reset(rig)
bpy.context.view_layer.update()
rest = pm.read(body)
tris = pm.triangles(body)
frame, report = 1, []
for name, joint, rotations in POSES:
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.keyframe_insert("rotation_quaternion", frame=frame)
    frame += MOVE
    P.reset(rig)
    for bone, rotation in rotations:
        P.set_rotation(rig, bone, rotation)
    for pb in rig.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        pb.keyframe_insert("rotation_quaternion", frame=frame + HOLD)
    bpy.context.view_layer.update()
    posed = pm.read(body)
    center = np.array(rig.data.bones[JOINT_POINT[joint]].head_local) + np.array(rig.matrix_world)[:3, 3]
    share, p1 = pm.collapse(rest, posed, tris, center, RADIUS[joint])
    report.append({"pose": name, "joint": joint, "frame": frame, "share_triangles_under_40pct": share, "area_ratio_p1": p1})
    print(f"{name:22} {joint:9} colapsados {share:6.2%}  p1 {p1:.2f}")
    frame += HOLD
for pb in rig.pose.bones:
    pb.rotation_quaternion = (1, 0, 0, 0)
    pb.keyframe_insert("rotation_quaternion", frame=frame + MOVE)
scene.frame_start, scene.frame_end = 1, frame + MOVE
pm.set_display(body, True)
bpy.ops.wm.save_as_mainfile(filepath=a[0])
report.sort(key=lambda r: -r["share_triangles_under_40pct"])
json.dump({"poses": report}, open(a[1], "w"), indent=1)
print("worst:", [r["pose"] for r in report[:6]])

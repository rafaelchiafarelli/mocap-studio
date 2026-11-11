"""Relaxed hands that answer to gravity and to the arm's swing. Run with --blend on a walking body. Args: out.blend out.json
The fingers curl as a hand at rest does. The wrist is a damped spring: the hand trails the forearm a little, settles towards hanging under its weight, and shakes slightly at each change of swing (initiative animation-body, Rafael 2026-11-11). Keyed on top of the walk; a later capture can replace the walk and keep these rules."""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

a = hb.args()
rig = bpy.data.objects["HM_rig"]
scene = bpy.context.scene
fps = scene.render.fps / scene.render.fps_base
# A relaxed hand: degrees per joint, from the knuckle out. By eye.
CURL = {"f_index": (12, 16, 8), "f_middle": (15, 20, 10), "f_ring": (18, 22, 12), "f_pinky": (22, 26, 14), "thumb": (4, 6, 4)}
CLOSE = {"f_index": 9, "f_ring": 6, "f_pinky": 13}  # degrees each finger turns towards the middle one at the knuckle: MPFB's rest hand spreads them
HZ, DAMPING = 2.5, 0.35  # the wrist's spring
HANG = 0.35  # how much of the forearm's tilt from vertical the hand gives back to gravity
MOST_DEG = 20.0


def curl_sign(name, side):
    """The local X turn of this finger bone that moves its fingertip towards the palm: the palms face the body in the rest pose, so towards the body's middle.
    Tested per bone, since a rig's bone rolls differ; the distance to the wrist can't tell, as a straight finger shortens it both ways."""
    finger = name.rsplit(".", 2)[0]
    tip_bone = rig.pose.bones[f"{finger}.03.{side}"]
    pb = rig.pose.bones[name]
    pb.rotation_mode = "QUATERNION"
    inward = -1.0 if side == "L" else 1.0  # +X is the body's left
    x = {}
    for sign in (1, -1):
        pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(15 * sign))
        bpy.context.view_layer.update()
        x[sign] = inward * (rig.matrix_world @ tip_bone.tail).x
    pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    return 1 if x[1] > x[-1] else -1


first, last = scene.frame_start, scene.frame_end
def close_sign(finger, side):
    """The local Z turn at the knuckle that brings this finger's tip towards the middle finger's tip."""
    pb = rig.pose.bones[f"{finger}.01.{side}"]
    tip = rig.pose.bones[f"{finger}.03.{side}"]
    middle = rig.matrix_world @ rig.pose.bones[f"f_middle.03.{side}"].tail
    pb.rotation_mode = "QUATERNION"
    d = {}
    for sign in (1, -1):
        pb.rotation_quaternion = Quaternion((0, 0, 1), math.radians(5 * sign))
        bpy.context.view_layer.update()
        d[sign] = (rig.matrix_world @ tip.tail - middle).length
    pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    return 1 if d[1] < d[-1] else -1


bpy.context.scene.frame_set(first)
saved = rig.data.pose_position
rig.data.pose_position = "REST"  # the palms face the body only in the rest pose
bpy.context.view_layer.update()
signs = {f"{finger}.0{i}.{s}": curl_sign(f"{finger}.0{i}.{s}", s) for s in "LR" for finger in CURL for i in (1, 2, 3) if f"{finger}.0{i}.{s}" in rig.pose.bones}
closing = {f"{finger}.{s}": close_sign(finger, s) for s in "LR" for finger in CLOSE}
rig.data.pose_position = saved
bpy.context.view_layer.update()
for f in range(first, last + 1):
    for s in "LR":
        for finger, angles in CURL.items():
            for i, deg in enumerate(angles, 1):
                name = f"{finger}.0{i}.{s}"
                if name in rig.pose.bones:
                    pb = rig.pose.bones[name]
                    pb.rotation_mode = "QUATERNION"
                    turn = Quaternion((1, 0, 0), math.radians(deg * signs[name]))
                    if i == 1 and finger in CLOSE:
                        turn = Quaternion((0, 0, 1), math.radians(CLOSE[finger] * closing[f"{finger}.{s}"])) @ turn
                    pb.rotation_quaternion = turn
                    if f in (first, last):
                        pb.keyframe_insert("rotation_quaternion", frame=f)

# The forearm's tilt forwards in the walk, frame by frame: the angle of its direction from straight down, about the body's left-right axis.
tilt = {s: [] for s in "LR"}
for f in range(first, last + 1):
    scene.frame_set(f)
    for s in "LR":
        pb = rig.pose.bones[f"forearm.{s}"]
        d = rig.matrix_world.to_3x3() @ (pb.tail - pb.head)
        tilt[s].append(math.atan2(-d.y, -d.z))
omega = 2 * math.pi * HZ
steps = 20
dt = 1.0 / (fps * steps)
report = {}
for s in "LR":
    p = np.unwrap(np.array(tilt[s]))
    q, v = p[0] * (1 - HANG), 0.0
    out = []
    for i in range(len(p)):
        target = p[i] * (1 - HANG)  # under gravity the hand hangs a little closer to vertical than the forearm
        for _ in range(steps):
            acc = -omega * omega * (q - target) - 2 * DAMPING * omega * v
            v += dt * acc
            q += dt * v
        out.append(q - p[i])
    rel = np.clip(np.degrees(np.array(out)), -MOST_DEG, MOST_DEG)
    report[s] = {"largest_deg": float(np.abs(rel).max()), "mean_deg": float(np.abs(rel).mean())}
    for i, f in enumerate(range(first, last + 1)):
        scene.frame_set(f)
        pb = rig.pose.bones[f"hand.{s}"]
        head = pb.head.copy()
        turn = Matrix.Translation(head) @ Matrix.Rotation(-math.radians(rel[i]), 4, "X") @ Matrix.Translation(-head)
        pb.matrix = turn @ pb.matrix
        bpy.context.view_layer.update()
        pb.keyframe_insert("rotation_quaternion", frame=f)
scene.frame_set(first)
bpy.ops.wm.save_as_mainfile(filepath=a[0])
json.dump({"wrist": report, "curl_sign": signs}, open(a[1], "w"), indent=1)
print(json.dumps(report), "curl signs", sorted(set(signs.values())))

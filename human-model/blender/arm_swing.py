"""A live elbow in the walk's arm swing. Run with --blend on a walking body. Args: out.blend out.json
The walk's data has no arms, so blender/walk.py swings them 18 degrees with the elbow held at 18. Walking people bend the elbow more as the arm swings forward and open it as it goes back:
here the bend follows the upper arm's swing a frame late, from LEAST_DEG behind to MOST_DEG in front (by eye, Rafael 2026-11-11). Until a capture brings real arms."""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Quaternion
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

a = hb.args()
rig = bpy.data.objects["HM_rig"]
scene = bpy.context.scene
fps = scene.render.fps / scene.render.fps_base
LEAST_DEG, MOST_DEG = 12.0, 38.0
WALK_BEND_DEG = 18.0  # blender/walk.py's FOREARM_BEND_DEG
SWING_DEG = 18.0  # blender/walk.py's ARM_SWING_DEG


def flex_sign(side):
    """The forearm's local X turn that bends the elbow, bringing the hand forward, on this rig."""
    pb = rig.pose.bones[f"forearm.{side}"]
    saved = pb.rotation_quaternion.copy()
    y = {}
    for sign in (1, -1):
        pb.rotation_quaternion = saved @ Quaternion((1, 0, 0), math.radians(10 * sign))
        bpy.context.view_layer.update()
        y[sign] = (rig.matrix_world @ rig.pose.bones[f"hand.{side}"].head).y
    pb.rotation_quaternion = saved
    bpy.context.view_layer.update()
    return 1 if y[1] < y[-1] else -1  # forward is -Y


first, last = scene.frame_start, scene.frame_end
scene.frame_set(first)
signs = {s: flex_sign(s) for s in "LR"}
forward = {s: [] for s in "LR"}
for f in range(first, last + 1):
    scene.frame_set(f)
    for s in "LR":
        pb = rig.pose.bones[f"upper_arm.{s}"]
        d = rig.matrix_world.to_3x3() @ (pb.tail - pb.head)
        forward[s].append(math.degrees(math.atan2(-d.y, -d.z)))
report = {}
for s in "LR":
    fwd = np.array(forward[s])
    lagged = np.concatenate([fwd[:1], fwd[:-1]])
    centre = np.median(fwd)
    share = np.clip((lagged - centre + SWING_DEG) / (2 * SWING_DEG), 0, 1)
    bend = LEAST_DEG + (MOST_DEG - LEAST_DEG) * share
    # the walk eases its swing to nothing as it stops; the elbow eases to the walk's own bend with it, by how wide the swing is over about a second
    half = int(fps * 0.5)
    width = np.array([np.ptp(fwd[max(0, i - half): i + half + 1]) for i in range(len(fwd))])
    amount = np.clip(width / (2 * SWING_DEG), 0, 1)
    bend = WALK_BEND_DEG + (bend - WALK_BEND_DEG) * amount
    report[s] = {"least_deg": float(bend.min()), "most_deg": float(bend.max())}
    for i, f in enumerate(range(first, last + 1)):
        scene.frame_set(f)
        pb = rig.pose.bones[f"forearm.{s}"]
        pb.rotation_quaternion = pb.rotation_quaternion @ Quaternion((1, 0, 0), math.radians((bend[i] - WALK_BEND_DEG) * signs[s]))
        pb.keyframe_insert("rotation_quaternion", frame=f)
scene.frame_set(first)
bpy.ops.wm.save_as_mainfile(filepath=a[0])
json.dump({"elbow": report, "flex_sign": signs}, open(a[1], "w"), indent=1)
print(json.dumps(report), signs)

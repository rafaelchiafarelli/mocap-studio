"""Keys the walking cycle from measured angles. Args: gait.json SEX out.blend [cycles]. Run with --blend. Trunk and arms aren't in the data: declared. The root is solved so the stance foot stays planted."""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posing as P

a = hb.args()
gait = json.load(open(a[0]))[a[1]]
out = a[2]
cycles = int(a[3]) if len(a) > 3 else 3
rig = bpy.data.objects["HM_rig"]
cols = gait["columns"]
mean = np.array(gait["mean"])
col = lambda n: mean[:, cols.index(n)]
FPS = 24
scene = bpy.context.scene
scene.render.fps = FPS
frames_per_cycle = round(gait["cycle_s"] * FPS)
ARM_SWING_DEG = 18.0  # declared
leg_hang = {s: P.hang_angle(rig, f"thigh.{s}") for s in "LR"}
shin_hang = {s: P.hang_angle(rig, f"shin.{s}") for s in "LR"}
arm_hang = {s: P.hang_angle(rig, f"upper_arm.{s}", 8.0) for s in "LR"}
FOREARM_BEND_DEG = 18.0  # declared: a relaxed elbow while walking


def forearm_rotation(side):
    """Brings the rest pose's forward-bent forearm back to a relaxed bend, in the hanging upper arm's frame."""
    d = P.direction(rig, f"forearm.{side}")
    current = math.degrees(math.atan2(-d.y, math.hypot(d.x, d.z)))
    sgn = 1 if side == "L" else -1
    return P.rx(current - FOREARM_BEND_DEG) @ P.ry(sgn * (P.hang_angle(rig, f"forearm.{side}", 8.0) - arm_hang[side]))


def sample(name, phase):
    i = (phase % 1.0) * 100.0
    k = int(i)
    return float(col(name)[k] * (1 - (i - k)) + col(name)[min(k + 1, 100)] * (i - k))


def pose(phase):
    right, left = phase, phase + 0.5
    obliq, rot = sample("RPelvisAngleX", right), sample("RPelvisAngleY", right)
    P.set_rotation(rig, "spine", P.ry(obliq) @ P.rz(rot))
    if "spine.002" in rig.pose.bones:
        P.set_rotation(rig, "spine.002", (P.ry(obliq) @ P.rz(rot)).inverted() @ P.rz(-rot * 0.8))
    for side, ph, sgn in (("R", right, -1), ("L", left, 1)):
        x = side
        hip_f = sample(f"{x}HipAngleZ", ph)
        add = sample(f"{x}HipAngleX", ph)
        knee = sample(f"{x}KneeAngleZ", ph)
        ankle = sample(f"{x}AnkleAngleZ", ph)
        P.set_rotation(rig, f"thigh.{side}", P.rx(-hip_f) @ P.ry(sgn * (leg_hang[side] + add)))
        # the shin continues from the thigh's hang: its own rest axis is rebuilt straight
        P.set_rotation(rig, f"shin.{side}", P.rx(knee) @ P.ry(sgn * (shin_hang[side] - leg_hang[side])))
        P.set_rotation(rig, f"foot.{side}", P.rx(-ankle))
        swing = ARM_SWING_DEG * math.sin(2 * math.pi * (ph + 0.5 - 0.1))
        P.set_rotation(rig, f"upper_arm.{side}", P.rx(swing) @ P.ry(sgn * arm_hang[side]))
        P.set_rotation(rig, f"forearm.{side}", forearm_rotation(side))


def foot_points():
    bpy.context.view_layer.update()
    pts = {}
    M = rig.matrix_world
    for s in "LR":
        heel = rig.pose.bones[f"foot.{s}"].head
        toe = rig.pose.bones[f"toe.{s}"].tail
        ball = rig.pose.bones[f"toe.{s}"].head
        pts[s] = (Vector(heel), Vector(ball), Vector(toe))
    return pts


total = frames_per_cycle * cycles
rest_low = 0.008
# first pass: pose per frame, read where the feet are, solve the root
root = np.zeros((total + 1, 2))
y = 0.0
prev = None
for f in range(total + 1):
    pose(f / frames_per_cycle)
    pts = foot_points()
    # the ankle is well above the ground, so height compares heel (under the ankle) and ball
    low = {s: min(pts[s][0].z - 0.065, pts[s][1].z - 0.008, pts[s][2].z) for s in "LR"}
    stance = min(low, key=low.get)
    k = 1 if pts[stance][1].z - 0.008 < pts[stance][0].z - 0.065 else 0
    if prev is not None:
        # the same point of the same foot in both frames, or the heel-to-ball hand-over would count as motion
        y += prev[stance][k].y - pts[stance][k].y
    prev = {s: tuple(p.copy() for p in pts[s]) for s in "LR"}
    root[f] = (y, -low[stance])
for f in range(total + 1):
    pose(f / frames_per_cycle)
    for pb_name in ["spine", "spine.002"] + [f"{b}.{s}" for s in "LR" for b in ("thigh", "shin", "foot", "upper_arm", "forearm")]:
        if pb_name in rig.pose.bones:
            rig.pose.bones[pb_name].keyframe_insert("rotation_quaternion", frame=f + 1)
    rig.location = (0, root[f][0], root[f][1])
    rig.keyframe_insert("location", frame=f + 1)
scene.frame_start, scene.frame_end = 1, total + 1
stride = abs(root[frames_per_cycle][0] - root[0][0])
speed = stride / gait["cycle_s"]
print(f"stride {stride:.3f} m speed {speed:.3f} m/s bounce {np.ptp(root[:, 1])*100:.1f} cm")
rig["hm_walk"] = {"stride_m": float(stride), "speed_ms": float(speed), "bounce_cm": float(np.ptp(root[:, 1]) * 100)}
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)

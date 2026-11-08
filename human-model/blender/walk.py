"""Keys the walking cycle from measured angles. Args: gait.json SEX out.blend [cycles] [stop_steps]. Run with --blend. stop_steps more steps, shorter and slower each, end it standing. Trunk and arms aren't in the data: declared.
The hip angles have the pelvis's tilt taken off, the toes roll at push-off, the root follows a soft contact between the feet, and each stance foot
is planted by a small correction of its leg (task muscle-physics/body-walk/2). Prints stride, speed, bounce and how far the legs were corrected."""
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
stop_steps = int(a[4]) if len(a) > 4 else 0
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
amount = 1.0  # how much of the measured motion is in the pose: 1 walking, falling to 0 as the walk slows to standing
FOREARM_BEND_DEG = 18.0  # declared: a relaxed elbow while walking
STOP_SLOWER = 1.5  # declared: the stopping steps take this many times as long as walking steps, so the rate slows from the walk's to half of it
TOE_MAX_DEG = 55.0  # declared: the most the toes bend up at push-off; the measured metatarsophalangeal peak is about 50


def pitch(bone):
    """How far a posed bone points above horizontal, in degrees, in the rig's own frame."""
    pb = rig.pose.bones[bone]
    d = pb.tail - pb.head
    return math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))


def toe_rest_pitch(side):
    d = rig.data.bones[f"toe.{side}"].tail_local - rig.data.bones[f"toe.{side}"].head_local
    return math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))


def roll_toes(side):
    """The foot rolls over the ball, not the toes' tips: when the heel lifts, the toes bend up until they lie as they do standing.
    The data has no toe angle, and with rigid toes the trailing foot stood on its tips at push-off and lifted the body 5 cm
    at every hand-over (bug human-model/5)."""
    P.set_rotation(rig, f"toe.{side}", Matrix.Identity(3))
    bpy.context.view_layer.update()
    deficit = toe_rest_pitch(side) - pitch(f"toe.{side}")
    if deficit <= 0:
        return
    bend = min(deficit, TOE_MAX_DEG)
    P.set_rotation(rig, f"toe.{side}", P.rx(bend))
    bpy.context.view_layer.update()
    if pitch(f"toe.{side}") < toe_rest_pitch(side) - deficit:  # turned the wrong way
        P.set_rotation(rig, f"toe.{side}", P.rx(-bend))


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


def pose(phase, fix=None):
    """The measured pose at a phase of the right leg's cycle; fix adds (hip, knee, ankle) degrees per side, from planting the feet."""
    right, left = phase, phase + 0.5
    obliq, rot = amount * sample("RPelvisAngleX", right), amount * sample("RPelvisAngleY", right)
    P.set_rotation(rig, "spine", P.ry(obliq) @ P.rz(rot))
    if "spine.002" in rig.pose.bones:
        P.set_rotation(rig, "spine.002", (P.ry(obliq) @ P.rz(rot)).inverted() @ P.rz(-rot * 0.8))
    for side, ph, sgn in (("R", right, -1), ("L", left, 1)):
        set_leg(side, ph, (fix or {}).get(side, (0.0, 0.0, 0.0)))
        swing = amount * ARM_SWING_DEG * math.sin(2 * math.pi * (ph + 0.5 - 0.1))
        P.set_rotation(rig, f"upper_arm.{side}", P.rx(swing) @ P.ry(sgn * arm_hang[side]))
        P.set_rotation(rig, f"forearm.{side}", forearm_rotation(side))


def set_leg(side, ph, d):
    sgn = -1 if side == "R" else 1
    # the data's hip angle is the thigh against the pelvis, which tilts forward about 10 degrees; the rig's rest pelvis is level,
    # so the tilt is taken off, or the thigh flexes 10 degrees too far and the stance foot never lies flat (bug human-model/5)
    hip_f = amount * (sample(f"{side}HipAngleZ", ph) - sample(f"{side}PelvisAngleZ", ph)) + d[0]
    add = amount * sample(f"{side}HipAngleX", ph)
    knee = max(amount * sample(f"{side}KneeAngleZ", ph) + d[1], 0.0)  # never past straight
    ankle = amount * sample(f"{side}AnkleAngleZ", ph) + d[2]
    P.set_rotation(rig, f"thigh.{side}", P.rx(-hip_f) @ P.ry(sgn * (leg_hang[side] + add)))
    # the shin continues from the thigh's hang: its own rest axis is rebuilt straight
    P.set_rotation(rig, f"shin.{side}", P.rx(knee) @ P.ry(sgn * (shin_hang[side] - leg_hang[side])))
    P.set_rotation(rig, f"foot.{side}", P.rx(-ankle))
    roll_toes(side)


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


walking = frames_per_cycle * cycles
stop_cycles = stop_steps / 2  # a cycle is two steps
n_stop = round(STOP_SLOWER * frames_per_cycle * stop_cycles)
total = walking + n_stop


def phase_at(f):
    """Phase of the cycle at frame f. While stopping it starts at the walk's own rate and slows down."""
    if f <= walking:
        return f / frames_per_cycle
    u = (f - walking) / n_stop
    return cycles + stop_cycles * (STOP_SLOWER * u + (1 - STOP_SLOWER) * u * u)


def amount_at(f):
    """The share of the measured motion at frame f, easing from all of it to none as the walk stops."""
    if f <= walking:
        return 1.0
    u = (f - walking) / n_stop
    return 1.0 - (3 * u * u - 2 * u * u * u)


CONTACT_MM = 4.0  # declared: points this close to the lowest share the contact, so the hand-over between feet is spread over frames
OFFSETS = (0.065, 0.008, 0.0)  # heel, ball, toe: the ankle is well above the ground, so height compares heel (under the ankle) and ball


def contact(pts):
    """Every foot point's height above its sole, and its share of the contact: a soft minimum, so the share moves smoothly from one point
    to the next instead of jumping to whichever is lowest (bug human-model/5, a 27 mm jump in one frame at each hand-over)."""
    h = np.array([pts[s][i].z - OFFSETS[i] for s in "LR" for i in range(3)])
    w = np.exp(-(h - h.min()) / (CONTACT_MM / 1000))
    w /= w.sum()
    return h, w


# first pass: pose per frame, read where the feet are, solve the root so the contact neither sinks nor slides
root = np.zeros((total + 1, 2))
y = 0.0
prev = None
for f in range(total + 1):
    amount = amount_at(f)
    pose(phase_at(f))
    pts = foot_points()
    h, w = contact(pts)
    ys = np.array([pts[s][i].y for s in "LR" for i in range(3)])
    if prev is not None:
        # each point's own motion, weighted by its share in both frames
        y += float(((prev[1] + w) / 2) @ (prev[0] - ys))
    prev = (ys, w)
    root[f] = (y, -float(h @ w))

# Second pass: the root keeps that path, and each foot bearing weight is planted by inverse kinematics on its leg. A foot point
# that touches the floor keeps the place where it touched until the foot leaves; the leg's hip, knee and ankle are corrected from the
# measured angles until the foot's contact sits there, on the floor, at the foot's measured pitch. The swing leg keeps the data.
TOE_OFF = 0.61  # declared: stance from heel strike (phase 0 of each leg's cycle) to toe-off, about 61% of the cycle (Perry)
PHASE = {"R": 0.0, "L": 0.5}


def foot_contact(side):
    """The foot's contact: its points' world (y, height above the sole) and their soft-minimum shares within this foot."""
    bpy.context.view_layer.update()
    pb = rig.pose.bones
    loc = rig.location
    pts = [pb[f"foot.{side}"].head, pb[f"toe.{side}"].head, pb[f"toe.{side}"].tail]
    y = np.array([p.y + loc.y for p in pts])
    h = np.array([p.z + loc.z - OFFSETS[i] for i, p in enumerate(pts)])
    w = np.exp(-(h - h.min()) / (CONTACT_MM / 1000))
    return y, h, w / w.sum()


def plant(side, ph, target_pitch, target_h, plants, d):
    """Corrects (hip, knee, ankle) until the contact is on its planted place, at target_h (the measured pose's own height, which
    already meets the floor once the pelvis's tilt is taken off), with the foot at target_pitch: only the slide is taken out.
    Bringing the heel down at heel strike too (it lands up to 20 mm short) bent the knee 30 degrees off the data: walk_root/v10."""
    def residual(dd):
        set_leg(side, ph, dd)
        y, h, w = foot_contact(side)
        known = [i for i in range(3) if plants[i] is not None]
        wk = w[known] / w[known].sum() if known else None
        ry = float(wk @ (y[known] - np.array([plants[i] for i in known]))) if known else 0.0
        return np.array([ry * 1000, (float(w @ h) - target_h) * 1000, pitch(f"foot.{side}") - target_pitch])
    d = np.array(d, float)
    for _ in range(8):
        r = residual(d)
        if np.abs(r[:2]).max() < 0.3 and abs(r[2]) < 0.3:
            break
        J = np.column_stack([(residual(d + e) - r) / 0.5 for e in np.eye(3) * 0.5])
        d = d - np.linalg.solve(J.T @ J + 0.05 * np.eye(3), J.T @ r)
        d = np.clip(d, -30, 30)
    r = residual(d)
    return d, r


fixes = {s: np.zeros((total + 1, 3)) for s in "LR"}
left_over = {s: np.zeros((total + 1, 2)) for s in "LR"}
plants = {s: [None, None, None] for s in "LR"}
last = {s: np.zeros(3) for s in "LR"}
for f in range(total + 1):
    phase = phase_at(f)
    amount = amount_at(f)
    rig.location = (0, root[f][0], root[f][1])
    pose(phase)
    for side in "LR":
        ph = (phase + PHASE[side]) % 1.0
        if ph >= TOE_OFF:
            plants[side] = [None, None, None]
            last[side] = np.zeros(3)
            continue
        set_leg(side, ph, (0.0, 0.0, 0.0))
        bpy.context.view_layer.update()
        target_pitch = pitch(f"foot.{side}")
        _, h0, w0 = foot_contact(side)
        d, r = plant(side, ph, target_pitch, float(w0 @ h0), plants[side], last[side])
        y, h, w = foot_contact(side)
        for i in range(3):
            if plants[side][i] is None and w[i] > 0.3 and h[i] < 0.002:
                plants[side][i] = float(y[i])  # this point has touched: it stays here until the foot leaves
        fixes[side][f], left_over[side][f], last[side] = d, r[:2], d
    pose(phase, {s: fixes[s][f] for s in "LR"})
    for pb_name in ["spine", "spine.002"] + [f"{b}.{s}" for s in "LR" for b in ("thigh", "shin", "foot", "toe", "upper_arm", "forearm")]:
        if pb_name in rig.pose.bones:
            rig.pose.bones[pb_name].keyframe_insert("rotation_quaternion", frame=f + 1)
    rig.keyframe_insert("location", frame=f + 1)
allfix = np.abs(np.vstack([fixes[s] for s in "LR"]))
planted = np.vstack([left_over[s][np.any(fixes[s] != 0, axis=1)] for s in "LR"])
if len(planted):
    print("planting: largest change hip %.1f knee %.1f ankle %.1f deg; mean %.1f %.1f %.1f; contact left off by up to %.1f mm along, %.1f mm in height" % (
        *allfix.max(axis=0), *allfix.mean(axis=0), np.abs(planted[:, 0]).max(), np.abs(planted[:, 1]).max()))
scene.frame_start, scene.frame_end = 1, total + 1
stride = abs(root[frames_per_cycle][0] - root[0][0])
speed = stride / gait["cycle_s"]
print(f"stride {stride:.3f} m speed {speed:.3f} m/s bounce {np.ptp(root[:, 1])*100:.1f} cm")
rig["hm_walk"] = {"stride_m": float(stride), "speed_ms": float(speed), "bounce_cm": float(np.ptp(root[:, 1]) * 100)}
bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)

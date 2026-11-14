"""Step 3 of the pose-capture investigation: keys MediaPipe's world landmarks onto the rigged body, with no physics.

    python3 human-model/blender_run.py --blend 02_corpo_com_rig.blend human-model/investigations/pose-capture/drive_capture.py LANDMARKS.npz OUT.blend REPORT.json [SIGMA_FRAMES] [--no-head]

LANDMARKS.npz is capture_pose.py's (one camera) or two_cameras.py's (two). With two, the root's path on the floor is the
captured hips', scaled by hip height to this body; --no-head keeps the head on the chest.

Motion is carried as directions and frames, never positions, so the body keeps its own proportions.

Axes. MediaPipe's world landmarks: x to the image's right, y down, z away from the camera, origin between the hips; its names
are the person's own sides. The body (MPFB) faces -Y with its left (.L) on +X and Z up. The map is (x, y, z) -> (x, z, -y),
a proper rotation (determinant +1), so nothing is mirrored and a landmark named left drives a .L bone. `side_check` below
verifies it on every frame: the captured left shoulder and the posed shoulder.L must be on the same side of the trunk.

Per frame:
- pelvis (`spine`): a frame from the hip line and the line from mid-hip to mid-shoulder;
- chest: the same from the shoulder line; the turn from pelvis to chest is shared equally by spine.001 to spine.004;
- head: a frame from the ears and the nose, its turn from the chest shared by spine.005 and spine.006; the nose sits
  `NOSE_PITCH_DEG` below the ears' level on a level head (by eye);
- thigh and upper arm: shortest swing onto the captured direction, then twisted about their own axis so the knee or elbow bends
  in the captured plane (faded in from 10 to 30 degrees of bend, since a straight limb has no plane);
- shin and forearm: shortest swing; foot: the sole (heel to toe) onto the captured heel to toe; hand: onto wrist to the
  middle of index and pinky, turned so index and pinky lie across it. Fingers, toes and shoulders stay at rest.
- root: lowered or raised so the lowest point of either foot stays on the floor; horizontally, with one camera, the lower
  foot is held still while it is the lower one (a contact, not a rule per pose), so the body travels as its feet allow;
  with two cameras, it follows the captured hips.
Gaps (frames with no capture) are filled by interpolation before smoothing.
Landmarks are smoothed in time first by a gaussian of SIGMA_FRAMES (default 2 frames, at 60 fps).
"""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
NO_HEAD = "--no-head" in argv  # the head follows the chest (a view that loses the head guesses it badly)
argv = [a for a in argv if a != "--no-head"]
npz, out, report_path = argv[0], argv[1], argv[2]
SIGMA = float(argv[3]) if len(argv) > 3 else 2.0
NOSE_PITCH_DEG = 10.0  # by eye: on a level head the nose tip is a little below the ears
HINGE_FADE_DEG = (10.0, 30.0)

d = np.load(npz)
fps = float(d["fps"])
mp = d["world"].astype(float)  # T, 33, 3


def smooth(x, sigma):
    if sigma <= 0:
        return x
    r = int(3 * sigma)
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.concatenate([np.repeat(x[:1], r, 0), x, np.repeat(x[-1:], r, 0)])
    return np.stack([np.tensordot(k, pad[i:i + 2 * r + 1], axes=(0, 0)) for i in range(len(x))])


def fill_gaps(x):
    """Frames with no capture take the line between their neighbours, so smoothing doesn't spread NaN."""
    x = x.copy()
    t = np.arange(len(x))
    flat = x.reshape(len(x), -1)
    for k in range(flat.shape[1]):
        ok = np.isfinite(flat[:, k])
        if ok.any() and not ok.all():
            flat[:, k] = np.interp(t, t[ok], flat[ok, k])
    return flat.reshape(x.shape)


mp = smooth(fill_gaps(mp), SIGMA)
# two cameras give where the hips really went (two_cameras.py's points_m, metres, Blender axes)
HIPS_M = None
if "points_m" in d.files:
    pm = smooth(fill_gaps(d["points_m"].astype(float)), SIGMA)
    HIPS_M = (pm[:, 23] + pm[:, 24]) / 2
B = np.stack([mp[..., 0], mp[..., 2], -mp[..., 1]], -1)  # (x, z, -y): proper rotation, no mirror
NAMES = dict(nose=0, ear_l=7, ear_r=8, sh_l=11, sh_r=12, el_l=13, el_r=14, wr_l=15, wr_r=16, pinky_l=17, pinky_r=18,
             index_l=19, index_r=20, hip_l=23, hip_r=24, knee_l=25, knee_r=26, ank_l=27, ank_r=28, heel_l=29, heel_r=30,
             toe_l=31, toe_r=32)

rig = bpy.data.objects["HM_rig"]
scene = bpy.context.scene
scene.render.fps = int(round(fps))
scene.frame_start, scene.frame_end = 1, len(B)
P, R = rig.pose.bones, rig.data.bones
for pb in P:
    pb.rotation_mode = "QUATERNION"


def V(t, n):
    return Vector(B[t, NAMES[n]])


def frame_from(x, up):
    """Columns X (to the left), Y (back), Z (up): the body's own axes at rest."""
    x = x.normalized()
    z = (up - up.dot(x) * x).normalized()
    y = z.cross(x)
    return Matrix((x, y, z)).transposed()


def set_world_rot(name, rot):
    """Bone's armature-space rotation becomes rot @ its rest rotation, head kept."""
    pb = P[name]
    head = pb.head.copy()
    pb.matrix = Matrix.Translation(head) @ (rot @ R[name].matrix_local.to_3x3()).to_quaternion().to_matrix().to_4x4()
    bpy.context.view_layer.update()


def cur(name):
    return P[name].matrix.to_3x3()


def swing(name, rest_vec_local, target):
    """Turn the bone by the shortest rotation that takes its vector (in its rest local axes) onto target."""
    now = (cur(name) @ rest_vec_local).normalized()
    rot = now.rotation_difference(target.normalized()).to_matrix()
    head = P[name].head.copy()
    P[name].matrix = Matrix.Translation(head) @ (rot @ cur(name)).to_quaternion().to_matrix().to_4x4()
    bpy.context.view_layer.update()


def twist(name, axis, angle):
    rot = Quaternion(axis.normalized(), angle).to_matrix()
    head = P[name].head.copy()
    P[name].matrix = Matrix.Translation(head) @ (rot @ cur(name)).to_quaternion().to_matrix().to_4x4()
    bpy.context.view_layer.update()


Y = Vector((0, 1, 0))


def rest_bend_sign(upper, lower):
    """Which way, about the upper bone's X axis, the joint bends at rest (MPFB's A-pose has knees and elbows a little bent)."""
    u = (R[upper].tail_local - R[upper].head_local).normalized()
    l = (R[lower].tail_local - R[lower].head_local).normalized()
    n = u.cross(l)
    xs = R[upper].matrix_local.col[0].to_3d()
    return 1.0 if n.dot(xs) >= 0 else -1.0


def hinge(upper, lower_target, sign):
    """Twist the upper bone about itself so its X axis is the captured bend's normal."""
    u = (cur(upper) @ Y).normalized()
    n = u.cross(lower_target.normalized())
    bend = math.degrees(math.asin(min(1.0, n.length)))
    if u.dot(lower_target.normalized()) < 0:
        bend = 180 - bend
    w = min(1.0, max(0.0, (bend - HINGE_FADE_DEG[0]) / (HINGE_FADE_DEG[1] - HINGE_FADE_DEG[0])))
    if w == 0:
        return
    n = (sign * n).normalized()
    xb = (cur(upper) @ Vector((1, 0, 0))).normalized()
    ang = math.atan2(u.dot(xb.cross(n)), xb.dot(n))
    twist(upper, u, w * ang)


SIGNS = {s: (rest_bend_sign(f"thigh.{s}", f"shin.{s}"), rest_bend_sign(f"upper_arm.{s}", f"forearm.{s}")) for s in "LR"}
# the sole at rest, in the foot bone's local axes: from heel.02 towards the toe's tail, flattened to the floor
SOLE = {}
HAND_ACROSS = {}
for s in "LR":
    sole = R[f"toe.{s}"].tail_local - (R[f"heel.02.{s}"].head_local + R[f"heel.02.{s}"].tail_local) / 2
    sole.z = 0
    SOLE[s] = R[f"foot.{s}"].matrix_local.to_3x3().inverted() @ sole.normalized()
    across = R[f"f_index.01.{s}"].head_local - R[f"f_pinky.01.{s}"].head_local
    HAND_ACROSS[s] = R[f"hand.{s}"].matrix_local.to_3x3().inverted() @ across.normalized()

CHAIN_CHEST = ["spine.001", "spine.002", "spine.003", "spine.004"]
CHAIN_HEAD = ["spine.005", "spine.006"]
FOOT_POINTS = {s: [(f"toe.{s}", "tail"), (f"heel.02.{s}", "head"), (f"heel.02.{s}", "tail"), (f"foot.{s}", "tail")] for s in "LR"}
rest_floor = min(getattr(R[b], f"{e}_local").z for s in "LR" for b, e in FOOT_POINTS[s])
L2 = {"L": "l", "R": "r"}


def foot_low(s):
    pts = [rig.matrix_world @ getattr(P[b], e) for b, e in FOOT_POINTS[s]]
    return min(pts, key=lambda p: p.z)


BODY_HIP_H = (R["thigh.L"].head_local.z + R["thigh.R"].head_local.z) / 2
CAPTURED_HIP_H = float(np.median(HIPS_M[:, 2])) if HIPS_M is not None else None
report = {"no_head": NO_HEAD, "root_from": "two cameras' hips" if HIPS_M is not None else "lower foot held still",
          "frames": len(B), "fps": fps, "sigma_frames": SIGMA, "side_check_failures": [], "stance": []}
root = Vector((0, 0, 0))
anchor = None  # (side, world xy of its lowest point)
for t in range(len(B)):
    for pb in P:
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)  # pb.matrix writes leave rounding scale behind; unreset, it grew frame by frame (the left foot's toe reached 1.5 m)
    rig.location = (0, 0, 0)
    bpy.context.view_layer.update()

    pelvis = frame_from(V(t, "hip_l") - V(t, "hip_r"), (V(t, "sh_l") + V(t, "sh_r")) / 2 - (V(t, "hip_l") + V(t, "hip_r")) / 2)
    chest = frame_from(V(t, "sh_l") - V(t, "sh_r"), (V(t, "sh_l") + V(t, "sh_r")) / 2 - (V(t, "hip_l") + V(t, "hip_r")) / 2)
    ears = (V(t, "ear_l") + V(t, "ear_r")) / 2
    fwd = V(t, "nose") - ears
    hx = (V(t, "ear_l") - V(t, "ear_r")).normalized()
    fwd = (fwd - fwd.dot(hx) * hx).normalized()
    fwd = Quaternion(hx, math.radians(NOSE_PITCH_DEG)) @ fwd  # undo the nose's natural drop
    head = Matrix((hx, -fwd, hx.cross(-fwd))).transposed()

    set_world_rot("spine", pelvis)
    qp, qc, qh = pelvis.to_quaternion(), chest.to_quaternion(), head.to_quaternion()
    for i, name in enumerate(CHAIN_CHEST):
        set_world_rot(name, qp.slerp(qc, (i + 1) / len(CHAIN_CHEST)).to_matrix())
    for i, name in enumerate(CHAIN_HEAD):
        set_world_rot(name, (qc if NO_HEAD else qc.slerp(qh, (i + 1) / len(CHAIN_HEAD))).to_matrix())

    for s in "LR":
        k = L2[s]
        thigh, shin = V(t, f"knee_{k}") - V(t, f"hip_{k}"), V(t, f"ank_{k}") - V(t, f"knee_{k}")
        swing(f"thigh.{s}", Y, thigh)
        hinge(f"thigh.{s}", shin, SIGNS[s][0])
        swing(f"shin.{s}", Y, shin)
        swing(f"foot.{s}", SOLE[s], V(t, f"toe_{k}") - V(t, f"heel_{k}"))
        upper, fore = V(t, f"el_{k}") - V(t, f"sh_{k}"), V(t, f"wr_{k}") - V(t, f"el_{k}")
        swing(f"upper_arm.{s}", Y, upper)
        hinge(f"upper_arm.{s}", fore, SIGNS[s][1])
        swing(f"forearm.{s}", Y, fore)
        knuckles = (V(t, f"index_{k}") + V(t, f"pinky_{k}")) / 2 - V(t, f"wr_{k}")
        swing(f"hand.{s}", Y, knuckles)
        across = V(t, f"index_{k}") - V(t, f"pinky_{k}")
        a = (cur(f"hand.{s}") @ Y).normalized()
        across = across - across.dot(a) * a
        now = cur(f"hand.{s}") @ HAND_ACROSS[s]
        now = now - now.dot(a) * a
        if across.length > 1e-4 and now.length > 1e-4:
            twist(f"hand.{s}", a, math.atan2(a.dot(now.normalized().cross(across.normalized())), now.normalized().dot(across.normalized())))

    # side check: captured left shoulder and posed shoulder.L both on the trunk's +X side
    cap_side = (V(t, "sh_l") - V(t, "sh_r")).dot(chest.col[0])
    pose_side = (P["upper_arm.L"].head - P["upper_arm.R"].head).dot(chest.col[0])
    if cap_side <= 0 or pose_side <= 0:
        report["side_check_failures"].append(t + 1)

    # feet on the floor, the lower one held still
    low = {s: foot_low(s) for s in "LR"}
    stance = min("LR", key=lambda s: low[s].z)
    if os.environ.get("HM_DEBUG") or t % 20 == 0:
        print("DBG", t + 1, tuple(round(x, 3) for x in rig.matrix_world.translation), {s: round(low[s].z, 3) for s in "LR"}, stance)
    root.z = rest_floor - low[stance].z
    if HIPS_M is not None:
        # the hips' captured path on the floor, scaled from the captured person to this body by hip height
        k = BODY_HIP_H / CAPTURED_HIP_H
        root.x, root.y = (HIPS_M[t, 0] - HIPS_M[0, 0]) * k, (HIPS_M[t, 1] - HIPS_M[0, 1]) * k
    elif anchor is not None and anchor[0] == stance:
        root.x += anchor[1].x - low[stance].x - root.x
        root.y += anchor[1].y - low[stance].y - root.y
    rig.location = root
    bpy.context.view_layer.update()
    if anchor is None or anchor[0] != stance:
        p = foot_low(stance)
        anchor = (stance, Vector((p.x, p.y)))
    report["stance"].append(stance)

    for pb in P:
        pb.keyframe_insert("rotation_quaternion", frame=t + 1)
    rig.keyframe_insert("location", frame=t + 1)

bpy.ops.wm.save_as_mainfile(filepath=out)
# the captured woman is taken as 1.70 m tall (Rafael, 2026-11-14); the ear sits at about 0.93 of stature (by eye, anthropometric
# tables put tragion near there). Angles don't use it; it makes the capture's speeds metric for the physics step.
ear_h = np.median((B[:, [7, 8], 2].mean(1) - B[:, [29, 30], 2].min(1)))
report["captured_ear_height"] = float(ear_h)
report["capture_to_metres_at_1_70"] = float(1.70 * 0.93 / ear_h)
report["side_check_ok"] = not report["side_check_failures"]
report["stance_changes"] = sum(1 for a, b in zip(report["stance"], report["stance"][1:]) if a != b)
report["root_travel_m"] = [round(x, 3) for x in root]
json.dump(report, open(report_path, "w"))
print({k: v for k, v in report.items() if k != "stance"})

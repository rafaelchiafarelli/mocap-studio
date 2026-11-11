"""Arms as damped triple pendulums with collision (Rafael, 2026-11-11). Run with --blend on a walking body. Args: out.blend out.json
Each arm hangs from the shoulder, which the walking trunk carries: shoulder, elbow and wrist are joints, the upper arm, forearm and closed hand are weights. Gravity pulls them down and each joint is damped,
so the arm settles pointing down and swings only from the trunk's motion; the wrist also has a light passive stiffness towards straight. The forearm turns about its length so the palm faces the thigh. The arm collides with the trunk and legs: it may press 5 mm into the skin (which tools/skin_waves.py dents), and friction slows
it along the skin. Joints: the elbow is a hinge, bending only forwards and not past ELBOW_MOST_DEG, the wrist bends at most WRIST_MOST_DEG. Position-based dynamics with Verlet steps; the result is keyed on the rig."""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hand_points as hp
import hmblender as hb
import posed_mesh as pm

a = hb.args()
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
scene = bpy.context.scene
fps = scene.render.fps / scene.render.fps_base
BODY_KG = 58.0  # declared
SHARE = {"upper": 0.028, "fore": 0.016, "hand": 0.006}  # of body mass, the usual segment tables (Dempster, as quoted in Winter's Biomechanics; from memory, not checked against the source)
DAMPING = {"shoulder": 3.75, "elbow": 6.0, "wrist": 9.0}  # per second, on each joint's relative motion: by eye, raised 50% by Rafael (2026-11-11)
FRICTION = 0.4  # share of the sliding along the skin taken out at each contact step: by eye
GIVE_M = 0.005  # the skin gives this much (Rafael: 5 mm at most)
RADIUS = {"upper": 0.045, "fore": 0.035, "hand": 0.04}
SAMPLES = {"upper": (0.75, 1.0), "fore": (0.5, 1.0), "hand": (1.0,)}  # the upper arm's top meets the trunk at the armpit by build, so it isn't tested there
ELBOW_MOST_DEG, WRIST_MOST_DEG = 145.0, 35.0
WRIST_STRAIGHTEN = 0.03  # per step, the share of its bend the wrist gives back: the passive stiffness that keeps a hanging hand in line with the forearm (by eye; without it the fists hooked)
SUBSTEPS, ITERATIONS = 40, 4
GRAVITY = np.array([0.0, 0.0, -9.81])
FIST = {"f_index": (88, 100, 70), "f_middle": (90, 100, 70), "f_ring": (90, 100, 70), "f_pinky": (90, 95, 65), "thumb": (0, 35, 35)}  # a closed fist, by eye; the thumb's first joint turns on another axis, so only its last two bend
FORWARD_WORLD = np.array([0.0, -1.0, 0.0])

pm.set_display(body, False)
tris = pm.triangles(body)
trunk_tris = tris[(hp.arm_weight(body, pm.N_BODY)[tris] < 0.2).all(axis=1)]
first, last = scene.frame_start, scene.frame_end
W = rig.matrix_world


def world(v):
    return np.array(W @ v)


def chain(side):
    """Shoulder, elbow, wrist and the closed fist's middle, in world space, as the walk has them."""
    up, fo, ha = (rig.pose.bones[f"{b}.{side}"] for b in ("upper_arm", "forearm", "hand"))
    fist = ha.head + 0.55 * (ha.tail - ha.head)
    return np.array([world(up.head), world(fo.head), world(ha.head), world(fist)])


palm_local = {}  # each hand's palm normal in its bone's own axes, from the nails: the palm faces away from them


def face_palm_in(side):
    """Turns the forearm about its own length so the palm faces the thigh, as a hanging arm's does; the hand follows. Returns the turn in degrees."""
    fo, ha = rig.pose.bones[f"forearm.{side}"], rig.pose.bones[f"hand.{side}"]
    bpy.context.view_layer.update()
    axis = np.array(fo.matrix.to_3x3().col[1])
    axis /= np.linalg.norm(axis)
    palm = np.array(ha.matrix.to_3x3()) @ palm_local[side]
    inward = np.array(W.inverted().to_3x3()) @ np.array([-1.0 if side == "L" else 1.0, 0.0, 0.0])
    p_, d_ = palm - np.dot(palm, axis) * axis, inward - np.dot(inward, axis) * axis
    if np.linalg.norm(p_) < 1e-6 or np.linalg.norm(d_) < 1e-6:
        return 0.0
    turn = math.atan2(float(np.dot(axis, np.cross(p_, d_))), float(np.dot(p_, d_)))
    M = fo.matrix.copy()
    head = M.to_translation()
    fo.matrix = Matrix.Translation(head) @ Matrix.Rotation(turn, 4, Vector(axis)) @ Matrix.Translation(-head) @ M
    return math.degrees(turn)


def fist_curl():
    """Closes both hands into fists, keyed once. Each finger bone's curl direction is the one that moves its fingertip away from its nail:
    MPFB's skin has a fingernails group, so the palm side is never guessed from the rest pose."""
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    skin = pm.read(body)
    nails_group = body.vertex_groups["fingernails"].index
    nails = skin[[v.index for v in body.data.vertices if any(g.group == nails_group and g.weight > 0.5 for g in v.groups)]]
    signs = {}
    for s in "LR":
        for finger in FIST:
            tip = rig.pose.bones[f"{finger}.03.{s}"]
            tip_point = np.array(W @ tip.tail)
            nail = nails[np.argsort(np.linalg.norm(nails - tip_point, axis=1))[:12]].mean(axis=0)
            axis = np.array(W @ tip.tail) - np.array(W @ tip.head)
            axis /= np.linalg.norm(axis)
            towards_nail = (nail - tip_point) - np.dot(nail - tip_point, axis) * axis
            if finger == "f_middle":
                palm_world = -towards_nail / np.linalg.norm(towards_nail)
                rest_rot = np.array(rig.data.bones[f"hand.{s}"].matrix_local.to_3x3())
                palm_local[s] = rest_rot.T @ (np.array(W.inverted().to_3x3()) @ palm_world)
            for i in (1, 2, 3):
                pb = rig.pose.bones[f"{finger}.0{i}.{s}"]
                pb.rotation_mode = "QUATERNION"
                moved = {}
                for sg in (1, -1):
                    pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(15 * sg))
                    bpy.context.view_layer.update()
                    moved[sg] = float(np.dot(np.array(W @ tip.tail) - tip_point, towards_nail))
                pb.rotation_quaternion = (1, 0, 0, 0)
                signs[pb.name] = 1 if moved[1] < moved[-1] else -1
    rig.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    for f in (first, last):
        for s in "LR":
            for finger, angles in FIST.items():
                for i, deg in enumerate(angles, 1):
                    pb = rig.pose.bones[f"{finger}.0{i}.{s}"]
                    pb.rotation_quaternion = Quaternion((1, 0, 0), math.radians(deg * signs[pb.name]))
                    pb.keyframe_insert("rotation_quaternion", frame=f)
    return signs


curl_signs = fist_curl()
scene.frame_set(first)
masses = {s: None for s in "LR"}
mass = np.array([np.inf, BODY_KG * (SHARE["upper"] + SHARE["fore"]) / 2, BODY_KG * (SHARE["fore"] + SHARE["hand"]) / 2, BODY_KG * SHARE["hand"] / 2])
inv = np.where(np.isinf(mass), 0.0, 1.0 / mass)
rest_len = {s: np.linalg.norm(np.diff(chain(s), axis=0), axis=1) for s in "LR"}
x = {s: chain(s) for s in "LR"}
x_prev = {s: x[s].copy() for s in "LR"}
segments = [("upper", 0, 1), ("fore", 1, 2), ("hand", 2, 3)]
joint_damp = [DAMPING["shoulder"], DAMPING["elbow"], DAMPING["wrist"]]
report = {s: {"contacts": 0, "deepest_mm": 0.0, "swing_deg": [], "elbow_deg": []} for s in "LR"}


def collide(p, prev, tree, s):
    """Pushes the chain's points out of the skin past what it gives, and takes FRICTION of the sliding out where they touch."""
    for name, i, j in segments:
        r = RADIUS[name]
        for t in SAMPLES[name]:
            q = p[i] + t * (p[j] - p[i])
            loc, normal, _, _ = tree.find_nearest(Vector(q))
            if loc is None:
                continue
            n = np.array(normal)
            depth = r - GIVE_M - float(np.dot(q - np.array(loc), n))
            if depth <= 0:
                continue
            report[s]["contacts"] += 1
            report[s]["deepest_mm"] = max(report[s]["deepest_mm"], depth * 1000)
            # the push goes to the moving end of the segment, weighted by where along it the touch is; the shoulder never moves
            norm = t * t + ((1 - t) * (1 - t) if inv[i] else 0.0)
            for k, w in ((j, t), (i, 1 - t)):
                if inv[k] and w > 0:
                    push = n * depth * w / norm
                    # an inelastic touch: the push moves the point, not its speed; speed into the skin stops, and friction slows the sliding
                    p[k] += push
                    prev[k] += push
                    v = p[k] - prev[k]
                    vn = float(np.dot(v, n))
                    if vn < 0:
                        prev[k] += vn * n
                        v = p[k] - prev[k]
                    slide = v - np.dot(v, n) * n
                    prev[k] += FRICTION * slide


def limit_joints(p, s):
    u1, u2, u3 = (p[1] - p[0]), (p[2] - p[1]), (p[3] - p[2])
    u1n = u1 / np.linalg.norm(u1)
    # The elbow is a hinge: the forearm bends only forwards, in the plane of the upper arm and the body's forward direction.
    # Its sideways part and any backward bend are taken out (Rafael saw the forearms bending outwards, 2026-11-11).
    # The correction is shared by elbow and wrist by their weights, so to move the hand sideways the whole arm opens at the shoulder instead of the two fighting.
    forward = FORWARD_WORLD - np.dot(FORWARD_WORLD, u1n) * u1n
    if np.linalg.norm(forward) > 1e-6:
        forward /= np.linalg.norm(forward)
        side = np.cross(u1n, forward)
        wrong = np.dot(u2, side) * side + min(0.0, float(np.dot(u2, forward))) * forward
        if np.linalg.norm(wrong) > 1e-9:
            w1, w2 = inv[1], inv[2]
            p[1] += wrong * w1 / (w1 + w2)
            p[2] -= wrong * w2 / (w1 + w2)
            p[3] -= wrong * w2 / (w1 + w2)
    for (i, j, k), most in (((0, 1, 2), ELBOW_MOST_DEG), ((1, 2, 3), WRIST_MOST_DEG)):
        a_ = p[j] - p[i]
        b_ = p[k] - p[j]
        ang = math.degrees(math.acos(np.clip(np.dot(a_, b_) / (np.linalg.norm(a_) * np.linalg.norm(b_)), -1, 1)))
        if ang > most:
            an = a_ / np.linalg.norm(a_)
            axis = np.cross(an, b_)
            if np.linalg.norm(axis) < 1e-9:
                continue
            axis /= np.linalg.norm(axis)
            back_turn = math.radians(ang - most)
            R = np.array(Matrix.Rotation(-back_turn, 3, Vector(axis)))
            for m in range(k, 4):
                p[m] = p[j] + R @ (p[m] - p[j])


def aim(pb, target):
    """Turns a posed bone about its head so its tail points at `target` (world), by the smallest turn, keeping its twist."""
    bpy.context.view_layer.update()
    M = pb.matrix.copy()
    head = M.to_translation()
    d = (W.inverted() @ Vector(target)) - head
    q = M.to_3x3().col[1].rotation_difference(d.normalized())
    pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ M


dt = 1.0 / (fps * SUBSTEPS)
SETTLE_S = 2.0  # before the walk, the arms start hanging straight down and settle with the body still


def hang(s):
    """The arm hanging straight down from the shoulder, a little outwards so it starts clear of the hips."""
    out = 1.0 if s == "L" else -1.0
    p = np.zeros((4, 3))
    p[0] = x[s][0]
    direction = np.array([out * 0.15, 0.0, -1.0])
    direction /= np.linalg.norm(direction)
    for j in (1, 2, 3):
        p[j] = p[j - 1] + direction * rest_len[s][j - 1]
    return p


scene.frame_set(first + 1)
second = {s: world(rig.pose.bones[f"upper_arm.{s}"].head) for s in "LR"}
scene.frame_set(first)
settle_tree = BVHTree.FromPolygons([Vector(v) for v in pm.read(body)[: pm.N_BODY]], trunk_tris.tolist())
for s in "LR":
    # the walk starts already moving: the arms settle moving with the shoulder at that speed, so the first frame doesn't jolt them
    step = (second[s] - x[s][0]) / SUBSTEPS
    p = hang(s) - step * int(SETTLE_S * fps * SUBSTEPS)
    prev = p - step
    for _ in range(int(SETTLE_S * fps * SUBSTEPS)):
        v = p - prev
        for j in range(1, 4):
            v[j] -= min(1.0, joint_damp[j - 1] * dt) * (v[j] - v[j - 1])
        new = p + v + GRAVITY * dt * dt
        new[0] = p[0] + step
        prev, p = p, new
        for _ in range(ITERATIONS):
            for j in (1, 2, 3):
                d = p[j] - p[j - 1]
                L = np.linalg.norm(d)
                corr = (L - rest_len[s][j - 1]) * d / max(L, 1e-9)
                wi, wj = inv[j - 1], inv[j]
                p[j - 1] += corr * wi / (wi + wj)
                p[j] -= corr * wj / (wi + wj)
            limit_joints(p, s)
            # the body stands at the first frame's place: the settling arm is tested against it shifted by how far the shoulder still has to go
            offset = x[s][0] - p[0]
            moved, moved_prev = p + offset, prev + offset
            collide(moved, moved_prev, settle_tree, s)
            p, prev = moved - offset, moved_prev - offset
    x[s], x_prev[s] = p, prev
    report[s]["contacts"], report[s]["deepest_mm"] = 0, 0.0
shoulder_prev = {s: x[s][0].copy() for s in "LR"}
for f in range(first, last + 1):
    scene.frame_set(f)
    V = pm.read(body)[: pm.N_BODY]
    tree = BVHTree.FromPolygons([Vector(v) for v in V], trunk_tris.tolist())
    for s in "LR":
        shoulder_now = world(rig.pose.bones[f"upper_arm.{s}"].head)
        p, prev = x[s], x_prev[s]
        for k in range(SUBSTEPS):
            u = (k + 1) / SUBSTEPS
            v = p - prev
            # joint damping: each point's motion relative to its parent slows
            for j in range(1, 4):
                v[j] -= min(1.0, joint_damp[j - 1] * dt) * (v[j] - v[j - 1])
            new = p + v + GRAVITY * dt * dt
            new[0] = shoulder_prev[s] + u * (shoulder_now - shoulder_prev[s])
            prev, p = p, new
            for _ in range(ITERATIONS):
                for j in (1, 2, 3):
                    d = p[j] - p[j - 1]
                    L = np.linalg.norm(d)
                    corr = (L - rest_len[s][j - 1]) * d / max(L, 1e-9)
                    wi, wj = inv[j - 1], inv[j]
                    p[j - 1] += corr * wi / (wi + wj)
                    p[j] -= corr * wj / (wi + wj)
                u2 = p[2] - p[1]
                straight = p[2] + u2 / np.linalg.norm(u2) * rest_len[s][2]
                p[3] += WRIST_STRAIGHTEN * (straight - p[3])
                if "no_limits" not in a:
                    limit_joints(p, s)
                if "no_collision" not in a:
                    collide(p, prev, tree, s)
        x[s], x_prev[s], shoulder_prev[s] = p, prev, shoulder_now
        # what is left inside the skin, past what it gives, once the frame is solved
        left = 0.0
        for name, i, j in segments:
            for t in SAMPLES[name]:
                q = p[i] + t * (p[j] - p[i])
                loc, normal, _, _ = tree.find_nearest(Vector(q))
                if loc is not None:
                    left = max(left, RADIUS[name] - GIVE_M - float(np.dot(q - np.array(loc), np.array(normal))))
        report[s]["left_mm"] = max(report[s].get("left_mm", 0.0), left * 1000)
        report[s]["frames_left"] = report[s].get("frames_left", 0) + int(left > 0.001)
        for name, (i, j) in (("upper_arm", (0, 1)), ("forearm", (1, 2)), ("hand", (2, 3))):
            pb = rig.pose.bones[f"{name}.{s}"]
            target = p[j] if name != "hand" else p[2] + (p[3] - p[2]) / 0.55
            aim(pb, target)
        report[s].setdefault("palm_turn_deg", []).append(face_palm_in(s))
        aim(rig.pose.bones[f"hand.{s}"], p[2] + (p[3] - p[2]) / 0.55)
        for name in ("upper_arm", "forearm", "hand"):
            rig.pose.bones[f"{name}.{s}"].keyframe_insert("rotation_quaternion", frame=f)
        u1, u2 = p[1] - p[0], p[2] - p[1]
        if "trace" in a and s == "L" and f % 6 == 1:
            print("trace", f, np.round(p, 3).tolist())
        report[s]["swing_deg"].append(math.degrees(math.atan2(-u1[1], -u1[2])))
        report[s]["elbow_deg"].append(math.degrees(math.acos(np.clip(np.dot(u1, u2) / (np.linalg.norm(u1) * np.linalg.norm(u2)), -1, 1))))
pm.set_display(body, True)
scene.frame_set(first)
bpy.ops.wm.save_as_mainfile(filepath=a[0])
summary = {s: {"contact_steps": r["contacts"], "deepest_inside_a_step_mm": r["deepest_mm"], "swing_range_deg": [min(r["swing_deg"]), max(r["swing_deg"])], "elbow_range_deg": [min(r["elbow_deg"]), max(r["elbow_deg"])], "deepest_left_after_frame_mm": r.get("left_mm", 0.0), "frames_left_inside": r.get("frames_left", 0), "palm_turn_range_deg": [min(r["palm_turn_deg"]), max(r["palm_turn_deg"])]} for s, r in report.items()}
json.dump({"arms": summary, "masses_kg": mass[1:].tolist()}, open(a[1], "w"), indent=1)
print(json.dumps(summary))

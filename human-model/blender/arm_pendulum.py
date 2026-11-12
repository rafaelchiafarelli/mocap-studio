"""Arms as damped triple pendulums with collision (Rafael, 2026-11-11), with the shoulder's and elbow's muscles as soft springs towards a swing opposite the legs. Run with --blend on a walking body. Args: out.blend out.json
Each arm hangs from the shoulder, which the walking trunk carries: shoulder, elbow and wrist are joints, the upper arm, forearm and closed hand are weights. Gravity pulls them down and each joint is damped,
so the arm settles pointing down and swings only from the trunk's motion; the wrist also has a light passive stiffness towards straight. The forearm turns about its length so the palm faces the thigh. The arm collides with the trunk and legs: it may press 5 mm into the skin (which tools/skin_waves.py dents), and friction slows
it along the skin. Joints: the elbow is a hinge, bending only forwards and not past ELBOW_MOST_DEG, the wrist bends at most WRIST_MOST_DEG. Position-based dynamics with Verlet steps; the solved arm is filtered over frames (SMOOTH_SIGMA_FRAMES) and keyed on the rig."""
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
FIST = {"f_index": (75, 85, 35), "f_middle": (78, 88, 35), "f_ring": (78, 88, 35), "f_pinky": (78, 85, 35), "thumb": (0, 35, 35)}  # a closed fist, by eye; the thumb's first joint turns on another axis, so only its last two bend
FORWARD_WORLD = np.array([0.0, -1.0, 0.0])
# Twist of the upper arm and the forearm about their own length (Rafael, 2026-11-11): each is a damped spring with inertia whose rest follows the trunk's turn
# and, a little, the swing (an arm behind the body turns inwards); it lags and rocks slightly. By eye: frequency, damping ratio, degrees of twist per degree of swing.
# The shoulder's muscles (Rafael, 2026-11-11: the passive arms looked like hanging wood, swung only by the thigh's hits). The elbow is pulled, as by a soft spring, towards a swing opposite the
# same side's leg, ARM_PER_LEG of its angle, with the arm a little out from the body; the elbow towards a light bend, more as the arm goes forward. Weight, inertia and damping still act on top. By eye.
ARM_PER_LEG = 0.65
REST_OUT_DEG = 5.0
ELBOW_REST_DEG, ELBOW_FORWARD_DEG = 12.0, 15.0
CARRY_DEG = 13.0  # a woman's elbow carrying angle: the straight forearm points this far outwards from the upper arm, so the hands pass beside the hips (12 to 15 is the usual range, from memory)
SHOULDER_DRIVE, ELBOW_DRIVE = 0.004, 0.0035  # per step, the share of the way to the target the muscles pull: weak, so weight and inertia lead (stronger ones made the arm reach a changed target within a frame: jumps)
# Intention (Rafael, 2026-11-12: "we throw the arms forwards on purpose"). While the arm's target moves forwards the shoulder works: its pull is FORWARD_GAIN times
# stronger, the target reaches FORWARD_BIAS_DEG further (INWARD_DEG towards the middle, 0 for now), and the elbow bends ELBOW_INTENT_DEG more, all eased in and out over INTENT_S.
# While the target moves back the muscles relax to BACK_GAIN and the arm falls back by its own weight. By eye.
FORWARD_GAIN, BACK_GAIN = 3.0, 0.3
FORWARD_BIAS_DEG, INWARD_DEG, ELBOW_INTENT_DEG = 6.0, 0.0, 10.0  # reaching inwards by 3 brought the hands onto the body in thousands of steps; 0 in none
SMOOTH_SIGMA_FRAMES = 1.2  # the filter on the solved arm, in frames
MAX_REL_M_S = 2.5  # the fastest any point of the arm moves against the shoulder
INTENT_S = 0.12  # the intention eases in and out over about this long; switched at once, it made the arm jump (Rafael, 2026-11-12)
TWIST = {"upper": {"hz": 1.6, "damping": 0.35, "per_swing": 0.25}, "fore": {"hz": 2.6, "damping": 0.35, "per_swing": 0.30}}

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
    """Closes both hands into fists, keyed once. Each finger bone bends about whichever of its local X and Z axes, and whichever way, moves it most towards the palm:
    on this rig the fingers' X is the spreading axis, and turning about it bent them sideways (Rafael saw the armature 'breaking', 2026-11-11).
    The palm is perpendicular to the hand and to its row of knuckles, on the side away from the middle fingertip's nail, measured on the straight hand at rest. Returns each bone's (axis, sign)."""
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    skin = pm.read(body)
    nails_group = body.vertex_groups["fingernails"].index
    nails = skin[[v.index for v in body.data.vertices if any(g.group == nails_group and g.weight > 0.5 for g in v.groups)]]
    bend = {}
    for s in "LR":
        # the palm is perpendicular to the hand's length and to the row of knuckles from index to little finger; the middle fingertip's nail says which face it is
        hand_b = rig.pose.bones[f"hand.{s}"]
        along = np.array(W @ hand_b.tail) - np.array(W @ hand_b.head)
        knuckles = np.array(W @ rig.pose.bones[f"f_index.01.{s}"].head) - np.array(W @ rig.pose.bones[f"f_pinky.01.{s}"].head)
        normal = np.cross(knuckles, along)
        normal /= np.linalg.norm(normal)
        tip = rig.pose.bones[f"f_middle.03.{s}"]
        tip_mid = (np.array(W @ tip.head) + np.array(W @ tip.tail)) / 2
        nail = nails[np.argsort(np.linalg.norm(nails - tip_mid, axis=1))[:6]].mean(axis=0)
        palm_world = -normal if np.dot(nail - tip_mid, normal) > 0 else normal
        palm_local[s] = np.array(rig.data.bones[f"hand.{s}"].matrix_local.to_3x3()).T @ (np.array(W.inverted().to_3x3()) @ palm_world)
        for finger in FIST:
            for i in (1, 2, 3):
                pb = rig.pose.bones[f"{finger}.0{i}.{s}"]
                pb.rotation_mode = "QUATERNION"
                before = np.array(W @ pb.tail)
                best = None
                for axis in ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)):
                    for sg in (1, -1):
                        pb.rotation_quaternion = Quaternion(axis, math.radians(20 * sg))
                        bpy.context.view_layer.update()
                        towards_palm = float(np.dot(np.array(W @ pb.tail) - before, palm_world))
                        if best is None or towards_palm > best[0]:
                            best = (towards_palm, axis, sg)
                pb.rotation_quaternion = (1, 0, 0, 0)
                bpy.context.view_layer.update()
                bend[pb.name] = (best[1], best[2])
    rig.data.pose_position = "POSE"
    bpy.context.view_layer.update()
    for f in (first, last):
        for s in "LR":
            for finger, angles in FIST.items():
                for i, deg in enumerate(angles, 1):
                    pb = rig.pose.bones[f"{finger}.0{i}.{s}"]
                    axis, sg = bend[pb.name]
                    pb.rotation_quaternion = Quaternion(axis, math.radians(deg * sg))
                    pb.keyframe_insert("rotation_quaternion", frame=f)
    return bend


curl_signs = fist_curl()


def wrap_thumbs():
    """Lays each thumb over the closed fingers: its three joints turn, by a small search, until the thumb's tip rests on the index finger's middle bone, a little outside it, as a fist's thumb does."""
    scene.frame_set(first)
    found = {}
    for s in "LR":
        bones = [rig.pose.bones[f"thumb.0{i}.{s}"] for i in (1, 2, 3)]
        index = rig.pose.bones[f"f_index.02.{s}"]
        best = None
        for ax in range(-60, 61, 10):
            for az in range(-60, 61, 10):
                bones[0].rotation_quaternion = Quaternion((1, 0, 0), math.radians(ax)) @ Quaternion((0, 0, 1), math.radians(az))
                for b2 in range(0, 61, 15):
                    for pb, deg in zip(bones[1:], (b2, b2)):
                        pb.rotation_quaternion = Quaternion(curl_signs[pb.name][0], math.radians(deg * curl_signs[pb.name][1]))
                    bpy.context.view_layer.update()
                    target = W @ (index.head + 0.5 * (index.tail - index.head))
                    d = ((W @ bones[2].tail) - target).length
                    if best is None or d < best[0]:
                        best = (d, ax, az, b2)
        d, ax, az, b2 = best
        found[s] = {"gap_mm": d * 1000, "base_x": ax, "base_z": az, "bend": b2}
        for f in (first, last):
            bones[0].rotation_quaternion = Quaternion((1, 0, 0), math.radians(ax)) @ Quaternion((0, 0, 1), math.radians(az))
            for pb in bones[1:]:
                pb.rotation_quaternion = Quaternion(curl_signs[pb.name][0], math.radians(b2 * curl_signs[pb.name][1]))
            for pb in bones:
                pb.keyframe_insert("rotation_quaternion", frame=f)
    return found


thumbs = wrap_thumbs()
print("thumbs", thumbs)
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
        # the hinge's plane leans outwards by the carrying angle: the straight forearm points a little away from the body
        out = np.cross(forward, u1n) * (1.0 if s == "L" else -1.0)
        out /= np.linalg.norm(out)
        if np.dot(out, [1.0 if s == "L" else -1.0, 0, 0]) < 0:
            out = -out
        base = math.cos(math.radians(CARRY_DEG)) * u1n + math.sin(math.radians(CARRY_DEG)) * out
        side = np.cross(base, forward)
        side /= np.linalg.norm(side)
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


def twist(pb, degrees):
    """Turns a posed bone about its own length, through its head."""
    bpy.context.view_layer.update()
    M = pb.matrix.copy()
    head = M.to_translation()
    pb.matrix = Matrix.Translation(head) @ Matrix.Rotation(math.radians(degrees), 4, M.to_3x3().col[1]) @ Matrix.Translation(-head) @ M


def inward_sign(side, bone):
    """Which way of turning `bone` about its length moves the palm backwards, so a positive twist means turning the arm inwards."""
    pb, ha = rig.pose.bones[f"{bone}.{side}"], rig.pose.bones[f"hand.{side}"]
    saved = pb.matrix.copy()
    moved = {}
    for sg in (1, -1):
        pb.matrix = saved
        twist(pb, 10 * sg)
        bpy.context.view_layer.update()
        palm = np.array(W.to_3x3()) @ (np.array(ha.matrix.to_3x3()) @ palm_local[side])
        moved[sg] = palm[1]  # +Y is backwards
    pb.matrix = saved
    bpy.context.view_layer.update()
    return 1 if moved[1] > moved[-1] else -1


def targets(s, advance):
    """The muscles' target directions for the upper arm and forearm this frame, and how hard they pull. `advance` moves the intention on by a frame."""
    thigh = rig.pose.bones[f"thigh.{s}"]
    leg = np.array(W.to_3x3()) @ np.array(thigh.tail - thigh.head)
    leg_swing = math.degrees(math.atan2(-leg[1], -leg[2]))  # forward is positive
    arm_swing = -ARM_PER_LEG * leg_swing
    if advance:
        going_forward = arm_swing > last_target[s]
        last_target[s] = arm_swing
        intent[s] += ((1.0 if going_forward else 0.0) - intent[s]) * min(1.0, 1.0 / (fps * INTENT_S))
    else:
        last_target[s] = arm_swing
    k_ = intent[s]
    gain = BACK_GAIN + (FORWARD_GAIN - BACK_GAIN) * k_
    arm_swing += FORWARD_BIAS_DEG * k_
    outward = 1.0 if s == "L" else -1.0
    out_deg = REST_OUT_DEG - INWARD_DEG * k_
    a_sw, a_out = math.radians(arm_swing), math.radians(out_deg)
    upper_dir = np.array([outward * math.sin(a_out), -math.sin(a_sw) * math.cos(a_out), -math.cos(a_sw) * math.cos(a_out)])
    elbow_flex = math.radians(ELBOW_REST_DEG + ELBOW_FORWARD_DEG * max(0.0, arm_swing) / 20.0 + ELBOW_INTENT_DEG * k_)
    fwd = FORWARD_WORLD - np.dot(FORWARD_WORLD, upper_dir) * upper_dir
    fwd /= np.linalg.norm(fwd)
    carry = math.radians(CARRY_DEG)
    straight = math.cos(carry) * upper_dir + math.sin(carry) * np.array([outward, 0.0, 0.0])
    straight /= np.linalg.norm(straight)
    fore_dir = math.cos(elbow_flex) * straight + math.sin(elbow_flex) * fwd
    return upper_dir, fore_dir, gain


def trunk_turn():
    """The chest's turn about the vertical, in degrees."""
    pb = rig.pose.bones["spine.003"]
    x_axis = np.array(W.to_3x3()) @ np.array(pb.matrix.to_3x3().col[0])
    return math.degrees(math.atan2(x_axis[1], x_axis[0]))


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


last_target = {s: 0.0 for s in "LR"}
intent = {s: 0.0 for s in "LR"}
scene.frame_set(first + 1)
second = {s: world(rig.pose.bones[f"upper_arm.{s}"].head) for s in "LR"}
scene.frame_set(first)
settle_tree = BVHTree.FromPolygons([Vector(v) for v in pm.read(body)[: pm.N_BODY]], trunk_tris.tolist())
for s in "LR":
    up0, fo0, gain0 = targets(s, False)  # the arms settle with their muscles already on, at the first frame's pose
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
        p[1] += min(1.0, SHOULDER_DRIVE * gain0) * (p[0] + up0 * rest_len[s][0] - p[1])
        p[2] += min(1.0, ELBOW_DRIVE * gain0) * (p[1] + fo0 * rest_len[s][1] - p[2])
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
scene.frame_set(first)
inward = {s: {bone: inward_sign(s, bone) for bone in ("upper_arm", "forearm")} for s in "LR"}
solved = {s: [] for s in "LR"}
last_target = {s: 0.0 for s in "LR"}
intent = {s: 0.0 for s in "LR"}
yaw0 = trunk_turn()
twist_state = {s: {"upper": [yaw0, 0.0], "fore": [0.0, 0.0]} for s in "LR"}
swing_rest = {s: 0.0 for s in "LR"}
for f in range(first, last + 1):
    scene.frame_set(f)
    V = pm.read(body)[: pm.N_BODY]
    tree = BVHTree.FromPolygons([Vector(v) for v in V], trunk_tris.tolist())
    for s in "LR":
        shoulder_now = world(rig.pose.bones[f"upper_arm.{s}"].head)
        p, prev = x[s], x_prev[s]
        upper_dir, fore_dir, gain = targets(s, True)
        for k in range(SUBSTEPS):
            u = (k + 1) / SUBSTEPS
            v = p - prev
            # joint damping: each point's motion relative to its parent slows
            for j in range(1, 4):
                v[j] -= min(1.0, joint_damp[j - 1] * dt) * (v[j] - v[j - 1])
                rel = v[j] - v[0]
                fast = np.linalg.norm(rel)
                if fast > MAX_REL_M_S * dt:  # nothing in a walking arm moves this fast against the shoulder; it stops jumps the rest may leave
                    v[j] = v[0] + rel * (MAX_REL_M_S * dt / fast)
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
                # the muscles pull towards the target pose, softly: elbow from the shoulder, wrist from the elbow
                p[1] += min(1.0, SHOULDER_DRIVE * gain) * (p[0] + upper_dir * rest_len[s][0] - p[1])
                p[2] += min(1.0, ELBOW_DRIVE * gain) * (p[1] + fore_dir * rest_len[s][1] - p[2])
                u2 = p[2] - p[1]
                straight_hand = p[2] + u2 / np.linalg.norm(u2) * rest_len[s][2]
                p[3] += WRIST_STRAIGHTEN * (straight_hand - p[3])
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
        # the twists' springs, one step per frame in small steps
        u1 = p[1] - p[0]
        swing = math.degrees(math.atan2(-u1[1], -u1[2])) - swing_rest[s]
        yaw = trunk_turn()
        for part, target in (("upper", yaw + TWIST["upper"]["per_swing"] * -swing), ("fore", TWIST["fore"]["per_swing"] * -swing)):
            q, qv = twist_state[s][part]
            omega = 2 * math.pi * TWIST[part]["hz"]
            for _ in range(SUBSTEPS):
                qv += dt * (-omega * omega * (q - target) - 2 * TWIST[part]["damping"] * omega * qv)
                q += dt * qv
            twist_state[s][part] = [q, qv]
        upper_twist = twist_state[s]["upper"][0] - yaw
        fore_twist = twist_state[s]["fore"][0]
        solved[s].append(((p - p[0]).copy(), upper_twist, fore_twist))
        report[s].setdefault("upper_twist_deg", []).append(upper_twist)
        report[s].setdefault("fore_twist_deg", []).append(fore_twist)
        u1, u2 = p[1] - p[0], p[2] - p[1]
        if "trace" in a and s == "L" and f % 6 == 1:
            print("trace", f, np.round(p, 3).tolist())
        report[s]["swing_deg"].append(math.degrees(math.atan2(-u1[1], -u1[2])))
        report[s]["elbow_deg"].append(math.degrees(math.acos(np.clip(np.dot(u1, u2) / (np.linalg.norm(u1) * np.linalg.norm(u2)), -1, 1))))

def smoothed(series, sigma):
    """A zero-phase gaussian over frames, edges held: keeps the swing (about 1 Hz), takes out the jolts the constraints leave."""
    radius = int(3 * sigma) + 1
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    kernel /= kernel.sum()
    padded = np.concatenate([np.repeat(series[:1], radius, axis=0), series, np.repeat(series[-1:], radius, axis=0)])
    return np.stack([np.convolve(padded[:, k], kernel, mode="valid") for k in range(series.shape[1])], axis=1)


# The solved arm is filtered before it becomes a pose: the wrist's acceleration against the shoulder reached 66 m/s2 in some frames (Rafael saw the arms jump, 2026-11-12)
for s in "LR":
    rel = np.array([r for r, _, _ in solved[s]])
    flat = smoothed(rel.reshape(len(rel), -1), SMOOTH_SIGMA_FRAMES).reshape(rel.shape)
    raw_acc = np.linalg.norm(np.diff(rel[:, 2], 2, axis=0), axis=1) * fps * fps
    new_acc = np.linalg.norm(np.diff(flat[:, 2], 2, axis=0), axis=1) * fps * fps
    report[s]["wrist_accel_before"] = [float(np.percentile(raw_acc, 95)), float(raw_acc.max())]
    report[s]["wrist_accel_after"] = [float(np.percentile(new_acc, 95)), float(new_acc.max())]
    solved[s] = [(flat[i], ut, ft) for i, (_, ut, ft) in enumerate(solved[s])]
for i, f in enumerate(range(first, last + 1)):
    scene.frame_set(f)
    for s in "LR":
        rel, upper_twist, fore_twist = solved[s][i]
        p = world(rig.pose.bones[f"upper_arm.{s}"].head) + rel
        aim(rig.pose.bones[f"upper_arm.{s}"], p[1])
        twist(rig.pose.bones[f"upper_arm.{s}"], inward[s]["upper_arm"] * upper_twist)
        aim(rig.pose.bones[f"forearm.{s}"], p[2])
        report[s].setdefault("palm_turn_deg", []).append(face_palm_in(s))
        twist(rig.pose.bones[f"forearm.{s}"], inward[s]["forearm"] * fore_twist)
        aim(rig.pose.bones[f"hand.{s}"], p[2] + (p[3] - p[2]) / 0.55)
        for name in ("upper_arm", "forearm", "hand"):
            rig.pose.bones[f"{name}.{s}"].keyframe_insert("rotation_quaternion", frame=f)
pm.set_display(body, True)
scene.frame_set(first)
bpy.ops.wm.save_as_mainfile(filepath=a[0])
summary = {s: {"contact_steps": r["contacts"], "deepest_inside_a_step_mm": r["deepest_mm"], "swing_range_deg": [min(r["swing_deg"]), max(r["swing_deg"])], "elbow_range_deg": [min(r["elbow_deg"]), max(r["elbow_deg"])], "deepest_left_after_frame_mm": r.get("left_mm", 0.0), "frames_left_inside": r.get("frames_left", 0), "palm_turn_range_deg": [min(r["palm_turn_deg"]), max(r["palm_turn_deg"])], "upper_twist_range_deg": [min(r["upper_twist_deg"]), max(r["upper_twist_deg"])], "fore_twist_range_deg": [min(r["fore_twist_deg"]), max(r["fore_twist_deg"])], "wrist_accel_p95_max_before": r["wrist_accel_before"], "wrist_accel_p95_max_after": r["wrist_accel_after"]} for s, r in report.items()}
json.dump({"arms": summary, "thumbs": thumbs, "masses_kg": mass[1:].tolist()}, open(a[1], "w"), indent=1)
print(json.dumps(summary))

"""The contact between hands and body while walking: the hand is stopped by the body, which gives under it. Run with --blend on a walking body. Args: out.blend out.json
Each frame, points along the forearm, hand and fingers are tested against the skin of the trunk and legs (the arms' own skin left out). A point may go up to 5 mm into the skin, which tools/skin_waves.py then dents under it;
past that the hand gives first, turning outwards at the wrist up to WRIST_MOST_DEG, and only then the upper arm opens, up to MOST_DEG, each by as little as it takes, smoothed over time and keyed on top of the walk. The hand touches and slides on the body instead of being held away from it (Rafael, 2026-11-11)."""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posed_mesh as pm
import posing as P

a = hb.args()
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
scene = bpy.context.scene
MARGIN_M = -0.005  # how far a point may sink into the skin, which yields there (Rafael, 2026-11-11: 5 mm at most)
WRIST_MOST_DEG = 15.0  # the hand gives first: fingers straighten, then it turns at the wrist
BEYOND_DEG = 20.0  # past MOST_DEG the arm may still open, to keep the hand out of the body; such frames are counted apart
FINGERS = ("f_index", "f_middle", "f_ring", "f_pinky", "thumb")
STEP_DEG, MOST_DEG = 0.5, 5.0  # then the arm, never more than this on its own (Rafael's rule, 2026-11-11)
SMOOTH_FRAMES = 2  # the opening is eased over this many frames either side
sign = {"L": 1, "R": -1}
import hand_points as hp

pm.set_display(body, False)
tris = pm.triangles(body)
arm_weight = hp.arm_weight(body, pm.N_BODY)
trunk_tris = tris[(arm_weight[tris] < 0.2).all(axis=1)]


def points(side):
    return hp.points(rig, side)


def worst(tree, side):
    """The deepest a point gets into the skin, as metres short of its radius plus the margin; 0 when all are clear."""
    short = 0.0
    for p, radius in points(side):
        hit = tree.find_nearest(p)
        if hit[0] is None:
            continue
        location, normal = hit[0], hit[1]
        d = (p - location).dot(normal)
        short = max(short, radius + MARGIN_M - d)
    return short


def turn_hand(side, degrees, base):
    """Turns the hand outwards about the vertical, at the wrist, from its walk pose `base` (a 4x4 pose matrix)."""
    pb = rig.pose.bones[f"hand.{side}"]
    head = base.to_translation()
    pb.matrix = Matrix.Translation(head) @ Matrix.Rotation(math.radians(-sign[side] * degrees), 4, "Z") @ Matrix.Translation(-head) @ base


def finger_bones(side):
    return [rig.pose.bones[f"{f}.0{i}.{side}"] for f in FINGERS for i in (1, 2, 3) if f"{f}.0{i}.{side}" in rig.pose.bones]


def straighten(side, share, saved):
    """Takes `share` of the relaxed curl out of the fingers: they give as they touch."""
    for pb, q in zip(finger_bones(side), saved):
        pb.rotation_quaternion = q.slerp((1, 0, 0, 0), share)


def open_arm(side, degrees, base):
    rest_rot = P.rest_rotation(rig, f"upper_arm.{side}")
    pb = rig.pose.bones[f"upper_arm.{side}"]
    world = rest_rot @ base.to_matrix() @ rest_rot.inverted()
    pb.rotation_quaternion = P.to_basis(rig, f"upper_arm.{side}", P.ry(-sign[side] * degrees) @ world)


first, last = scene.frame_start, scene.frame_end
needed = {s: np.zeros(last - first + 1) for s in "LR"}
wrist_needed = {s: np.zeros(last - first + 1) for s in "LR"}
finger_needed = {s: np.zeros(last - first + 1) for s in "LR"}
before = {s: np.zeros(last - first + 1) for s in "LR"}
for i, f in enumerate(range(first, last + 1)):
    scene.frame_set(f)
    V = pm.read(body)[: pm.N_BODY]
    tree = BVHTree.FromPolygons([Vector(x) for x in V], trunk_tris.tolist())
    for s in "LR":
        pb = rig.pose.bones[f"upper_arm.{s}"]
        hand = rig.pose.bones[f"hand.{s}"]
        base, hand_base, hand_quat = pb.rotation_quaternion.copy(), hand.matrix.copy(), hand.rotation_quaternion.copy()
        fingers = [f.rotation_quaternion.copy() for f in finger_bones(s)]
        before[s][i] = worst(tree, s)
        share = 0.0
        while worst(tree, s) > 0 and share < 1.0:
            share = min(1.0, share + 0.1)
            straighten(s, share, fingers)
            bpy.context.view_layer.update()
        wrist, way = 0.0, 0.0
        if worst(tree, s) > 0:
            # the wrist turns whichever way frees the hand
            trial = {}
            for d in (1.0, -1.0):
                turn_hand(s, d * 5.0, hand_base)
                bpy.context.view_layer.update()
                trial[d] = worst(tree, s)
            way = 1.0 if trial[1.0] <= trial[-1.0] else -1.0
        while way and worst(tree, s) > 0 and wrist < WRIST_MOST_DEG:
            wrist += STEP_DEG
            turn_hand(s, way * wrist, hand_base)
            bpy.context.view_layer.update()
        if way and worst(tree, s) > 0 and wrist >= WRIST_MOST_DEG:
            turn_hand(s, way * wrist, hand_base)
        angle = 0.0
        while worst(tree, s) > 0 and angle < MOST_DEG + BEYOND_DEG:
            angle += STEP_DEG
            open_arm(s, angle, base)
            bpy.context.view_layer.update()
        needed[s][i], wrist_needed[s][i], finger_needed[s][i] = angle, way * wrist, share
        pb.rotation_quaternion = base
        hand.rotation_quaternion = hand_quat
        for f, q in zip(finger_bones(s), fingers):
            f.rotation_quaternion = q
        bpy.context.view_layer.update()


def smooth(x):
    kernel = np.hanning(2 * SMOOTH_FRAMES + 3)[1:-1]
    kernel /= kernel.sum()
    padded = np.pad(x, SMOOTH_FRAMES, mode="edge")
    return np.maximum(np.convolve(padded, kernel, mode="valid"), x)


after = {s: np.zeros(last - first + 1) for s in "LR"}
walk_arm = {s: [] for s in "LR"}
opening = {s: smooth(needed[s]) for s in "LR"}
def smooth_signed(x):
    kernel = np.hanning(2 * SMOOTH_FRAMES + 3)[1:-1]
    kernel /= kernel.sum()
    return np.convolve(np.pad(x, SMOOTH_FRAMES, mode="edge"), kernel, mode="valid")


def smooth_wrist(x):
    """The turn's size smoothed like the arm's, never below what a frame needed; its way kept from the nearest frame that turned."""
    size = smooth(np.abs(x))
    way = np.sign(x)
    known = np.nonzero(way)[0]
    if known.size:
        way = way[known[np.abs(np.arange(len(x))[:, None] - known[None]).argmin(axis=1)]]
    return size * way


wrist_turn = {s: smooth_wrist(wrist_needed[s]) for s in "LR"}
finger_give = {s: smooth(finger_needed[s]) for s in "LR"}
for i, f in enumerate(range(first, last + 1)):
    scene.frame_set(f)
    for s in "LR":
        pb = rig.pose.bones[f"upper_arm.{s}"]
        hand = rig.pose.bones[f"hand.{s}"]
        hand_base = hand.matrix.copy()
        walk_arm[s].append(pb.rotation_quaternion.copy())
        open_arm(s, float(opening[s][i]), pb.rotation_quaternion.copy())
        pb.keyframe_insert("rotation_quaternion", frame=f)
        bpy.context.view_layer.update()
        turn_hand(s, float(wrist_turn[s][i]), rig.pose.bones[f"hand.{s}"].matrix.copy())
        hand.keyframe_insert("rotation_quaternion", frame=f)
        straighten(s, float(finger_give[s][i]), [b.rotation_quaternion.copy() for b in finger_bones(s)])
        for b in finger_bones(s):
            b.keyframe_insert("rotation_quaternion", frame=f)
    bpy.context.view_layer.update()
    V = pm.read(body)[: pm.N_BODY]
    tree = BVHTree.FromPolygons([Vector(x) for x in V], trunk_tris.tolist())
    for s in "LR":
        # smoothing can undo part of a frame's fix; whatever still goes through is closed here by the arm, and counted
        extra = 0.0
        pb = rig.pose.bones[f"upper_arm.{s}"]
        base = pb.rotation_quaternion.copy()
        while worst(tree, s) > 0 and opening[s][i] + extra < MOST_DEG + BEYOND_DEG:
            extra += STEP_DEG
            open_arm(s, extra, base)
            bpy.context.view_layer.update()
        if extra:
            opening[s][i] += extra
            pb.keyframe_insert("rotation_quaternion", frame=f)
        after[s][i] = worst(tree, s)
# Smoothing can undo part of a frame's fix. Rounds: measure what still goes through, open the arm that much more, smooth, apply from the walk's own arm, until nothing does.
def apply_opening():
    for i, f in enumerate(range(first, last + 1)):
        scene.frame_set(f)
        for s in "LR":
            pb = rig.pose.bones[f"upper_arm.{s}"]
            pb.rotation_quaternion = walk_arm[s][i]
            open_arm(s, float(opening[s][i]), walk_arm[s][i])
            pb.keyframe_insert("rotation_quaternion", frame=f)


for round_ in range(4):
    extra = {s: np.zeros(last - first + 1) for s in "LR"}
    for i, f in enumerate(range(first, last + 1)):
        scene.frame_set(f)
        V = pm.read(body)[: pm.N_BODY]
        tree = BVHTree.FromPolygons([Vector(x) for x in V], trunk_tris.tolist())
        for s in "LR":
            after[s][i] = worst(tree, s)
            pb = rig.pose.bones[f"upper_arm.{s}"]
            base = pb.rotation_quaternion.copy()
            while worst(tree, s) > 0 and opening[s][i] + extra[s][i] < MOST_DEG + BEYOND_DEG:
                extra[s][i] += STEP_DEG
                open_arm(s, extra[s][i], base)
                bpy.context.view_layer.update()
            pb.rotation_quaternion = base
    if not any(extra[s].any() for s in "LR"):
        break
    for s in "LR":
        opening[s] = smooth(opening[s] + extra[s])
    apply_opening()
pm.set_display(body, True)
scene.frame_set(first)
bpy.ops.wm.save_as_mainfile(filepath=a[0])
# worst() is how far short of the allowed sinking a point is; a point touches when it is within its radius of the skin.
deep = lambda x: (x - MARGIN_M) * 1000
report = {s: {"frames_touching": int((after[s] >= MARGIN_M).sum()), "frames_through_before": int((before[s] > 0).sum()), "deepest_before_mm": float(deep(before[s]).max()), "frames_through_after": int((after[s] > 0).sum()), "deepest_after_mm": float(deep(after[s]).max()), "largest_opening_deg": float(opening[s].max()), "mean_opening_deg": float(opening[s].mean()), "largest_wrist_deg": float(np.abs(wrist_turn[s]).max()), "mean_wrist_deg": float(np.abs(wrist_turn[s]).mean()), "frames_fingers_giving": int((finger_give[s] > 0.05).sum()), "frames_arm_past_rule": int((opening[s] > MOST_DEG + 1e-6).sum())} for s in "LR"}
json.dump(report, open(a[1], "w"), indent=1)
print(json.dumps(report))

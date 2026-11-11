"""The contact between hands and body while walking: the hand is stopped by the body, which gives under it. Run with --blend on a walking body. Args: out.blend out.json
Each frame, points along the forearm, hand and fingers are tested against the skin of the trunk and legs (the arms' own skin left out). A point may go up to SKIN_GIVES_M into the skin, which tools/skin_waves.py then dents under it;
only past that does the upper arm open, by as little as it takes, smoothed over time and keyed on top of the walk. The hand touches and slides on the body instead of being held away from it (Rafael, 2026-11-11)."""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posed_mesh as pm
import posing as P

a = hb.args()
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
scene = bpy.context.scene
MARGIN_M = -0.012  # SKIN_GIVES_M: how far a point may sink into the skin, which yields there
STEP_DEG, MOST_DEG = 0.5, 25.0
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


def open_arm(side, degrees, base):
    rest_rot = P.rest_rotation(rig, f"upper_arm.{side}")
    pb = rig.pose.bones[f"upper_arm.{side}"]
    world = rest_rot @ base.to_matrix() @ rest_rot.inverted()
    pb.rotation_quaternion = P.to_basis(rig, f"upper_arm.{side}", P.ry(-sign[side] * degrees) @ world)


first, last = scene.frame_start, scene.frame_end
needed = {s: np.zeros(last - first + 1) for s in "LR"}
before = {s: np.zeros(last - first + 1) for s in "LR"}
for i, f in enumerate(range(first, last + 1)):
    scene.frame_set(f)
    V = pm.read(body)[: pm.N_BODY]
    tree = BVHTree.FromPolygons([Vector(x) for x in V], trunk_tris.tolist())
    for s in "LR":
        pb = rig.pose.bones[f"upper_arm.{s}"]
        base = pb.rotation_quaternion.copy()
        before[s][i] = worst(tree, s)
        angle = 0.0
        while worst(tree, s) > 0 and angle < MOST_DEG:
            angle += STEP_DEG
            open_arm(s, angle, base)
            bpy.context.view_layer.update()
        needed[s][i] = angle
        pb.rotation_quaternion = base
        bpy.context.view_layer.update()


def smooth(x):
    kernel = np.hanning(2 * SMOOTH_FRAMES + 3)[1:-1]
    kernel /= kernel.sum()
    padded = np.pad(x, SMOOTH_FRAMES, mode="edge")
    return np.maximum(np.convolve(padded, kernel, mode="valid"), x)


after = {s: np.zeros(last - first + 1) for s in "LR"}
opening = {s: smooth(needed[s]) for s in "LR"}
for i, f in enumerate(range(first, last + 1)):
    scene.frame_set(f)
    for s in "LR":
        pb = rig.pose.bones[f"upper_arm.{s}"]
        base = pb.rotation_quaternion.copy()
        open_arm(s, float(opening[s][i]), base)
        pb.keyframe_insert("rotation_quaternion", frame=f)
    bpy.context.view_layer.update()
    V = pm.read(body)[: pm.N_BODY]
    tree = BVHTree.FromPolygons([Vector(x) for x in V], trunk_tris.tolist())
    for s in "LR":
        after[s][i] = worst(tree, s)
pm.set_display(body, True)
scene.frame_set(first)
bpy.ops.wm.save_as_mainfile(filepath=a[0])
# worst() is how far short of the allowed sinking a point is; a point touches when it is within its radius of the skin.
deep = lambda x: (x - MARGIN_M) * 1000
report = {s: {"frames_touching": int((after[s] >= MARGIN_M).sum()), "frames_through_before": int((before[s] > 0).sum()), "deepest_before_mm": float(deep(before[s]).max()), "frames_through_after": int((after[s] > 0).sum()), "deepest_after_mm": float(deep(after[s]).max()), "largest_opening_deg": float(opening[s].max()), "mean_opening_deg": float(opening[s].mean())} for s in "LR"}
json.dump(report, open(a[1], "w"), indent=1)
print(json.dumps(report))

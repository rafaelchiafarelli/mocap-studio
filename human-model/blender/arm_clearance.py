"""Keeps the forearms, hands and fingers outside the body while walking: a collision solved on the pose, not simulated. Run with --blend on a walking body. Args: out.blend out.json
Each frame, points along the forearm, hand and middle finger are tested against the skin of the trunk and legs (the arms' own skin left out). Where a point is inside, or closer than its radius plus MARGIN_M, the upper arm opens outwards a little at a time.
The opening found per frame is then widened and smoothed over time so the arm doesn't jerk, and keyed on top of the walk."""
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
MARGIN_M = 0.01
STEP_DEG, MOST_DEG = 1.5, 25.0
SMOOTH_FRAMES = 4  # the opening is held this many frames either side, then eased
sign = {"L": 1, "R": -1}
ARM_BONES = ("upper_arm", "forearm", "hand", "palm", "f_", "thumb", "shoulder")
POINTS = [("forearm", 0.5, 0.040), ("forearm", 1.0, 0.032), ("hand", 0.5, 0.025), ("hand", 1.0, 0.020), ("f_middle.03", 1.0, 0.010), ("f_index.03", 1.0, 0.010), ("f_pinky.03", 1.0, 0.010)]

pm.set_display(body, False)
tris = pm.triangles(body)
arm_weight = np.zeros(pm.N_BODY)
groups = {g.index: g.name for g in body.vertex_groups}
for v in body.data.vertices[: pm.N_BODY]:
    for g in v.groups:
        name = groups[g.group]
        if any(name.startswith(b) for b in ARM_BONES):
            arm_weight[v.index] += g.weight
trunk_tris = tris[(arm_weight[tris] < 0.2).all(axis=1)]


def points(side):
    pts = []
    for bone, along, radius in POINTS:
        name = f"{bone}.{side}"
        if name not in rig.pose.bones:
            continue
        pb = rig.pose.bones[name]
        p = rig.matrix_world @ (pb.head + along * (pb.tail - pb.head))
        pts.append((p, radius))
    return pts


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
    held = np.array([x[max(0, i - SMOOTH_FRAMES): i + SMOOTH_FRAMES + 1].max() for i in range(len(x))])
    kernel = np.hanning(2 * SMOOTH_FRAMES + 3)[1:-1]
    kernel /= kernel.sum()
    padded = np.pad(held, SMOOTH_FRAMES, mode="edge")
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
report = {s: {"frames_touching_before": int((before[s] > MARGIN_M).sum()), "deepest_before_mm": float(before[s].max() * 1000), "frames_touching_after": int((after[s] > MARGIN_M).sum()), "deepest_after_mm": float(after[s].max() * 1000), "largest_opening_deg": float(opening[s].max()), "mean_opening_deg": float(opening[s].mean())} for s in "LR"}
json.dump(report, open(a[1], "w"), indent=1)
print(json.dumps(report))

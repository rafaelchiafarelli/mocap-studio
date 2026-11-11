"""The contact between hands and body while walking: the hand is stopped by the body, and both give. Run with --blend on a walking body. Args: out.blend out.json
Each frame, points along the forearm, hand and fingers are tested against the skin of the trunk and legs (the arms' own skin left out). A point may go 5 mm into the skin, which tools/skin_waves.py
dents under it. Past that, in order, each by as little as it takes (Rafael, 2026-11-11):
  1. the fingers straighten;
  2. the elbow bends further, up to ELBOW_MOST_DEG;
  3. the wrist bends on its own hinge, up to WRIST_MOST_DEG, whichever way frees the hand;
  4. the shoulder opens the arm, MOST_DEG by rule, and up to BEYOND_DEG more only to keep the hand out, counted apart.
Each give is smoothed over time, never below what a frame needs, and keyed on top of the walk. Then rounds close whatever smoothing undid, elbow first, then shoulder.
This is geometry, not physics: no mass, no friction (see the explainer in the review folder)."""
import json, math, os, sys
import bpy
import numpy as np
from mathutils import Quaternion, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hand_points as hp
import hmblender as hb
import posed_mesh as pm
import posing as P

a = hb.args()
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
scene = bpy.context.scene
MARGIN_M = -0.005  # a point may sink this far into the skin, which yields there (Rafael: 5 mm at most)
ELBOW_MOST_DEG = 20.0
WRIST_MOST_DEG = 10.0
STEP_DEG, MOST_DEG = 0.5, 5.0  # the shoulder: never more than MOST_DEG on its own (Rafael's rule)
BEYOND_DEG = 20.0
SMOOTH_FRAMES = 2
FINGERS = ("f_index", "f_middle", "f_ring", "f_pinky", "thumb")
sign = {"L": 1, "R": -1}

pm.set_display(body, False)
tris = pm.triangles(body)
arm_weight = hp.arm_weight(body, pm.N_BODY)
trunk_tris = tris[(arm_weight[tris] < 0.2).all(axis=1)]
first, last = scene.frame_start, scene.frame_end
n = last - first + 1


def tree_now():
    V = pm.read(body)[: pm.N_BODY]
    return BVHTree.FromPolygons([Vector(x) for x in V], trunk_tris.tolist())


def worst(tree, side):
    """How far the deepest point is past what the skin may give, in metres; 0 when all are clear."""
    short = 0.0
    for p, radius in hp.points(rig, side):
        location, normal, _, _ = tree.find_nearest(p)
        if location is not None:
            short = max(short, radius + MARGIN_M - (p - location).dot(normal))
    return short


def bones(side):
    fingers = [rig.pose.bones[f"{f}.0{i}.{side}"] for f in FINGERS for i in (1, 2, 3) if f"{f}.0{i}.{side}" in rig.pose.bones]
    return rig.pose.bones[f"upper_arm.{side}"], rig.pose.bones[f"forearm.{side}"], rig.pose.bones[f"hand.{side}"], fingers


def saved_pose(side):
    upper, fore, hand, fingers = bones(side)
    return upper.rotation_quaternion.copy(), fore.rotation_quaternion.copy(), hand.rotation_quaternion.copy(), [f.rotation_quaternion.copy() for f in fingers]


def hinge_sign(side, bone, towards):
    """The local X turn of `bone` that moves the hand's tip along `towards` (a world direction): which way the elbow and wrist bend on this rig."""
    pb = rig.pose.bones[f"{bone}.{side}"]
    tip = rig.pose.bones[f"hand.{side}"]
    saved = pb.rotation_quaternion.copy()
    moved = {}
    for s in (1, -1):
        pb.rotation_quaternion = saved @ Quaternion((1, 0, 0), math.radians(10 * s))
        bpy.context.view_layer.update()
        moved[s] = Vector(towards).dot(rig.matrix_world @ tip.tail)
    pb.rotation_quaternion = saved
    bpy.context.view_layer.update()
    return 1 if moved[1] > moved[-1] else -1


def pose(side, base, fingers=0.0, elbow=0.0, wrist=0.0, shoulder=0.0):
    """Sets the arm from its walk pose `base` plus each give."""
    upper, fore, hand, finger_bones = bones(side)
    u, fo, h, fs = base
    world = P.rest_rotation(rig, f"upper_arm.{side}") @ u.to_matrix() @ P.rest_rotation(rig, f"upper_arm.{side}").inverted()
    upper.rotation_quaternion = P.to_basis(rig, f"upper_arm.{side}", P.ry(-sign[side] * shoulder) @ world) if shoulder else u
    fore.rotation_quaternion = fo @ Quaternion((1, 0, 0), math.radians(elbow * elbow_sign[side]))
    hand.rotation_quaternion = h @ Quaternion((1, 0, 0), math.radians(wrist))
    for pb, q in zip(finger_bones, fs):
        pb.rotation_quaternion = q.slerp((1, 0, 0, 0), fingers)


def key(side, f):
    upper, fore, hand, fingers = bones(side)
    for pb in [upper, fore, hand] + fingers:
        pb.keyframe_insert("rotation_quaternion", frame=f)


scene.frame_set(first)
elbow_sign = {s: hinge_sign(s, "forearm", (0, -1, 0)) for s in "LR"}  # bending brings the hand forward
gives = {s: {k: np.zeros(n) for k in ("fingers", "elbow", "wrist", "shoulder")} for s in "LR"}
before = {s: np.zeros(n) for s in "LR"}
base = {s: [] for s in "LR"}
for i, f in enumerate(range(first, last + 1)):
    scene.frame_set(f)
    tree = tree_now()
    for s in "LR":
        b = saved_pose(s)
        base[s].append(b)
        before[s][i] = worst(tree, s)
        g = {"fingers": 0.0, "elbow": 0.0, "wrist": 0.0, "shoulder": 0.0}

        def clear():
            pose(s, b, **g)
            bpy.context.view_layer.update()
            return worst(tree, s) <= 0

        while not clear() and g["fingers"] < 1.0:
            g["fingers"] = min(1.0, g["fingers"] + 0.1)
        while not clear() and g["elbow"] < ELBOW_MOST_DEG:
            g["elbow"] += STEP_DEG
        if not clear():
            trial = {}
            for d in (1.0, -1.0):
                g["wrist"] = d * 5.0
                clear()
                trial[d] = worst(tree, s)
            way = 1.0 if trial[1.0] <= trial[-1.0] else -1.0
            g["wrist"] = 0.0
            while not clear() and abs(g["wrist"]) < WRIST_MOST_DEG:
                g["wrist"] += way * STEP_DEG
        while not clear() and g["shoulder"] < MOST_DEG + BEYOND_DEG:
            g["shoulder"] += STEP_DEG
        for k, v in g.items():
            gives[s][k][i] = v
        pose(s, b)
    bpy.context.view_layer.update()


def smooth(x):
    """Eased over time, never below what a frame needs, keeping the sign of a two-way give."""
    size = np.abs(x)
    kernel = np.hanning(2 * SMOOTH_FRAMES + 3)[1:-1]
    kernel /= kernel.sum()
    eased = np.maximum(np.convolve(np.pad(size, SMOOTH_FRAMES, mode="edge"), kernel, mode="valid"), size)
    way = np.sign(x)
    known = np.nonzero(way)[0]
    if known.size:
        way = way[known[np.abs(np.arange(len(x))[:, None] - known[None]).argmin(axis=1)]]
    else:
        way = np.ones(len(x))
    return eased * way


def apply_all():
    for i, f in enumerate(range(first, last + 1)):
        scene.frame_set(f)
        for s in "LR":
            pose(s, base[s][i], **{k: float(v[i]) for k, v in gives[s].items()})
            key(s, f)


for s in "LR":
    for k in gives[s]:
        gives[s][k] = smooth(gives[s][k])
apply_all()
after = {s: np.zeros(n) for s in "LR"}
for round_ in range(5):
    extra = False
    for i, f in enumerate(range(first, last + 1)):
        scene.frame_set(f)
        tree = tree_now()
        for s in "LR":
            g = {k: float(v[i]) for k, v in gives[s].items()}
            after[s][i] = worst(tree, s)
            if after[s][i] <= 0:
                continue
            extra = True
            while after[s][i] > 0 and (g["elbow"] < ELBOW_MOST_DEG or g["shoulder"] < MOST_DEG + BEYOND_DEG):
                if g["elbow"] < ELBOW_MOST_DEG:
                    g["elbow"] += STEP_DEG
                else:
                    g["shoulder"] += STEP_DEG
                pose(s, base[s][i], **g)
                bpy.context.view_layer.update()
                after[s][i] = worst(tree, s)
            gives[s]["elbow"][i], gives[s]["shoulder"][i] = g["elbow"], g["shoulder"]
    if not extra:
        break
    for s in "LR":
        gives[s]["elbow"] = smooth(gives[s]["elbow"])
        gives[s]["shoulder"] = smooth(gives[s]["shoulder"])
    apply_all()

pm.set_display(body, True)
scene.frame_set(first)
bpy.ops.wm.save_as_mainfile(filepath=a[0])
deep = lambda x: (x - MARGIN_M) * 1000
report = {s: {"frames_through_before": int((before[s] > 0).sum()), "deepest_before_mm": float(deep(before[s]).max()), "frames_through_after": int((after[s] > 0).sum()),
              "frames_fingers_giving": int((gives[s]["fingers"] > 0.05).sum()),
              "elbow_extra_largest_deg": float(gives[s]["elbow"].max()), "elbow_extra_mean_deg": float(gives[s]["elbow"].mean()),
              "wrist_largest_deg": float(np.abs(gives[s]["wrist"]).max()), "wrist_mean_deg": float(np.abs(gives[s]["wrist"]).mean()),
              "shoulder_largest_deg": float(gives[s]["shoulder"].max()), "frames_shoulder_past_rule": int((gives[s]["shoulder"] > MOST_DEG + 1e-6).sum())} for s in "LR"}
json.dump(report, open(a[1], "w"), indent=1)
print(json.dumps(report))

"""Measures skin against bones while walking. Args: out.json [step]. Run with --blend on a file from walk.py.
For each sampled frame, and at rest: how far each skin vertex is from the nearest bone, where a bone comes out through the skin, and how much the nipple moves in the rib cage's own frame, which is zero if the breast only rides on the trunk."""
import json, sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]
step = int(a[1]) if len(a) > 1 else 3
N_BODY = 13380
scene = bpy.context.scene
rig = bpy.data.objects["HM_rig"]
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
bones = [o for o in bpy.data.objects if o.type == "MESH" and o.parent_type == "BONE" and o.parent == rig]
REGIONS = {"breast": ("breast.L", "breast.R"), "hip": ("pelvis.L", "pelvis.R"), "thigh": ("thigh.L", "thigh.R"), "knee_shin": ("shin.L", "shin.R"), "shoulder": ("shoulder.L", "shoulder.R"), "upper_arm": ("upper_arm.L", "upper_arm.R"), "forearm": ("forearm.L", "forearm.R")}
region_verts = {}
for name, groups in REGIONS.items():
    ids = {skin.vertex_groups[g].index for g in groups if g in skin.vertex_groups}
    region_verts[name] = np.array([v.index for v in skin.data.vertices[:N_BODY] if any(e.group in ids and e.weight > 0.5 for e in v.groups)], dtype=np.int32)
nipple_group = skin.vertex_groups["nippleTip"].index
nipples = np.array([v.index for v in skin.data.vertices[:N_BODY] if any(e.group == nipple_group for e in v.groups)], dtype=np.int32)


def skin_state():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = skin.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co, normal = np.empty(n * 3), np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    me.vertex_normals.foreach_get("vector", normal)
    ev.to_mesh_clear()
    M = np.array(skin.matrix_world)[:3, :3]
    world = co.reshape(-1, 3) @ M.T + np.array(skin.matrix_world)[:3, 3]
    return world[:N_BODY], (normal.reshape(-1, 3) @ M.T)[:N_BODY]


def bone_tree():
    points, owner = [], []
    for ob in bones:
        c = np.empty(len(ob.data.vertices) * 3)
        ob.data.vertices.foreach_get("co", c)
        M = np.array(ob.matrix_world)
        points.append(c.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])
        owner += [ob.name] * len(ob.data.vertices)
    points = np.concatenate(points)
    tree = KDTree(len(points))
    for i, p in enumerate(points):
        tree.insert(p, i)
    tree.balance()
    return tree, points, owner


def sample():
    bpy.context.view_layer.update()
    co, normal = skin_state()
    tree, points, owner = bone_tree()
    index = np.array([tree.find(Vector(p))[1] for p in co])
    delta = points[index] - co
    distance = np.linalg.norm(delta, axis=1)
    poking = (delta * normal).sum(1) > 0  # the nearest bone point is outside the skin
    worst = {}
    for i in np.flatnonzero(poking):
        worst[owner[index[i]]] = worst.get(owner[index[i]], 0) + 1
    regions = {name: {"min_mm": round(float(distance[v].min() * 1000), 1), "poking": int(poking[v].sum())} for name, v in region_verts.items() if len(v)}
    thorax = np.array((rig.matrix_world @ rig.pose.bones["spine.003"].matrix).inverted())
    local = co[nipples] @ thorax[:3, :3].T + thorax[:3, 3]
    return {"poking": int(poking.sum()), "min_mm": round(float(distance.min() * 1000), 1), "under_3mm": int((distance < 0.003).sum()), "bones": dict(sorted(worst.items(), key=lambda x: -x[1])[:8]), "regions": regions, "nipple_local": local.mean(0).tolist()}


rig.data.pose_position = "REST"
scene.frame_set(scene.frame_start)
rest = sample()
rig.data.pose_position = "POSE"
frames = {}
for f in range(scene.frame_start, scene.frame_end + 1, step):
    scene.frame_set(f)
    frames[f] = sample()
    print("frame", f, frames[f]["poking"], flush=True)
local = np.array([frames[f]["nipple_local"] for f in frames])
peak = {name: {"min_mm": min(frames[f]["regions"][name]["min_mm"] for f in frames), "poking_max": max(frames[f]["regions"][name]["poking"] for f in frames)} for name in rest["regions"]}
summary = {"rest": {k: rest[k] for k in ("poking", "min_mm", "under_3mm", "bones", "regions")}, "walk_poking_max": max(frames[f]["poking"] for f in frames), "walk_min_mm": min(frames[f]["min_mm"] for f in frames),
           "walk_regions": peak, "nipple_range_in_thorax_mm": (np.ptp(local, axis=0) * 1000).round(1).tolist(), "frames": frames}
json.dump(summary, open(out, "w"), indent=1)
print("rest poking", rest["poking"], "walk max", summary["walk_poking_max"], "nipple range mm", summary["nipple_range_in_thorax_mm"])

"""Finds each fold's line on the skin and how the rig drives it, and writes data/folds.json. Run with --blend on a clean body. Args: out.json
A fold is declared by where it sits relative to a bone: a plane, a sector around the limb's axis, and a pose of the rig that deepens it. Vertices come from the skin nearest that plane; the pose gives the bone's local rotation at full depth, read once so the file holds plain numbers."""
import json, math, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posed_mesh as pm
import posing as P

a = hb.args()
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
pm.set_display(body, False)
P.reset(rig)
bpy.context.view_layer.update()
V = pm.read(body)[: pm.N_BODY]
BAND = 0.018  # how far from the plane a vertex may be
BINS = 28  # how many steps around the sector; each keeps one vertex
sign = {"L": 1, "R": -1}
M = np.array(rig.matrix_world)


def point(bone, along=0.0):
    b = rig.data.bones[bone]
    head, tail = np.array(b.head_local), np.array(b.tail_local)
    return (head + along * (tail - head)) @ M[:3, :3].T + M[:3, 3], (tail - head) / np.linalg.norm(tail - head) @ M[:3, :3].T


FORWARD, BACK, UP = np.array([0.0, -1.0, 0.0]), np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])


def line(center, normal, facing, half_angle, reach, world_z_cut=None):
    """The skin vertices around `center` in the plane through it, within half_angle of `facing`, one per angular step, nearest the plane."""
    normal = normal / np.linalg.norm(normal)
    facing = facing - facing.dot(normal) * normal
    facing /= np.linalg.norm(facing)
    side = np.cross(normal, facing)
    rel = V - center
    off = rel @ normal
    x, y = rel @ facing, rel @ side
    angle = np.degrees(np.arctan2(y, x))
    ok = (np.abs(off) < BAND) & (np.abs(angle) <= half_angle) & (np.hypot(x, y) < reach)
    if world_z_cut is not None:
        ok &= (V[:, 2] > world_z_cut[0]) & (V[:, 2] < world_z_cut[1])
    picks = []
    edges = np.linspace(-half_angle, half_angle, BINS + 1)
    for lo, hi in zip(edges, edges[1:]):
        idx = np.nonzero(ok & (angle >= lo) & (angle < hi))[0]
        if idx.size:
            picks.append(int(idx[np.argmin(np.abs(off[idx]))]))
    return list(dict.fromkeys(picks))


def euler_at(bone, rotation):
    """The bone's local rotation at rest and at the pose that deepens the fold, and the axis that moves most."""
    P.reset(rig)
    if rotation is not None:
        P.set_rotation(rig, bone, rotation)
    bpy.context.view_layer.update()
    e = rig.pose.bones[bone].matrix_basis.to_euler("XYZ")
    P.reset(rig)
    return [e.x, e.y, e.z]


def driver_for(bone, rotation):
    rest, deep = euler_at(bone, None), euler_at(bone, rotation)
    k = int(np.argmax(np.abs(np.array(deep) - np.array(rest))))
    return {"bone": bone, "axis": "XYZ"[k], "rest": rest[k], "deep": deep[k]}


def axis_at(z):
    """The middle of the trunk's section at a height: the spine's bones run near the back, so a sector around them is lopsided."""
    near = V[(np.abs(V[:, 2] - z) < 0.02) & (np.abs(V[:, 0]) < 0.20)]
    return np.array([0.0, near[:, 1].mean(), z])


folds, skipped = [], []


def add(name, side, verts, driver, depth_mm, width_cm, at_rest):
    if len(verts) < 5:
        skipped.append(name + (f".{side}" if side else ""))
        return
    folds.append({"name": name, "side": side, "vertices": verts, "driver": driver, "depth_mm": depth_mm, "width_cm": width_cm, "at_rest": at_rest})


for s in "LR":
    g = sign[s]
    out = np.array([float(g), 0.0, 0.0])
    # Under the buttock: across the back of the thigh's top. Standing, it already exists; a leg behind the body deepens it.
    hip, thigh_dir = point(f"thigh.{s}", 0.26)
    add("sob_gluteo", s, line(hip, thigh_dir + np.array([0, 0.25, 0]), BACK + 0.15 * out, 62, 0.16), driver_for(f"thigh.{s}", P.rx(25)), 14, 3.0, 0.6)
    # The groin: across the front of the thigh's top, deepened by flexing the hip.
    hip2, _ = point(f"thigh.{s}", 0.10)
    add("virilha", s, line(hip2, thigh_dir + np.array([g * 0.35, -0.55, 0]), FORWARD + 0.5 * out, 60, 0.17), driver_for(f"thigh.{s}", P.rx(-90)), 15, 2.8, 0.2)
    # Back of the knee.
    knee, shin_dir = point(f"shin.{s}", 0.0)
    add("atras_do_joelho", s, line(knee, shin_dir, BACK, 70, 0.11), driver_for(f"shin.{s}", P.rx(120)), 12, 2.2, 0.1)
    # Inner elbow.
    elbow, fore_dir = point(f"forearm.{s}", 0.0)
    add("dentro_do_cotovelo", s, line(elbow, fore_dir, FORWARD + 0.3 * out, 75, 0.09), driver_for(f"forearm.{s}", P.rx(-130)), 8, 1.6, 0.05)
    # Armpit, front and back, deepened as the arm comes down from the rest pose's A.
    shoulder, arm_dir = point(f"upper_arm.{s}", 0.18)
    arm_rotation = P.ry(g * P.hang_angle(rig, f"upper_arm.{s}", 0.0))
    add("axila_frente", s, line(shoulder, arm_dir, FORWARD - 0.7 * out, 45, 0.13), driver_for(f"upper_arm.{s}", arm_rotation), 9, 2.0, 0.2)
    add("axila_atras", s, line(shoulder, arm_dir, BACK - 0.7 * out, 45, 0.13), driver_for(f"upper_arm.{s}", arm_rotation), 9, 2.0, 0.2)
    # Under the breast, from the group MPFB weights to the breast: the lowest vertices of its front.
    group = body.vertex_groups.get(f"breast.{s}")
    if group is not None:
        weights = np.zeros(pm.N_BODY)
        for v in body.data.vertices[: pm.N_BODY]:
            for g2 in v.groups:
                if g2.group == group.index:
                    weights[v.index] = g2.weight
        inside = np.nonzero(weights > 0.45)[0]
        if inside.size:
            c = V[inside].mean(0)
            z = np.percentile(V[inside, 2], 3)
            add("sob_o_seio", s, line(np.array([c[0], c[1] + 0.015, z]), UP, FORWARD, 72, 0.14), driver_for("spine.002", P.rx(15)), 16, 3.2, 0.7)
    # The side of the waist, deepened by leaning to that side.
    waist, _ = point("spine.002", 0.1)
    waist = axis_at(waist[2])
    lean = P.ry(-g * 15)
    add("lado_da_cintura", s, line(waist, UP, out, 42, 0.25), driver_for("spine.001", lean), 11, 3.0, 0.15)
# Across the belly, below the navel, deepened by bending forward.
belly, _ = point("spine.001", -0.4)
add("barriga", "", line(axis_at(belly[2]), UP, FORWARD, 62, 0.25), driver_for("spine.001", P.rx(15)), 13, 3.4, 0.05)

pm.set_display(body, True)
out = {"_about": "The folds of the skin (initiative animation-body). Written by blender/fold_lines.py; the depths and widths are by eye. vertices: the line, in MPFB's skin order. driver: the bone's local Euler axis, its value at rest and at full depth. at_rest: the share of the depth already there at rest.", "folds": folds}
with open(a[0], "w", encoding="utf-8") as f:
    json.dump(out, f, indent=0)
print("folds", len(folds), "skipped", skipped)
for x in folds:
    print(f"{x['name']:20}{x['side']:2} vertices {len(x['vertices']):3}  {x['driver']['bone']:14} eixo {x['driver']['axis']} {x['driver']['rest']:+.2f} -> {x['driver']['deep']:+.2f}")

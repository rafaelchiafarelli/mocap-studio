"""The lips touch, press and give, on a face driven by the mouth faders (initiative animation-face, epic lip-contact; Rafael, 2026-11-12). Run with --blend on a faders file. Args: out.blend out.json [first-last, to try a stretch]
Each frame, in the head's frame:
  1. the orbicularis pulls: at an M (also P and B) the lips seal along the whole width, as much as the faders' mouthPress asks (only the M pose has it): each point of
     either lip's edge, paired at rest with the nearest point of the other lip, meets it halfway, like a zipper; at an F the lower lip's edge goes to the upper incisors' edge
     and presses PRESS_M on it, as much as lipBite asks (only the F pose has it);
  2. the teeth don't give: a lip inside them is pushed out;
  3. the give spreads to the lip around it, smoothly.
A first try met the lips by vertical rays against each other's skin; on the coarse, curved lips it read a lip behind the other as inside it, and left the sides open.
The offsets go back to the rest pose through each vertex's bones, and are baked as one shape key per frame with contact, played by driver; the fader lip_contact (0 to 2) on
HM_controls scales them all, 0 being the faders alone. The faders' animation is baked first: if the faders change, run this again. lip_contact_check.py measures the result."""
import json, os, sys
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posed_mesh as pm

PRESS_M = 0.0015  # how far the lips push into each other, or the lower lip onto the teeth, before they give: by eye
SEAM_M = 0.005  # a lip point within this of the other lip at rest is on the edge where they meet
SPREAD_ROUNDS = 12  # rounds of spreading the give to neighbouring vertices
ROUNDS = 3  # drive, contact and spread, repeated
CLEAR_M = 0.0002  # a lip pushed out of the teeth stops this far outside

a = hb.args()
scene = bpy.context.scene
body, teeth = bpy.data.objects["HM_body"], bpy.data.objects["HM_teeth"]
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
ctrl_mouth = next(o for o in bpy.data.objects if o.type == "EMPTY" and "jawOpen" in o.keys())
N = pm.N_BODY


def weights(obj, prefix, n):
    names = {g.index for g in obj.vertex_groups if g.name.startswith(prefix)}
    w = np.zeros(len(obj.data.vertices))
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group in names:
                w[v.index] += g.weight
    return w[:n]


top, bottom = weights(body, "lip.T", N), weights(body, "lip.B", N)
lips_group = weights(body, "lips", N)
region = np.nonzero(top + bottom > 0.05)[0]  # what may move: everything the lip bones move
upper = np.nonzero((top > bottom) & (top > 0.3))[0]
lower = np.nonzero((bottom > top) & (bottom > 0.3))[0]
tris = pm.triangles(body)
scene.frame_set(scene.frame_start)
pm.set_display(body, False)
_rest = pm.read(body)[:N]
pairs = []  # (lip point, the other lip's point) on the edge where they meet, from either side
for mine, other in ((upper, lower), (lower, upper)):
    for i in mine:
        d = np.linalg.norm(_rest[other] - _rest[i], axis=1)
        if d.min() < SEAM_M:
            pairs.append((i, int(other[d.argmin()])))
seam_lower = np.array(sorted({i for i, _ in pairs if i in set(lower.tolist())}))
teeth_top = weights(teeth, "teeth.T", len(teeth.data.vertices)) > 0.5
teeth_tris = [list(p.vertices) for p in teeth.data.polygons]
upper_teeth_tris = [t for t in teeth_tris if teeth_top[t].all()]
neighbours = {i: set() for i in region}
in_region = set(region.tolist())
for e in body.data.edges:
    i, j = e.vertices
    if i in in_region and j in in_region:
        neighbours[i].add(j)
        neighbours[j].add(i)
spread_w = np.clip((top + bottom)[region], 0, 1)  # the give fades where the lip bones' hold fades


def channel(name):
    fc = ctrl_mouth.animation_data.action.fcurves.find(f'["{name}"]') if hasattr(ctrl_mouth.animation_data.action, "fcurves") else None
    if fc is None:
        from bpy_extras import anim_utils
        bag = anim_utils.action_get_channelbag_for_slot(ctrl_mouth.animation_data.action, ctrl_mouth.animation_data.action_slot)
        fc = bag.fcurves.find(f'["{name}"]')
    return np.array([fc.evaluate(f) for f in range(scene.frame_start, scene.frame_end + 1)]) if fc else np.zeros(scene.frame_end - scene.frame_start + 1)


press = channel("mouthPressLeft")
bite = channel("lipBite")
press, bite = press / max(press.max(), 1e-6), bite / max(bite.max(), 1e-6)


def head_matrix():
    return np.array(rig.matrix_world @ rig.pose.bones["spine.006"].matrix)


def to_head(points, m):
    inv = np.linalg.inv(m)
    return points @ inv[:3, :3].T + inv[:3, 3]


def teeth_world():
    ev = teeth.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return np.array([teeth.matrix_world @ v.co for v in ev.data.vertices])


def spread(D, fixed):
    """Spreads the give D (region vertices) to unfixed neighbours, fading with the lip bones' hold."""
    idx = {v: k for k, v in enumerate(region)}
    for _ in range(SPREAD_ROUNDS):
        new = D.copy()
        for k, v in enumerate(region):
            if fixed[k] or not neighbours[v]:
                continue
            new[k] = np.mean([D[idx[j]] for j in neighbours[v]], axis=0) * spread_w[k]
        D = new
    return D


def solve(V, T, p, b):
    """The offsets of the region's vertices this frame, in the head's frame."""
    D = np.zeros((len(region), 3))
    idx = {v: k for k, v in enumerate(region)}
    up_idx = np.array([idx[v] for v in upper])
    lo_idx = np.array([idx[v] for v in lower])
    top_teeth = BVHTree.FromPolygons([Vector(x) for x in T], upper_teeth_tris)
    all_teeth = BVHTree.FromPolygons([Vector(x) for x in T], teeth_tris)
    pinned = np.zeros(len(region), bool)  # what the pull placed stays placed through the rounds
    for round_ in range(ROUNDS):
        fixed = pinned.copy()
        W = V.copy()
        W[region] += D
        # 1. the pull: at an M, every pair on the seam meets halfway
        if p > 0.02 and round_ == 0:
            for i, j in pairs:
                D[idx[i]] += p * (W[j] - W[i]) / 2
                pinned[idx[i]] = fixed[idx[i]] = True
        # at an F, the lower lip's edge to the incisors' edge, pressing a little
        if b > 0.02 and round_ == 0:
            best, move = np.inf, None
            for i in seam_lower:
                loc, normal, _, dist = top_teeth.find_nearest(Vector(W[i]))
                if loc is not None and dist < best:
                    best, move = dist, np.array(loc) - W[i]
            if move is not None:
                length = np.linalg.norm(move)
                shift = move / max(length, 1e-9) * (length + PRESS_M) * b
                D[lo_idx] += shift[None, :] * np.clip(bottom[lower], 0, 1)[:, None]
                pinned[lo_idx] = fixed[lo_idx] = True
        W = V.copy()
        W[region] += D
        # the teeth don't give
        W = V.copy()
        W[region] += D
        for v in np.concatenate([upper, lower]):
            k = idx[v]
            loc, normal, _, _ = all_teeth.find_nearest(Vector(W[v]))
            if loc is None:
                continue
            depth = (Vector(W[v]) - loc).dot(normal)
            if depth < CLEAR_M:
                D[k] += np.array(normal) * (CLEAR_M - depth)
                fixed[k] = True
        # 3. the give spreads around
        D = spread(D, fixed)
    return D


def deform_rotations():
    """Each region vertex's blended bone rotation, rest to pose, to carry an offset back to the rest pose."""
    groups = {g.index: g.name for g in body.vertex_groups}
    mats = {pb.name: np.array(pb.matrix @ pb.bone.matrix_local.inverted())[:3, :3] for pb in rig.pose.bones}
    out = np.zeros((len(region), 3, 3))
    for k, v in enumerate(region):
        total, m = 0.0, np.zeros((3, 3))
        for g in body.data.vertices[v].groups:
            name = groups.get(g.group)
            if name in mats and g.weight > 0:
                m += g.weight * mats[name]
                total += g.weight
        out[k] = m / total if total else np.eye(3)
    return out


pm.set_display(body, False)
pm.set_display(teeth, False)
first, last = scene.frame_start, scene.frame_end
lo, hi = (int(x) for x in a[2].split("-")) if len(a) > 2 else (first, last)
to_object = np.array(body.matrix_world.inverted())[:3, :3]
baked, report = {}, []
for f in range(lo, hi + 1):
    scene.frame_set(f)
    m = head_matrix()
    V = to_head(pm.read(body)[:N], m)
    T = to_head(teeth_world(), m)
    D = solve(V, T, press[f - first], bite[f - first])
    size = np.linalg.norm(D, axis=1)
    report.append({"frame": f, "press": float(press[f - first]), "bite": float(bite[f - first]), "largest_give_mm": float(size.max() * 1000)})
    if size.max() < 1e-5:
        continue
    world = D @ m[:3, :3].T  # head frame to world
    rot = deform_rotations()
    local = np.einsum("kij,kj->ki", np.linalg.inv(rot), world @ to_object.T)
    baked[f] = local
pm.set_display(body, True)
pm.set_display(teeth, True)

ctrl = hb.controls_object("HM_controls")
hb.add_prop(ctrl, "lip_contact", 1.0, 0.0, 2.0)
if body.data.shape_keys is None:
    body.shape_key_add(name="Basis", from_mix=False)
n = len(body.data.vertices)
basis = np.empty(n * 3)
body.data.shape_keys.key_blocks[0].data.foreach_get("co", basis)
basis = basis.reshape(-1, 3)
for f, local in baked.items():
    co = basis.copy()
    co[region] += local
    kb = body.shape_key_add(name=f"lips.{f:04d}", from_mix=False)
    kb.data.foreach_set("co", co.ravel())
    kb.slider_min, kb.slider_max = 0.0, 2.0
    driver = kb.driver_add("value").driver
    driver.type = "SCRIPTED"
    v = driver.variables.new()
    v.name = "a"
    v.targets[0].id, v.targets[0].data_path = ctrl, '["lip_contact"]'
    driver.expression = f"max(0,1-abs(frame-{f}))*a"
bpy.ops.wm.save_as_mainfile(filepath=a[0])
summary = {"frames": len(report), "frames_with_contact": len(baked), "largest_give_mm": max(r["largest_give_mm"] for r in report),
           "region_vertices": int(len(region)), "upper_lip": int(len(upper)), "lower_lip": int(len(lower)), "seam_pairs": len(pairs), "per_frame": report}
json.dump(summary, open(a[1], "w"), indent=1)
print("RESULT", json.dumps({k: v for k, v in summary.items() if k != "per_frame"}))

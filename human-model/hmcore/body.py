"""The whole body from the inside out, at rest: bone, muscle, fat by plastic-surgery zone, a skin band and the trunk's cavity, as tetrahedra
inside the MPFB skin (task muscle-physics/body-at-rest/1). The limb version is layers.py; this reuses its grid, tetrahedra and ties.
The head, hands and feet are cut off at the neck, wrists and ankles. Point queries run on the GPU (meshgpu.py), so this needs hm.sh --gpu."""
import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull
from . import fit, layers

BONE, MUSCLE, FAT, SKIN, CAVITY = 0, 1, 2, 3, 4
LABELS = ("bone", "muscle", "fat", "skin", "cavity")
GLUTEUS_ZONES = ("buttocks_upper_center", "buttocks_upper_side", "buttocks_lower_center", "buttocks_lower_side")
BREAST_ZONES = ("breast_L", "breast_R")
ZONES = ("neck", "chest", *BREAST_ZONES, "upper_back", "belly", "flanks", "lower_back", "hips", *GLUTEUS_ZONES,
         "thigh_front", "thigh_back", "thigh_inner", "thigh_outer", "knee", "calf_front", "calf_back",
         "upper_arm_front", "upper_arm_back", "forearm")
# Where the skin is cut: (rig bone whose head is the joint, rig bone along which the plane faces, how far from the joint the cut reaches, m)
CUTS = (("spine.006", "spine.005", 0.15), ("hand.L", "forearm.L", 0.10), ("hand.R", "forearm.R", 0.10),
        ("foot.L", "shin.L", 0.12), ("foot.R", "shin.R", 0.12))
CHEST_BONES = tuple(f"rib_{i}_{s}" for i in range(1, 13) for s in "LR") + ("costal_cartilages", "sternum")
SPINE_BONES = tuple(f"vertebra_{k}" for k in ("T1 T2 T3 T4 T5 T6 T7 T8 T9 T10 T11 T12 L1 L2 L3 L4 L5".split())) + ("sacrum",)
TRUNK_BONES = CHEST_BONES + SPINE_BONES + ("hip_L", "hip_R")
# Rig bones that pick a skin vertex's region: the nearest one wins
REGION_BONES = {"neck": ("spine.004", "spine.005"), "upper_arm": ("upper_arm.L", "upper_arm.R"), "forearm": ("forearm.L", "forearm.R"),
                "thigh": ("thigh.L", "thigh.R"), "shin": ("shin.L", "shin.R"), "breast": ("breast.L", "breast.R"),
                "trunk": ("spine", "spine.001", "spine.002", "spine.003", "pelvis.L", "pelvis.R", "shoulder.L", "shoulder.R")}


def head_vertices(n, rig, groups):
    """Vertices the rig moves mostly with the head: their weights on spine.006 and every bone under it outweigh the rest. This border is
    MPFB's own and runs under the jaw, where a plane at the head's base left the chin's underside behind as a collar (bug human-model/17)."""
    children = {}
    for name, b in rig.items():
        children.setdefault(b["parent"], []).append(name)
    head, stack = set(), ["spine.006"]
    while stack:
        b = stack.pop()
        head.add(b)
        stack += children.get(b, [])
    w_head, w_rest = np.zeros(n), np.zeros(n)
    for name, pairs in groups.items():
        if name not in rig and not name.startswith("DEF-"):
            continue  # helpers, joints and MakeHuman's own groups don't move the skin
        for i, w in pairs:
            if i < n:
                (w_head if name in head else w_rest)[i] += w
    return w_head > w_rest


def cut_skin(skin, tris, rig, groups=None):
    """The body's triangles without head, hands and feet: near each joint, vertices past its plane are dropped, then the largest piece is kept.
    With the rig's vertex groups, the head goes along its weights' border instead of a plane."""
    beyond = np.zeros(len(skin), bool)
    if groups is not None:
        beyond |= head_vertices(len(skin), rig, groups)
    for joint, along, reach in CUTS:
        if groups is not None and joint == "spine.006":
            continue
        p = np.asarray(rig[joint]["head"])
        n = np.asarray(rig[along]["tail"]) - np.asarray(rig[along]["head"])
        n /= np.linalg.norm(n)
        beyond |= ((skin - p) @ n > 0) & (np.linalg.norm(skin - p, axis=1) < reach)
    t = tris[~beyond[tris].any(axis=1)]
    return layers.cut_patch(skin, t, None, -np.inf, np.inf)


def cut_planes(skin, patch):
    """Each cut's plane, from the cut skin's own border: (centre, normal pointing out of the body, radius) per border loop."""
    middle = skin[np.unique(patch)].mean(axis=0)
    out = []
    for loop in layers.boundary_loops(patch):
        p = skin[loop]
        c = p.mean(axis=0)
        n = np.linalg.svd(p - c, full_matrices=False)[2][-1]
        if (c - middle) @ n < 0:
            n = -n
        out.append((c, n, float(np.linalg.norm(p - c, axis=1).max())))
    return out


def near_a_cut(points, rig, planes=None):
    """Points past or at the head's, a hand's or a foot's cut: a bone there leaves the cut skin by design, it isn't poking through.
    With planes (cut_planes of the cut skin), each cut is where the skin was really cut; the head's follows the rig's weights since
    bug human-model/17, so its rig plane let the neck's C4 count as 44 mm out. Without, planes at the joints, as cut_skin's."""
    out = np.zeros(len(points), bool)
    if planes is not None:
        for c, n, r in planes:
            out |= ((points - c) @ n > -0.02) & (np.linalg.norm(points - c, axis=1) < 1.5 * r + 0.05)
        return out
    for joint, along, reach in CUTS:
        p = np.asarray(rig[joint]["head"])
        n = np.asarray(rig[along]["tail"]) - np.asarray(rig[along]["head"])
        n = n / np.linalg.norm(n)
        out |= ((points - p) @ n > -0.02) & (np.linalg.norm(points - p, axis=1) < reach + 0.05)
    return out


def segment_distance(points, a, b):
    """Distance from each point to the segment a-b, and the closest point on it."""
    d = b - a
    t = np.clip((points - a) @ d / max(d @ d, 1e-12), 0, 1)
    c = a + t[:, None] * d
    return np.linalg.norm(points - c, axis=1), c


def zones(skin, ids, rig, bones, knee=0.06):
    """A zone for each skin vertex in ids. The region is the nearest of REGION_BONES; on the trunk the zone is by height,
    against the bottom of the rib cage and the top of the hip bones, and by direction from the trunk's middle. The body faces -Y."""
    p = skin[ids]
    names, which = [], []
    best = np.full(len(p), np.inf)
    region = np.empty(len(p), object)
    nearest = np.empty(len(p), object)
    for r, bone_names in REGION_BONES.items():
        for b in bone_names:
            d, _ = segment_distance(p, np.asarray(rig[b]["head"]), np.asarray(rig[b]["tail"]))
            m = d < best
            best[m], region[m], nearest[m] = d[m], r, b
    rib_bottom = min(bones[b][0][:, 2].min() for b in CHEST_BONES if b.startswith("rib"))
    iliac_top = max(bones[b][0][:, 2].max() for b in ("hip_L", "hip_R"))
    out = np.empty(len(p), object)
    for i, (q, r, b) in enumerate(zip(p, region, nearest)):
        head, tail = np.asarray(rig[b]["head"]), np.asarray(rig[b]["tail"])
        _, c = segment_distance(q[None], head, tail)
        rel = q - c[0]
        side = 1.0 if q[0] > 0 else -1.0  # the body's left is +X
        if r == "neck" or r == "forearm":
            out[i] = r
        elif r == "upper_arm":
            out[i] = "upper_arm_front" if rel[1] < 0 else "upper_arm_back"
        elif r == "thigh":
            w = layers.zone_weights(q[None], c[0], (head - tail) / np.linalg.norm(head - tail), side)[0]
            out[i] = ("thigh_front", "thigh_back", "thigh_inner", "thigh_outer")[int(w.argmax())]
        elif r == "shin":
            out[i] = "knee" if np.linalg.norm(q - head) < knee else ("calf_front" if rel[1] < 0 else "calf_back")
        elif r == "breast":
            out[i] = "breast" if rel[1] < 0 else "upper_back"
        else:
            # The trunk: front, back or side, from the trunk's middle at this height
            band = p[(np.abs(p[:, 2] - q[2]) < 0.01) & (np.abs(p[:, 0]) < 0.2)]
            mid_y = band[:, 1].mean() if len(band) else 0.0
            dx, dy = q[0], q[1] - mid_y
            facing = "front" if -dy > abs(dx) else "back" if dy > abs(dx) else "side"
            if q[2] >= rib_bottom:
                out[i] = "chest" if facing == "front" else "upper_back"
            elif q[2] >= iliac_top:
                out[i] = {"front": "belly", "side": "flanks", "back": "lower_back"}[facing]
            else:
                out[i] = {"front": "belly", "side": "hips", "back": "buttocks"}[facing]
    return out


def divide_zones(points, zone):
    """The gluteus into upper and lower and centre and side, the breast into left and right, for the shapes. Upper and lower at the middle height of
    the buttocks' own points, centre and side at the middle of their distance from the midline. Left is +X."""
    out = zone.copy()
    glute = zone == "buttocks"
    if glute.any():
        p = points[glute]
        high = p[:, 2] >= (p[:, 2].min() + p[:, 2].max()) / 2
        side = np.abs(p[:, 0]) >= np.median(np.abs(p[:, 0]))
        out[glute] = [f"buttocks_{'upper' if h else 'lower'}_{'side' if s else 'center'}" for h, s in zip(high, side)]
    breast = zone == "breast"
    out[breast] = ["breast_L" if x > 0 else "breast_R" for x in points[breast, 0]]
    return out


def smooth_on_surface(values, tris, n_verts, iterations):
    """Averages each vertex with its neighbours, so a value changes gradually between zones instead of in steps."""
    edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    edges = np.concatenate([edges, edges[:, ::-1]])
    deg = np.bincount(edges[:, 0], minlength=n_verts)
    v = np.asarray(values, float).copy()
    for _ in range(iterations):
        s = np.bincount(edges[:, 0], weights=v[edges[:, 1]], minlength=n_verts)
        v = np.where(deg > 0, 0.5 * v + 0.5 * s / np.maximum(deg, 1), v)
    return v


def inside_hull(points, hull, eps=1e-9):
    out = np.empty(len(points), bool)
    for s in range(0, len(points), 200_000):
        out[s:s + 200_000] = np.all(points[s:s + 200_000] @ hull.equations[:, :3].T + hull.equations[:, 3] <= eps, axis=1)
    return out


def spine_front(bones, z, band=0.01):
    """For each height, the front of the spine (its smallest y), or +inf where there's no vertebra: the cavity lies in front of it."""
    pts = np.concatenate([bones[b][0] for b in SPINE_BONES])
    out = np.full(len(z), np.inf)
    zs = np.unique(np.round(z, 3))
    for value in zs:
        near = pts[np.abs(pts[:, 2] - value) < band]
        if len(near):
            out[np.round(z, 3) == value] = near[:, 1].min()
    return out


def island_cleanup(grid_labels, label, into, min_voxels):
    """Pieces of one label smaller than min_voxels become another label. Returns how many voxels moved."""
    lab, n = ndimage.label(grid_labels == label)
    if n == 0:
        return 0
    size = np.bincount(lab.ravel())
    small = (size < min_voxels) & (np.arange(len(size)) > 0)
    m = small[lab]
    grid_labels[m] = into
    return int(m.sum())


def tet_zones(zone_of_included, included, shape, vox, tet_voxel):
    """The zone index of each tetrahedron: zone_of_included gives one for each included voxel, in grid order (included is the flat mask over the whole grid)."""
    grid_zone = np.full(int(np.prod(shape)), -1, np.int16)
    grid_zone[included] = zone_of_included
    return grid_zone.reshape(shape)[tuple(vox.T)][tet_voxel]


def outward(verts, tris):
    """fit.outward. Builds made before bug human-model/11 was fixed have the left leg's bones inside out, and a winding number of -1
    called them outside (body_v2 had no left femur), so every bone is still turned outward before use."""
    return fit.outward(verts, tris)


def build(skin, tris, rig, bones, fat_mm, structure, h, gpu_mesh, groups=None):
    """Everything for the body. bones: {name: (verts, tris)}. fat_mm: {zone: mm}. structure: declared depths in mm and smoothing.
    gpu_mesh: meshgpu.Mesh, passed in so this module imports without Warp. groups: the rig's vertex groups, for the head's cut.
    Returns a dict of arrays, every intermediate kept."""
    patch = cut_skin(skin, tris, rig, groups)
    ids = np.unique(patch)
    closed_v, closed_t = layers.capped(skin, patch)
    zone = np.empty(len(skin), object)
    zone[ids] = divide_zones(skin[ids], zones(skin, ids, rig, bones))
    thick = np.zeros(len(skin))
    thick[ids] = [fat_mm[z] / 1000 for z in zone[ids]]
    thick = smooth_on_surface(thick, patch, len(skin), int(structure["smoothing_iterations"]))

    pv = skin[ids]
    origin, shape, centres = layers.grid(pv.min(axis=0), pv.max(axis=0), h)
    inside = gpu_mesh(closed_v, closed_t).inside(centres)
    skin_mesh = gpu_mesh(skin, patch)
    dist, face, uv = skin_mesh.closest(centres)
    included = inside | (dist < h * np.sqrt(3) / 2)
    c = centres[included]
    d_skin = dist[included]
    f, u, v = patch[face[included]], uv[included, 0], uv[included, 1]
    w = np.column_stack([u, v, 1 - u - v])
    t_fat = np.einsum("ij,ij->i", w, thick[f])
    z_of = zone[f[np.arange(len(f)), w.argmax(axis=1)]]

    names = sorted(bones)
    bv, bt, owner, n = [], [], [], 0
    for k, name in enumerate(names):
        vtx, tri = bones[name]
        bv.append(vtx)
        bt.append(outward(vtx, tri) + n)
        owner.append(np.full(len(tri), k))
        n += len(vtx)
    bone_mesh = gpu_mesh(np.concatenate(bv), np.concatenate(bt))
    in_bone = bone_mesh.inside(c)
    d_bone, bface, _ = bone_mesh.closest(c)
    near_bone = np.array(names, object)[np.concatenate(owner)[bface]]

    chest_hull = ConvexHull(np.concatenate([bones[b][0] for b in CHEST_BONES + SPINE_BONES[:12]]))
    trunk_hull = ConvexHull(np.concatenate([bones[b][0] for b in TRUNK_BONES]))
    in_chest = inside_hull(c, chest_hull)
    in_trunk = inside_hull(c, trunk_hull)
    # The belly's organs reach back beside the vertebral bodies (the kidneys), not only in front of them: at the waist the lumbar spine's
    # front is 7 cm ahead of the body's middle, and holding the cavity in front of it left only a sliver (body_v3)
    front_of_spine = c[:, 1] < spine_front(bones, c[:, 2]) + structure["cavity_behind_spine_front_mm"] / 1000
    chest_bone = np.isin(near_bone, CHEST_BONES)

    s = {k: v / 1000 for k, v in structure.items() if k.endswith("_mm")}
    lab = np.full(len(c), MUSCLE, np.int8)
    deep = d_skin > t_fat + s["abdominal_wall_mm"]
    lab[in_trunk & front_of_spine & deep & (d_bone > s["cavity_bone_gap_mm"])] = CAVITY
    # The lungs reach back beside the spine, so the chest's cavity isn't held in front of it as the belly's is (body_v2 was)
    lab[in_chest & (d_bone > s["cavity_bone_gap_mm"])] = CAVITY
    lab[np.isin(z_of, BREAST_ZONES) & ~in_chest & (~chest_bone | (d_bone > s["pectoral_mm"]))] = FAT
    lab[(d_skin < t_fat) & (lab != CAVITY)] = FAT
    lab[(d_skin < structure["skin_band_voxels"] * h) | ~inside[included]] = SKIN
    lab[in_bone] = BONE
    raw = np.full(int(np.prod(shape)), -1, np.int8)
    raw[included] = lab

    clean = raw.copy().reshape(shape)
    moved = {"muscle_to_fat": island_cleanup(clean, MUSCLE, FAT, int(structure["min_island_voxels"])),
             "cavity_to_muscle": island_cleanup(clean, CAVITY, MUSCLE, int(structure["min_island_voxels"]))}
    nodes, tets, tet_voxel, vox = layers.tetrahedra(clean >= 0, origin, h)
    tet_label = clean[tuple(vox.T)][tet_voxel]
    zone_index = {z: i for i, z in enumerate(ZONES)}
    tet_zone = tet_zones(np.array([zone_index[z] for z in z_of], np.int16), included, shape, vox, tet_voxel)
    skin_tet, skin_bary, skin_score = layers.tie(skin[ids], nodes, tets, tet_voxel, vox, origin, h)
    return dict(patch=patch, skin_ids=ids, capped_verts=closed_v, capped_tris=closed_t, zone=zone, thickness=thick,
                origin=origin, shape=shape, h=h, centres=centres, included=included, labels_raw=raw, labels_clean=clean.ravel(), moved=moved,
                nodes=nodes, tets=tets, tet_voxel=tet_voxel, vox=vox, tet_label=tet_label, tet_zone=tet_zone,
                skin_tet=skin_tet, skin_bary=skin_bary, skin_score=skin_score, bone_names=names)

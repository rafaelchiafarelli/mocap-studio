"""A limb built from the inside out: tetrahedra labelled bone, muscle or fat under a piece of skin, and the skin's vertices tied to them.
The skin patch is cut from the MPFB mesh, closed with a fan on each cut, filled on a voxel grid, and each voxel split into six tetrahedra."""
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from .fit import winding_number

BONE, MUSCLE, FAT = 0, 1, 2
LABELS = ("bone", "muscle", "fat")
ZONES = ("front", "back", "inner", "outer")
# Six tetrahedra around the cube's diagonal from corner 0 to corner 7 (Kuhn): neighbouring cubes share faces exactly. Corner bits are x, y, z.
KUHN = np.array([[0, 1, 3, 7], [0, 1, 5, 7], [0, 2, 3, 7], [0, 2, 6, 7], [0, 4, 5, 7], [0, 4, 6, 7]])
CORNERS = np.array([[(c >> 0) & 1, (c >> 1) & 1, (c >> 2) & 1] for c in range(8)])


def crotch_z(skin, midline=0.004):
    """The lowest skin point on the midline. The body is symmetric about x = 0, and only the crotch reaches that low on it."""
    return float(skin[np.abs(skin[:, 0]) < midline, 2].min())


def cut_patch(skin, tris, side, z_lo, z_hi):
    """The triangles of one limb between two heights: those wholly in the slab on that side (+1 is +X, the body's left), largest connected piece."""
    v = skin[tris]
    keep = np.all((v[:, :, 2] > z_lo) & (v[:, :, 2] < z_hi), axis=1) & (v[:, :, 0].mean(axis=1) * side > 0)
    t = tris[keep]
    ids, inv = np.unique(t, return_inverse=True)
    local = inv.reshape(-1, 3)
    parent = np.arange(len(ids))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b, c in local:
        for x, y in ((a, b), (a, c)):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry
    roots = np.array([find(i) for i in range(len(ids))])
    biggest = np.bincount(roots).argmax()
    return t[roots[local[:, 0]] == biggest]


def boundary_loops(tris):
    """Each open edge as the triangle runs it, chained into loops."""
    edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    key = np.sort(edges, axis=1)
    _, inv, count = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    open_edges = edges[count[inv.ravel()] == 1]
    nxt = {a: b for a, b in open_edges}
    loops, seen = [], set()
    for start in nxt:
        if start in seen:
            continue
        loop, v = [], start
        while v not in seen:
            seen.add(v)
            loop.append(v)
            v = nxt[v]
        loops.append(np.array(loop))
    return loops


def capped(skin, tris):
    """The patch closed with a fan to each cut's centre, oriented with the skin, so the winding number tells inside from outside.
    Returns the vertices (the skin's, then one centre per loop) and the triangles."""
    verts, extra = [skin], []
    n = len(skin)
    for loop in boundary_loops(tris):
        centre = n + len(extra)
        extra.append(skin[loop].mean(axis=0))
        # The open edge runs a to b in its triangle, so the cap runs b to a.
        tris = np.concatenate([tris, np.column_stack([np.roll(loop, -1), loop, np.full(len(loop), centre)])])
    return np.concatenate(verts + [np.array(extra).reshape(-1, 3)]), tris


def surface_samples(verts, tris, spacing):
    """Points on every triangle no further apart than about `spacing`, for distances to the surface."""
    out = [verts[np.unique(tris)]]
    edge = np.max([np.linalg.norm(verts[tris[:, i]] - verts[tris[:, (i + 1) % 3]], axis=1) for i in range(3)], axis=0)
    for n in np.unique(np.ceil(edge / spacing).astype(int)):
        if n < 2:
            continue
        t = tris[np.ceil(edge / spacing).astype(int) == n]
        ij = np.array([(i, j) for i in range(n + 1) for j in range(n + 1 - i)]) / n
        w = np.column_stack([1 - ij.sum(axis=1), ij])
        out.append(np.einsum("sk,tkd->tsd", w, verts[t]).reshape(-1, 3))
    return np.concatenate(out)


def axis_line(bone):
    """The bone's long axis: its centre and unit direction, pointing up."""
    c = bone.mean(axis=0)
    d = np.linalg.svd(bone - c, full_matrices=False)[2][0]
    return c, d if d[2] > 0 else -d


def zone_weights(points, centre, direction, side):
    """Each point's share of front, back, inner and outer, from its direction around the bone's axis seen from above.
    The body faces -Y. The shares are squared cosines, so they add to 1 and change smoothly."""
    p = points - centre
    p = p - np.outer(p @ direction, direction)
    d = p[:, :2] / np.maximum(np.linalg.norm(p[:, :2], axis=1, keepdims=True), 1e-9)
    x, y = d[:, 0] * side, d[:, 1]
    return np.column_stack([np.maximum(-y, 0) ** 2, np.maximum(y, 0) ** 2, np.maximum(-x, 0) ** 2, np.maximum(x, 0) ** 2])


def grid(lo, hi, h):
    """Voxel centres covering a box, with the grid's origin (the first node) and shape in voxels."""
    origin = np.asarray(lo, float) - h
    shape = np.ceil((np.asarray(hi, float) + h - origin) / h).astype(int)
    idx = np.indices(shape).reshape(3, -1).T
    return origin, shape, origin + (idx + 0.5) * h


def largest_component(mask):
    """The largest 6-connected piece of a voxel mask, and what was dropped."""
    lab, n = ndimage.label(mask)
    if n < 2:
        return mask, np.zeros_like(mask)
    keep = lab == np.bincount(lab.ravel())[1:].argmax() + 1
    return keep, mask & ~keep


def tetrahedra(included, origin, h):
    """Six tetrahedra per included voxel, on shared grid nodes. Returns nodes, tetrahedra (positive volume) and each one's voxel."""
    shape = np.array(included.shape)
    vox = np.argwhere(included)
    corners = vox[:, None, :] + CORNERS[None]
    flat = np.ravel_multi_index(corners.reshape(-1, 3).T, shape + 1)
    used, inv = np.unique(flat, return_inverse=True)
    nodes = origin + np.column_stack(np.unravel_index(used, shape + 1)) * h
    local = inv.reshape(-1, 8)
    tets = local[:, KUHN].reshape(-1, 4)
    v = nodes[tets]
    neg = np.einsum("ij,ij->i", np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), v[:, 3] - v[:, 0]) < 0
    tets[neg] = tets[neg][:, [0, 2, 1, 3]]
    return nodes, tets, np.repeat(np.arange(len(vox)), 6), vox


def barycentric(points, corners):
    """Barycentric weights of each point in its tetrahedron (corners: n x 4 x 3)."""
    T = (corners[:, 1:] - corners[:, :1]).transpose(0, 2, 1)
    w = np.linalg.solve(T, (points - corners[:, 0])[..., None])[..., 0]
    return np.column_stack([1 - w.sum(axis=1), w])


def tie(points, nodes, tets, tet_voxel, vox, origin, h):
    """For each point, the tetrahedron that holds it and its barycentric weights. Every point must lie in an included voxel."""
    where = {tuple(v): i for i, v in enumerate(vox)}
    cell = np.floor((points - origin) / h).astype(int)
    vi = np.array([where.get(tuple(c), -1) for c in cell])
    if (vi < 0).any():
        raise ValueError(f"{int((vi < 0).sum())} points are outside every voxel")
    candidates = vi[:, None] * 6 + np.arange(6)[None]
    best_t = np.empty(len(points), int)
    best_w = np.empty((len(points), 4))
    score = np.full(len(points), -np.inf)
    for k in range(6):
        t = candidates[:, k]
        w = barycentric(points, nodes[tets[t]])
        m = w.min(axis=1) > score
        best_t[m], best_w[m], score[m] = t[m], w[m], w.min(axis=1)[m]
    return best_t, best_w, score


def boundary_faces(tets):
    """The faces used by only one tetrahedron of the set: its surface, outward."""
    faces = np.concatenate([tets[:, [0, 2, 1]], tets[:, [0, 1, 3]], tets[:, [0, 3, 2]], tets[:, [1, 2, 3]]])
    key = np.sort(faces, axis=1)
    _, inv, count = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    return faces[count[inv.ravel()] == 1]


def build(skin, tris, bone, bone_tris, side, z_lo, z_hi, h, fat_mm, spacing=None):
    """Everything for one limb. fat_mm is the declared fat thickness per zone, in millimetres, as {zone: value}.
    Returns a dict of arrays, with every intermediate kept for review."""
    spacing = spacing or h / 3
    patch = cut_patch(skin, tris, side, z_lo, z_hi)
    closed_v, closed_t = capped(skin, patch)
    samples = surface_samples(skin, patch, spacing)
    tree = cKDTree(samples)
    pv = skin[np.unique(patch)]
    origin, shape, centres = grid(pv.min(axis=0), pv.max(axis=0), h)
    # A skin vertex near a cut can sit in a voxel whose centre is just past it.
    in_slab = (centres[:, 2] > z_lo - h / 2) & (centres[:, 2] < z_hi + h / 2)
    dist = np.full(len(centres), np.inf)
    dist[in_slab] = tree.query(centres[in_slab])[0]
    near = dist < h * np.sqrt(3) / 2
    inside = np.zeros(len(centres), bool)
    inside[in_slab] = winding_number(centres[in_slab], closed_v, closed_t) > 0.5
    included = (inside | near) & in_slab

    lo, hi = bone.min(axis=0) - h, bone.max(axis=0) + h
    test = included & np.all((centres > lo) & (centres < hi), axis=1)
    in_bone = np.zeros(len(centres), bool)
    in_bone[test] = winding_number(centres[test], bone, bone_tris) > 0.5

    centre, direction = axis_line(bone)
    w = zone_weights(centres, centre, direction, side)
    thickness = w @ (np.array([fat_mm[z] for z in ZONES]) / 1000)
    raw = np.full(len(centres), -1, np.int8)
    raw[included] = MUSCLE
    raw[included & ((dist < thickness) | ~inside)] = FAT
    raw[included & in_bone] = BONE

    clean = raw.copy().reshape(shape)
    bone_keep, bone_drop = largest_component(clean == BONE)
    clean[bone_drop] = MUSCLE
    muscle_keep, muscle_drop = largest_component(clean == MUSCLE)
    clean[muscle_drop] = FAT

    nodes, tets, tet_voxel, vox = tetrahedra(clean >= 0, origin, h)
    tet_label = clean[tuple(vox.T)][tet_voxel]
    skin_ids = np.unique(patch)
    skin_tet, skin_bary, skin_score = tie(skin[skin_ids], nodes, tets, tet_voxel, vox, origin, h)
    return dict(patch=patch, capped_verts=closed_v, capped_tris=closed_t, origin=origin, shape=shape, h=h,
                centres=centres, inside=inside, included=included, in_bone=in_bone, dist=dist, thickness=thickness,
                labels_raw=raw, labels_clean=clean.ravel(), dropped_bone=bone_drop.ravel(), dropped_muscle=muscle_drop.ravel(),
                nodes=nodes, tets=tets, tet_label=tet_label, skin_ids=skin_ids, skin_tet=skin_tet, skin_bary=skin_bary,
                skin_score=skin_score, samples=samples, axis_centre=centre, axis_direction=direction)


def measure(result, skin, bone, side, fat_mm, margin=0.01):
    """What task 2 reports: the bone inside the skin and how close it comes, tetrahedra per layer, and the fat's actual thickness per zone."""
    r = result
    # The patch keeps whole triangles only, so it ends short of the cuts. Count between its two rings, where skin surrounds the bone.
    rings = [skin[loop, 2] for loop in boundary_loops(r["patch"])]
    z_lo, z_hi = float(min(rings, key=np.mean).max()), float(max(rings, key=np.mean).min())
    tree = cKDTree(r["samples"])
    in_slab = (bone[:, 2] > z_lo) & (bone[:, 2] < z_hi)
    b = bone[in_slab]
    wn = winding_number(b, r["capped_verts"], r["capped_tris"])
    gap = tree.query(b)[0]
    counts = {LABELS[k]: int((r["tet_label"] == k).sum()) for k in range(3)}

    muscle = r["centres"][r["labels_clean"] == MUSCLE]
    s = skin[r["skin_ids"]]
    s = s[(s[:, 2] > z_lo + margin) & (s[:, 2] < z_hi - margin)]
    actual = cKDTree(muscle).query(s)[0] - r["h"] / 2
    zone = zone_weights(s, r["axis_centre"], r["axis_direction"], side).argmax(axis=1)
    fat = {}
    for i, z in enumerate(ZONES):
        a = actual[zone == i]
        fat[z] = {"declared_mm": fat_mm[z], "median_mm": round(float(np.median(a)) * 1000, 1) if len(a) else None,
                  "p10_mm": round(float(np.percentile(a, 10)) * 1000, 1) if len(a) else None,
                  "p90_mm": round(float(np.percentile(a, 90)) * 1000, 1) if len(a) else None, "skin_points": int(len(a))}
    return {"measured_between_z_m": [round(z_lo, 4), round(z_hi, 4)], "bone_points_in_slab": int(len(b)), "bone_points_outside_skin": int((wn <= 0.5).sum()),
            "bone_min_distance_to_skin_mm": round(float(gap.min()) * 1000, 1), "bone_median_distance_to_skin_mm": round(float(np.median(gap)) * 1000, 1),
            "tetrahedra": counts, "nodes": int(len(r["nodes"])), "voxel_mm": r["h"] * 1000,
            "dropped_voxels": {"bone_to_muscle": int(r["dropped_bone"].sum()), "muscle_to_fat": int(r["dropped_muscle"].sum())},
            "skin_points_tied": int(len(r["skin_ids"])), "skin_tie_worst_weight": round(float(r["skin_score"].min()), 6),
            "fat": fat}


def write_ply(path, verts, faces=None):
    """A binary PLY that Blender imports: vertices, and triangles if given."""
    verts = np.asarray(verts, "<f4")
    header = ["ply", "format binary_little_endian 1.0", f"element vertex {len(verts)}", "property float x", "property float y", "property float z"]
    if faces is not None:
        header += [f"element face {len(faces)}", "property list uchar int vertex_indices"]
    with open(path, "wb") as f:
        f.write(("\n".join(header + ["end_header"]) + "\n").encode())
        f.write(verts.tobytes())
        if faces is not None:
            rec = np.zeros(len(faces), dtype=[("n", "u1"), ("v", "<i4", 3)])
            rec["n"], rec["v"] = 3, faces
            f.write(rec.tobytes())

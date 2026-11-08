"""Places source bones inside one individual's body. Every bone stays rigid apart from a scale, so its shape is the measured one."""
import numpy as np


def rotation_between(a, b):
    """The smallest rotation taking direction a to direction b."""
    a = np.asarray(a, float) / np.linalg.norm(a)
    b = np.asarray(b, float) / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(a @ b)
    if c < -0.999999:
        axis = np.cross(a, [1, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1, 0])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def frame_rotation(a1, a2, b1, b2):
    """Rotation taking a1 to b1 exactly, and a2 as near to b2 as a1 allows."""
    def frame(x, y):
        x = np.asarray(x, float) / np.linalg.norm(x)
        z = np.cross(x, y)
        z /= np.linalg.norm(z)
        return np.column_stack([x, np.cross(z, x), z])
    return frame(b1, b2) @ frame(a1, a2).T


def segment_fit(verts, a, b, target_a, target_b, radial_power=0.7, rotation=None):
    """Maps a bone so its joints a and b land on target_a and target_b. Along the axis it scales by the length ratio, across it by that ratio to radial_power (limbs don't get thicker in proportion to length)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    ta, tb = np.asarray(target_a, float), np.asarray(target_b, float)
    src = b - a
    s = np.linalg.norm(tb - ta) / np.linalg.norm(src)
    axis = src / np.linalg.norm(src)
    p = np.asarray(verts, float) - a
    along = p @ axis
    radial = p - np.outer(along, axis)
    scaled = np.outer(along * s, axis) + radial * s ** radial_power
    R = rotation if rotation is not None else rotation_between(src, tb - ta)
    return scaled @ R.T + ta


def similarity(verts, a, b, target_a, target_b):
    return segment_fit(verts, a, b, target_a, target_b, radial_power=1.0)


def box_map(verts, box_min, box_max, target_min, target_max):
    """Anisotropic map of a bounding box onto another."""
    box_min, box_max, target_min, target_max = map(lambda x: np.asarray(x, float), (box_min, box_max, target_min, target_max))
    return (np.asarray(verts, float) - box_min) * (target_max - target_min) / (box_max - box_min) + target_min


def outward(verts, tris):
    """The triangles wound so the mesh's volume is positive, so its normals face out and its winding number is +1 inside."""
    t = np.asarray(verts, float)[tris]
    volume = np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum()
    return tris if volume >= 0 else tris[:, [0, 2, 1]]


def triangles(starts, sizes, loops):
    """Polygons to triangles, as fans."""
    out = []
    for s, n in zip(starts, sizes):
        for i in range(1, n - 1):
            out.append((loops[s], loops[s + i], loops[s + i + 1]))
    return np.array(out, dtype=np.int64)


def winding_number(points, verts, tris, chunk=512):
    """Generalized winding number of each point against a triangle mesh: about 1 inside, about 0 outside, also with small holes such as eyes and mouth."""
    points = np.asarray(points, float)
    A, B, C = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
    out = np.zeros(len(points))
    for i in range(0, len(points), chunk):
        p = points[i:i + chunk, None, :]
        a, b, c = A[None] - p, B[None] - p, C[None] - p
        la, lb, lc = np.linalg.norm(a, axis=2), np.linalg.norm(b, axis=2), np.linalg.norm(c, axis=2)
        num = np.einsum("ijk,ijk->ij", a, np.cross(b, c))
        den = la * lb * lc + np.einsum("ijk,ijk->ij", a, b) * lc + np.einsum("ijk,ijk->ij", b, c) * la + np.einsum("ijk,ijk->ij", c, a) * lb
        out[i:i + chunk] = np.arctan2(num, den).sum(axis=1) / (2 * np.pi)
    return np.abs(out)


def body_profile(skin, z, half_width=0.03, band=0.012, x0=0.0):
    """Front and back of the skin near one height and sideways position: (y front, y back). The body faces -Y."""
    m = (np.abs(skin[:, 2] - z) < band) & (np.abs(skin[:, 0] - x0) < half_width)
    if not m.any():
        return None
    return float(skin[m, 1].min()), float(skin[m, 1].max())


def body_half_width(skin, z, band=0.012, gap=0.015):
    """Half the trunk's width at one height. Walks out from the midline and stops at the first empty gap, so an arm beyond the armpit doesn't count."""
    x = np.sort(np.abs(skin[np.abs(skin[:, 2] - z) < band, 0]))
    if len(x) == 0:
        return None
    jumps = np.flatnonzero(np.diff(x) > gap)
    return float(x[jumps[0]] if len(jumps) else x[-1])


def ring_centre(skin, head, tail, radius):
    """Centre of the skin around a thin segment, such as a finger: the rig's bones don't always run through the middle."""
    axis = tail - head
    length = np.linalg.norm(axis)
    axis = axis / length
    p = skin - head
    t = p @ axis
    r = np.linalg.norm(p - np.outer(t, axis), axis=1)
    m = (t > 0.15 * length) & (t < 0.85 * length) & (r < radius)
    return skin[m].mean(axis=0) if m.sum() >= 8 else None


class SkinDepth:
    """Signed depth of points under the skin on the CPU, fast enough to try thousands of placements: positive inside, negative outside.
    The skin is sampled about every spacing metres over its triangles; a point's depth is its distance to the nearest sample, signed by
    that sample's triangle normal, turned outward from the mesh's signed volume. Off by up to about half the spacing."""

    def __init__(self, verts, tris, spacing=0.0015):
        from scipy.spatial import cKDTree
        verts = np.asarray(verts, float)
        a, b, c = verts[tris[:, 0]], verts[tris[:, 1]], verts[tris[:, 2]]
        normal = np.cross(b - a, c - a)
        flat = np.linalg.norm(normal, axis=1) < 1e-12  # no normal to sign by
        a, b, c, normal = a[~flat], b[~flat], c[~flat], normal[~flat]
        if np.einsum("ij,ij->i", a, normal).sum() < 0:  # six times the signed volume: negative means the normals face in
            normal = -normal
        normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
        edge = np.max([np.linalg.norm(b - a, axis=1), np.linalg.norm(c - b, axis=1), np.linalg.norm(a - c, axis=1)], axis=0)
        steps = np.maximum(1, np.ceil(edge / spacing)).astype(int)
        pts, nrm = [], []
        for n in np.unique(steps):
            i, j = np.mgrid[0:n + 1, 0:n + 1]
            keep = i + j <= n
            u, v = i[keep] / n, j[keep] / n
            m = steps == n
            pts.append((a[m, None] * (1 - u - v)[None, :, None] + b[m, None] * u[None, :, None] + c[m, None] * v[None, :, None]).reshape(-1, 3))
            nrm.append(np.repeat(normal[m], len(u), axis=0))
        self.points, self.normals = np.vstack(pts), np.vstack(nrm)
        self.tree = cKDTree(self.points)
        self.verts, self.tris = verts, tris

    def inside(self, points):
        """The exact test, by winding number: slow, for checking the fast sign once."""
        return winding_number(points, self.verts, self.tris) > 0.5

    def __call__(self, points):
        points = np.asarray(points, float)
        dist, k = self.tree.query(points)
        outward = np.einsum("ij,ij->i", points - self.points[k], self.normals[k]) > 0
        return np.where(outward, -dist, dist)


def largest_scale(short, least=0.4, steps=14):
    """The largest scale in [least, 1] for which short(scale) is at most zero, by bisection; 1 if it already is, least if none is."""
    if short(1.0) <= 0:
        return 1.0
    lo, hi = least, 1.0
    if short(lo) > 0:
        return least
    for _ in range(steps):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if short(mid) <= 0 else (lo, mid)
    return lo


def slim_to_skin(meshes, a, b, skin, depth_of, need, start=0.5, bin_size=0.01, reach=0.12, least=0.4):
    """Narrows bones, height by height along the segment a to b, just where the skin around them leaves less than need metres over them.
    The bones go together through one map, so what lies apart stays apart. Each height scales across the segment about the middle of the
    skin's own section, and heights that fit don't change at all. The scale per height is the largest that fits, widened by a window and
    averaged so it changes smoothly and is never larger than one that fits. Heights before start, a fraction of the segment from a, are
    left alone: the fast depth's sign fails in the groin's crease, which read as the femur's head needing to shrink to 40%.
    Returns (the meshes' new vertices, the smallest scale)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    axis = (b - a) / np.linalg.norm(b - a)
    sizes = [len(m) for m in meshes]
    v = np.vstack(meshes).astype(float)

    def split(p):
        p = p - a
        along = p @ axis
        return along, p - np.outer(along, axis)

    t, across = split(v)
    skin_t, skin_across = split(np.asarray(skin, float))
    heights = np.arange(t.min(), t.max() + bin_size, bin_size)
    scale, centre = np.ones(len(heights)), np.zeros((len(heights), 3))
    for i, h in enumerate(heights):
        around = (np.abs(skin_t - h) < bin_size) & (np.linalg.norm(skin_across, axis=1) < reach)  # this leg's skin only
        here = np.abs(t - h) <= bin_size / 2
        if h < start * np.linalg.norm(b - a) or not around.any() or not here.any():
            continue
        centre[i] = (skin_across[around].min(axis=0) + skin_across[around].max(axis=0)) / 2
        scale[i] = largest_scale(lambda s: float((need - depth_of(a + np.outer(t[here], axis) + centre[i] + (across[here] - centre[i]) * s)).max()), least)
    k = max(1, round(0.02 / bin_size))
    window = lambda x, f: np.array([f(x[max(0, i - k):i + k + 1], axis=0) for i in range(len(x))])
    scale = window(window(scale, np.min), np.mean)  # each averaged value is the minimum of a window holding this height, so none grows
    centre = window(centre, np.mean)
    s = np.interp(t, heights, scale)[:, None]
    c = np.column_stack([np.interp(t, heights, centre[:, j]) for j in range(3)])
    placed = a + np.outer(t, axis) + c + (across - c) * s
    return np.split(placed, np.cumsum(sizes)[:-1]), float(scale.min())


def axis_rotation(axis, angle):
    """Rotation by angle (radians) about a unit axis."""
    x, y, z = np.asarray(axis, float) / np.linalg.norm(axis)
    k = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k


DEEP = 0.03  # m: a bone point this far from any skin, having started inside, is still inside


def settle(verts, pivot, depth_of, need, moves, avoid=None, clearance=0.003, keep=(), exact=False, steps=9, sample=400, seed=0):
    """The smallest rigid move of a bone that leaves at least need metres of tissue over all of it, or as near as it gets.
    moves lists what the bone may do, each ("turn", axis, most degrees) about pivot or ("shift", direction, most metres). Every
    combination on a grid of steps values per move is tried, then a finer grid around the best; among moves that leave the same
    shortfall (to half a millimetre) the smallest wins, each move counted as a fraction of its most. avoid is a cKDTree of neighbouring
    bones' points: no point may come closer to them than clearance, or than it already was if that's less. keep lists (point,
    tolerance) pairs, such as a joint's end: the moved point may stray no further than tolerance from where it was. exact signs the
    points nearer than DEEP to the skin by the exact test on every try, where creases make the fast one fail (the pelvis): slower.
    Returns (move as a function of points, worst shortfall before, after in metres, the chosen amounts)."""
    v = np.asarray(verts, float)
    v = v[np.random.default_rng(seed).choice(len(v), min(sample, len(v)), replace=False)]
    # The fast depth's sign is wrong in deep creases (the groin: 1 to 3% of the pelvis's points, up to 90 mm deep, and more of them
    # as the pelvis moves). So a point that starts inside, by the exact test, and stays more than DEEP from any skin counts as inside:
    # it can't have left the body without first passing near the skin. Near points where the two tests disagree are left out.
    deep_inside = np.zeros(len(v), bool)
    if hasattr(depth_of, "inside"):
        fast, inside = depth_of(v), depth_of.inside(v)
        trusted = ((fast > 0) == inside) | (inside & (np.abs(fast) > DEEP))
        v, deep_inside = v[trusted], inside[trusted]
    floor = None if avoid is None else np.minimum(avoid.query(v)[0], clearance)
    most = np.array([m[2] for m in moves], float)

    def apply(amounts, p):
        p = np.asarray(p, float)
        for (kind, d, _), a in zip(moves, amounts):
            if kind == "turn":
                p = (p - pivot) @ axis_rotation(d, np.radians(a)).T + pivot
            else:
                p = p + np.asarray(d, float) / np.linalg.norm(d) * a
        return p

    def shortfall(amounts):
        p = apply(amounts, v)
        d = depth_of(p)
        d = np.where(deep_inside & (np.abs(d) > DEEP), np.abs(d), d)
        if exact:
            near = np.abs(d) <= DEEP
            d[near] = np.where(depth_of.inside(p[near]), np.abs(d[near]), -np.abs(d[near]))
        short = need - d
        if floor is not None:
            short = np.maximum(short, floor - avoid.query(p)[0])
        worst = float(short.max(initial=0.0))  # every point may be too deep to matter
        for point, tol in keep:
            worst = max(worst, float(np.linalg.norm(apply(amounts, np.asarray(point, float)[None])[0] - point)) - tol)
        return max(worst, 0.0)

    def search(centre, half):
        axes = [np.linspace(-h, h, steps) for h in half]
        best = None
        for a in np.stack(np.meshgrid(*axes, indexing="ij"), -1).reshape(-1, len(moves)) + centre:
            if (np.abs(a) > most + 1e-9).any():
                continue
            key = (round(shortfall(a) / 0.0005), float(np.linalg.norm(a / most)))
            if best is None or key < best[0]:
                best = (key, a)
        return best[1]

    coarse = search(np.zeros(len(moves)), most)
    fine = search(coarse, most / (steps - 1))
    return (lambda p: apply(fine, p)), shortfall(np.zeros(len(moves))), shortfall(fine), fine

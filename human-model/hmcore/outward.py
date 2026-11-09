"""Muscle and fat grown outward from the bones, and the skin as their result (initiative body-type-selection, epic volumes-outward). Numpy and scipy only; the bones reach it as a mask from whoever rasterized them.
The order of a body in this path: bones, muscle around them by zone, fat around that up to the body-fat percentage, and the 13,380 skin points moved onto what results."""
import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

DENSITY = {"bone": 1500.0, "muscle": 1060.0, "fat": 900.0, "skin": 1100.0, "cavity": 900.0}  # kg/m3, as in tools/body_report.py
REAL_SKIN_M = 0.0015  # as tools/body_report.py's REAL_SKIN_MM


def core_mask(centres, hull_points, in_bone):
    """Where the body's inside starts: the bones, and the trunk's cavity as the convex hull of its bones. Muscle grows from here."""
    hull = ConvexHull(hull_points)
    inside = np.ones(len(centres), bool)
    for s in range(0, len(centres), 200_000):
        inside[s:s + 200_000] = np.all(centres[s:s + 200_000] @ hull.equations[:, :3].T + hull.equations[:, 3] <= 1e-9, axis=1)
    return in_bone | inside


def grow(mask, thickness_m, keep, h):
    """The cells within thickness_m (one value per cell, or one for all) of mask, inside keep. Distances are the exact Euclidean transform on the grid."""
    distance = ndimage.distance_transform_edt(~mask) * h
    return (distance <= thickness_m) & keep


def muscle_layer(core, muscle_m_per_cell, scale, keep, h):
    """The muscle: everything within its zone's thickness of the core, scaled by the biotype's muscle. Cells of the core itself aren't muscle."""
    return grow(core, muscle_m_per_cell * scale, keep, h) & ~core


def masses_kg(in_bone, core, muscle, fat, keep, h, skin_area_m2):
    """kg of each tissue among the kept cells, with real skin as its area times REAL_SKIN_M. The cavity is the core that isn't bone."""
    cell = h ** 3
    kg = lambda m, name: float(m.sum()) * cell * DENSITY[name]
    return {"bone": kg(in_bone & keep, "bone"), "cavity": kg(core & ~in_bone & keep, "cavity"), "muscle": kg(muscle & keep, "muscle"), "fat": kg(fat & keep, "fat"),
            "skin": skin_area_m2 * REAL_SKIN_M * DENSITY["skin"]}


def fat_percent(masses):
    return 100.0 * masses["fat"] / sum(masses.values())


def fat_to_percent(in_bone, core, muscle, keep, fat_m_per_cell, target_percent, h, skin_area_m2, tolerance=0.5, lo=0.0, hi=6.0):
    """The fat, grown outward from the muscle by one scale on every zone's thickness, found by bisection until the body's fat reaches target_percent within tolerance (percentage points).
    Returns {"fat": mask, "scale", "percent", "reached"}. The percentage counts the simulated body: head, hands and feet aren't in the layers."""
    inner = core | muscle
    distance = ndimage.distance_transform_edt(~inner) * h

    def at(scale):
        fat = (distance <= fat_m_per_cell * scale) & keep & ~inner
        return fat, fat_percent(masses_kg(in_bone, core, muscle, fat, keep, h, skin_area_m2))

    best = None
    for _ in range(40):
        mid = (lo + hi) / 2
        fat, percent = at(mid)
        if best is None or abs(percent - target_percent) < abs(best["percent"] - target_percent):
            best = {"fat": fat, "scale": mid, "percent": percent}
        if abs(percent - target_percent) <= tolerance / 4:
            break
        lo, hi = (mid, hi) if percent < target_percent else (lo, mid)
    best["reached"] = abs(best["percent"] - target_percent) <= tolerance
    return best


def per_cell(points, values, centres):
    """A value per grid cell from the nearest of these points, as the fat's thickness per skin vertex becomes a thickness per cell."""
    from scipy.spatial import cKDTree
    return values[cKDTree(points).query(centres, workers=-1)[1]]


def signed_distance(solid, h):
    """Metres to the solid's surface, on the cell grid: positive outside, negative inside."""
    return (ndimage.distance_transform_edt(~solid) - ndimage.distance_transform_edt(solid)) * h


def sample(field, points, origin, h):
    """A cell-centred field at these points, by linear interpolation."""
    return ndimage.map_coordinates(field, ((np.asarray(points) - origin) / h - 0.5).T, order=1, mode="nearest")


def vertex_normals(points, tris):
    n = np.cross(points[tris[:, 1]] - points[tris[:, 0]], points[tris[:, 2]] - points[tris[:, 0]])
    out = np.zeros(points.shape)
    for k in range(3):
        np.add.at(out, tris[:, k], n)
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)


def project(points, normals, sdf, origin, h, most, iterations=8):
    """Moves points along their normals onto the surface where sdf is zero, by at most most metres. Their topology stays the same."""
    p = np.asarray(points, float).copy()
    start = p.copy()
    for _ in range(iterations):
        d = sample(sdf, p, origin, h)
        p -= normals * np.clip(d, -3 * h, 3 * h)[:, None]
        along = np.einsum("ij,ij->i", p - start, normals)
        p = start + normals * np.clip(along, -most, most)[:, None]
    return p


def folded(before, after, tris):
    """How many triangles turned over: their normals point the other way after the move."""
    nb = np.cross(before[tris[:, 1]] - before[tris[:, 0]], before[tris[:, 2]] - before[tris[:, 0]])
    na = np.cross(after[tris[:, 1]] - after[tris[:, 0]], after[tris[:, 2]] - after[tris[:, 0]])
    return int((np.einsum("ij,ij->i", nb, na) < 0).sum())


def ring_fade(points, rings, reach):
    """1 far from the cut rings, 0 at them, fading smoothly over reach metres: multiplied into the skin's move, so it blends into the head's, hands' and feet's without a step. rings: arrays of points."""
    d = np.full(len(points), np.inf)
    for ring in rings:
        from scipy.spatial import cKDTree
        d = np.minimum(d, cKDTree(ring).query(points)[0])
    t = np.clip(d / reach, 0, 1)
    return t * t * (3 - 2 * t)


def ring_steps(before, after, rings):
    """The most each cut ring's points moved, mm: the size of the step left at each join."""
    return [round(float(np.linalg.norm(after[r] - before[r], axis=1).max()) * 1000, 2) for r in rings]

"""The body's inside and the skin over it (initiative body-type-selection): the bones and the trunk's cavity, muscles from hmcore.muscle_bodies, and the first shape's skin moved out only where these need it. What lies between them and the skin is fat. Numpy and scipy only; the bones reach it as a mask."""
import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

DENSITY = {"bone": 1500.0, "muscle": 1060.0, "fat": 900.0, "skin": 1100.0, "cavity": 900.0}  # kg/m3, as in tools/body_report.py
REAL_SKIN_M = 0.0015  # as tools/body_report.py's REAL_SKIN_MM


def inside_hull(points, hull_points):
    hull = ConvexHull(hull_points)
    inside = np.ones(len(points), bool)
    for s in range(0, len(points), 200_000):
        inside[s:s + 200_000] = np.all(points[s:s + 200_000] @ hull.equations[:, :3].T + hull.equations[:, 3] <= 1e-9, axis=1)
    return inside


def core_mask(centres, chest_points, trunk_points, front_of_spine, in_bone):
    """Where the body's inside starts: the bones, the chest's hull, and the trunk's hull only in front of the spine: a hull of the whole trunk bridged the lumbar curve and pushed the lower back out 4 cm (bug human-model/32)."""
    return in_bone | inside_hull(centres, chest_points) | (inside_hull(centres, trunk_points) & front_of_spine)


def grow(mask, thickness_m, keep, h):
    """The cells within thickness_m of mask, inside keep. Distances are the exact Euclidean transform on the grid."""
    return (ndimage.distance_transform_edt(~mask) * h <= thickness_m) & keep


def masses_kg(in_bone, core, muscle, fat, keep, h, skin_area_m2):
    """kg of each tissue among the kept cells, with real skin as its area times REAL_SKIN_M. The cavity is the core that isn't bone."""
    cell = h ** 3
    kg = lambda m, name: float(m.sum()) * cell * DENSITY[name]
    return {"bone": kg(in_bone & keep, "bone"), "cavity": kg(core & ~in_bone & keep, "cavity"), "muscle": kg(muscle & keep, "muscle"), "fat": kg(fat & keep, "fat"),
            "skin": skin_area_m2 * REAL_SKIN_M * DENSITY["skin"]}


def fat_percent(masses):
    return 100.0 * masses["fat"] / sum(masses.values())


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


def push_needed(points, inner_sdf, origin, h):
    """How far each point must go out so that what lies inside (inner_sdf, negative inside it) stays under it. Zero where it already does."""
    return np.maximum(-sample(inner_sdf, points, origin, h), 0.0)


def push_needed_on_surface(points, tris, inner_sdf, origin, h):
    """The same over the whole skin, not only at its vertices: a bone's edge can stand out between them. Each triangle is asked at its middle and its edges' middles, and every vertex takes the most its triangles ask for."""
    t = points[tris]
    samples = np.concatenate([t.mean(axis=1), t[:, [0, 1]].mean(axis=1), t[:, [1, 2]].mean(axis=1), t[:, [2, 0]].mean(axis=1), t[:, 0], t[:, 1], t[:, 2]])
    need = np.maximum(-sample(inner_sdf, samples, origin, h), 0.0).reshape(7, -1).max(axis=0)
    out = np.zeros(len(points))
    for k in range(3):
        np.maximum.at(out, tris[:, k], need)
    return out


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

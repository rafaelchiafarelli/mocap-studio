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

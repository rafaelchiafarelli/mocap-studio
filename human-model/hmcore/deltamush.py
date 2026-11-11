"""Delta Mush (Mancewicz et al. 2014) on a skin mesh: what a smoothed copy of the skin loses is kept in local frames at rest and added back on the smoothed posed skin, which removes the collapse of a skinned joint.
Plain numpy, so it runs in Blender's Python and in the tests."""
from __future__ import annotations

import numpy as np


def neighbours(tris, n):
    """Each vertex's neighbours as a CSR-like pair: start offsets and indices."""
    a = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    a = np.unique(np.concatenate([a, a[:, ::-1]]), axis=0)
    starts = np.searchsorted(a[:, 0], np.arange(n + 1))
    return starts, a[:, 1]


def smooth(verts, adjacency, iterations=25, step=0.5):
    """Moves each vertex towards the mean of its neighbours. Vertices with no neighbours stay."""
    starts, targets = adjacency
    counts = np.diff(starts)
    index = np.repeat(np.arange(len(verts)), counts)
    v = verts.copy()
    for _ in range(iterations):
        mean = np.zeros_like(v)
        np.add.at(mean, index, v[targets])
        lonely = counts == 0
        mean[~lonely] /= counts[~lonely][:, None]
        mean[lonely] = v[lonely]
        v += step * (mean - v)
    return v


def vertex_normals(verts, tris):
    faces = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
    normals = np.zeros_like(verts)
    for i in range(3):
        np.add.at(normals, tris[:, i], faces)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    return normals / np.maximum(length, 1e-12)


def frames(verts, tris, adjacency):
    """A right-handed frame per vertex, 3 x 3 with columns tangent, bitangent, normal; the tangent points at the vertex's first neighbour."""
    starts, targets = adjacency
    n = vertex_normals(verts, tris)
    first = np.where(np.diff(starts) > 0, targets[np.minimum(starts[:-1], len(targets) - 1)], np.arange(len(verts)))
    t = verts[first] - verts
    t -= (t * n).sum(1, keepdims=True) * n
    bad = np.linalg.norm(t, axis=1) < 1e-12
    t[bad] = np.cross(n[bad], [1.0, 0.0, 0.0])
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-12)
    return np.stack([t, np.cross(n, t), n], axis=2)


def correction(rest, posed, tris, iterations=25, step=0.5):
    """What must be added to the posed skin, and the same in the rest pose's axes, ready for a shape key that goes before the armature."""
    adjacency = neighbours(tris, len(rest))
    rest_smooth, posed_smooth = smooth(rest, adjacency, iterations, step), smooth(posed, adjacency, iterations, step)
    local = (np.transpose(frames(rest_smooth, tris, adjacency), (0, 2, 1)) @ (rest - rest_smooth)[..., None])
    fixed = posed_smooth + (frames(posed_smooth, tris, adjacency) @ local)[..., 0]
    in_pose = fixed - posed
    rotation = frames(posed, tris, adjacency) @ np.transpose(frames(rest, tris, adjacency), (0, 2, 1))
    in_rest = (np.transpose(rotation, (0, 2, 1)) @ in_pose[..., None])[..., 0]
    return in_pose, in_rest


def falloff(rest, centers, radius):
    """1 within radius of any centre, easing to 0 at twice that."""
    distance = np.min([np.linalg.norm(rest - c, axis=1) for c in centers], axis=0)
    u = np.clip((2.0 * radius - distance) / radius, 0.0, 1.0)
    return u * u * (3.0 - 2.0 * u)

"""Bones no allowed source has as a mesh: tubes along paths, and shells. Built from declared measures and marked "parametric"."""
import numpy as np


def tube(path, radius, sides=10):
    """A closed tube along a polyline. radius is one value or one per point."""
    path = np.asarray(path, float)
    radii = np.broadcast_to(radius, (len(path),))
    verts, faces = [], []
    for i, p in enumerate(path):
        t = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
        t /= np.linalg.norm(t)
        ref = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
        u = np.cross(t, ref)
        u /= np.linalg.norm(u)
        v = np.cross(t, u)
        for k in range(sides):
            a = 2 * np.pi * k / sides
            verts.append(p + radii[i] * (np.cos(a) * u + np.sin(a) * v))
    for i in range(len(path) - 1):
        for k in range(sides):
            a, b = i * sides + k, i * sides + (k + 1) % sides
            c, d = a + sides, b + sides
            faces += [(a, b, d), (a, d, c)]
    n = len(verts)
    verts += [path[0], path[-1]]
    for k in range(sides):
        faces.append((n, (k + 1) % sides, k))
        faces.append((n + 1, (len(path) - 1) * sides + k, (len(path) - 1) * sides + (k + 1) % sides))
    return np.array(verts, float), np.array(faces, np.int32)


def hyoid(centre, width=0.042, depth=0.030):
    """A horseshoe opening backwards: the body in front, greater horns to the sides and back."""
    t = np.linspace(-1, 1, 25)
    x = width / 2 * np.sin(t * 1.6) / np.sin(1.6)
    y = depth * (t ** 2)
    path = np.column_stack([x, y, 0.004 * t ** 2]) + np.asarray(centre, float)
    return tube(path, 0.0028 + 0.0018 * (1 - t ** 2))


def thyroid_shield(centre, width=0.040, height=0.032, depth=0.028, n=14):
    """The larynx as one open shell: two plates meeting at the front. Moves as a volume, no internal parts."""
    centre = np.asarray(centre, float)
    verts, faces = [], []
    for i in range(n):
        z = (i / (n - 1) - 0.5) * height
        for k in range(n):
            s = k / (n - 1) * 2 - 1
            verts.append(centre + np.array([s * width / 2, abs(s) * depth, z]))
    for i in range(n - 1):
        for k in range(n - 1):
            a = i * n + k
            faces += [(a, a + 1, a + n + 1), (a, a + n + 1, a + n)]
    return np.array(verts, float), np.array(faces, np.int32)

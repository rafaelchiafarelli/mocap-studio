"""MPFB clothes (.mhclo + .obj) fitted to an MPFB body, in plain numpy, for dress_rest.py and dress_cloth.py.

A clothes vertex is three body vertices weighted plus an offset scaled by the body's size, as MPFB's
ClothesService.fit_clothes_to_human: x by the body's x, MakeHuman's y (up) by Blender's z, its z (depth) by Blender's y.
"""
import numpy as np


def read_mhclo(path):
    """Scale references, and per clothes vertex: three body vertices, their weights, the offset (MakeHuman axes)."""
    scale, rows, in_verts = {}, [], False
    for line in open(path):
        w = line.split()
        if not w or w[0].startswith("#"):
            continue
        if w[0] in ("x_scale", "y_scale", "z_scale"):
            scale[w[0]] = (int(w[1]), int(w[2]), float(w[3]))
        elif w[0] == "verts":
            in_verts = True
        elif in_verts and len(w) == 9:
            rows.append([float(x) for x in w])
        elif in_verts and len(w) == 1 and w[0].isdigit():
            v = int(w[0])
            rows.append([v, v, v, 1, 0, 0, 0, 0, 0])
        elif in_verts:
            in_verts = False
    r = np.array(rows)
    return scale, r[:, :3].astype(int), r[:, 3:6], r[:, 6:9]


def read_obj(path):
    """Faces (vertex indices), their UV indices and the UVs."""
    vt, faces, fuv = [], [], []
    for line in open(path):
        w = line.split()
        if not w:
            continue
        if w[0] == "vt":
            vt.append([float(w[1]), float(w[2])])
        elif w[0] == "f":
            faces.append([int(x.split("/")[0]) - 1 for x in w[1:]])
            fuv.append([int(x.split("/")[1]) - 1 for x in w[1:]])
    return faces, fuv, np.array(vt)


def frames(P1, P2, P3):
    """An orthonormal frame per triangle (columns: first edge, in-plane normal to it, normal)."""
    e1 = P2 - P1
    e1 /= np.linalg.norm(e1, axis=1, keepdims=True) + 1e-12
    n = np.cross(P2 - P1, P3 - P1)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    e2 = np.cross(n, e1)
    return np.stack([e1, e2, n], axis=2)


def fit(rest, scale, tri, w, d, posed=None):
    """Clothes vertices on the body. rest: body vertices with shape keys, no pose (sizes are read there). posed, if given:
    the same vertices posed; each offset then turns with its triangle from rest to the pose."""
    xs = abs(rest[scale["x_scale"][0], 0] - rest[scale["x_scale"][1], 0]) / scale["x_scale"][2]
    ys = abs(rest[scale["y_scale"][0], 2] - rest[scale["y_scale"][1], 2]) / scale["y_scale"][2]
    zs = abs(rest[scale["z_scale"][0], 1] - rest[scale["z_scale"][1], 1]) / scale["z_scale"][2]
    off = np.stack([d[:, 0] * xs, -d[:, 2] * zs, d[:, 1] * ys], axis=1)
    if posed is None:
        return np.einsum("nk,nkj->nj", w, rest[tri]) + off
    R0 = frames(*(rest[tri[:, k]] for k in range(3)))
    R1 = frames(*(posed[tri[:, k]] for k in range(3)))
    single = (tri[:, 0] == tri[:, 1]) & (tri[:, 1] == tri[:, 2])
    off_posed = np.einsum("nij,nj->ni", R1, np.einsum("nji,nj->ni", R0, off))
    off_posed[single] = off[single]
    return np.einsum("nk,nkj->nj", w, posed[tri]) + off_posed


def components(n, faces):
    """Connected part per vertex; parts ordered from highest to lowest (by mean height, given later)."""
    parent = list(range(n))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for f in faces:
        for i in range(len(f)):
            parent[root(f[i])] = root(f[(i + 1) % len(f)])
    return np.array([root(i) for i in range(n)])


def parts(X, faces):
    """{'cima': mask, 'baixo': mask}: the suit's upper and lower connected parts."""
    lab = components(len(X), faces)
    comps = sorted(np.unique(lab), key=lambda c: -X[lab == c, 2].mean())
    return {"cima": lab == comps[0], "baixo": lab == comps[1]}


def parts_by_height(X, faces, z_waist):
    """{'cima', 'baixo', 'toda'}: the connected parts whose mean height is above, below the waist, and all of it; for any
    garment (one piece is 'toda'; a two-part suit splits at the waist)."""
    lab = components(len(X), faces)
    up = np.zeros(len(X), bool)
    for c in np.unique(lab):
        sel = lab == c
        up[sel] = X[sel, 2].mean() > z_waist
    return {"cima": up, "baixo": ~up, "toda": np.ones(len(X), bool)}

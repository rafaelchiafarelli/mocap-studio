"""Counts creases on the simulated skin: edges of the shown skin bent more than BENT degrees where the rig's own skinning of the
same skin is bent less than FLAT. For comparing tissue runs objectively, not only by eye.

    python creases.py TECIDOS.npz PELE.pc2 LBS.npz [BENT] [FLAT]

LBS.npz: the subdivided skin skinned by the rig at some frames (keys f<frame>), from a Blender dump of HM_body with Subsurf 2.
Prints, per frame, the crease edges and where they are (rest height and side)."""
import struct
import sys

import numpy as np


def face_normals(v, quads):
    n = np.cross(v[quads[:, 2]] - v[quads[:, 0]], v[quads[:, 3]] - v[quads[:, 1]])
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def edge_faces(quads):
    e = np.concatenate([quads[:, [0, 1]], quads[:, [1, 2]], quads[:, [2, 3]], quads[:, [3, 0]]])
    f = np.tile(np.arange(len(quads)), 4)
    key = np.sort(e, axis=1)
    order = np.lexsort((key[:, 1], key[:, 0]))
    key, f = key[order], f[order]
    same = (key[1:] == key[:-1]).all(axis=1)
    return key[1:][same], f[:-1][same], f[1:][same]


def main(tissue, pc2, lbs, bent=25.0, flat=10.0):
    m = np.load(tissue)
    quads, ids, rest = m["sub_faces"], m["sub_ids"], m["sub_rest"]
    with open(pc2, "rb") as fh:
        h = struct.unpack("<12siiffi", fh.read(32))
        data = np.frombuffer(fh.read(), np.float32).reshape(h[5], h[2], 3)
    L = np.load(lbs)
    edges, fa, fb = edge_faces(quads)
    total = 0
    for k in sorted(L.files, key=lambda s: int(s[1:])):
        f = int(k[1:])
        ns, nl = face_normals(data[f - 1], quads), face_normals(L[k][ids], quads)
        a_sim = np.degrees(np.arccos(np.clip((ns[fa] * ns[fb]).sum(1), -1, 1)))
        a_lbs = np.degrees(np.arccos(np.clip((nl[fa] * nl[fb]).sum(1), -1, 1)))
        crease = (a_sim > bent) & (a_lbs < flat)
        total += int(crease.sum())
        p = rest[edges[crease, 0]]
        where = f"z {np.percentile(p[:, 2], 10):.2f}-{np.percentile(p[:, 2], 90):.2f}" if len(p) else ""
        print(f"frame {f}: {int(crease.sum())} crease edges {where}")
    print("total", total)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], *(float(x) for x in a[3:5]))

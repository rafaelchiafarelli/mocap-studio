"""What a contraction does to skin. The skin is a smooth sheet solved once per muscle: the muscle's patch moves, retaining ligaments and bone resist, and compressed tissue thickens outward.
Each muscle becomes one displacement field at full activation, stored as a shape key: its activation is a linear blend."""
import numpy as np
import scipy.sparse as sp
from scipy.sparse.csgraph import dijkstra
from scipy.sparse.linalg import splu
from scipy.spatial import cKDTree

NOSE_STIFFNESS = 1.0
LIDS_STIFFNESS = 1.0
LIGAMENT_STIFFNESS = 0.3  # relative to the sheet's median stiffness; declared
HARD = 10.0
BULGE_GAIN = 0.8  # how much of the conserved volume goes outward instead of sliding away; declared
THICK_CAP = 0.012  # tissue over bone that can bunch, m
BULGE_MAX = 0.004
NO_BONE = 0.03
FOLD_WAVE_FOREHEAD = 0.014
FOLD_RAYS = 16
FOLD_DEPTH = 0.0007  # declared


class Region:
    """The part of the skin that takes facial fields: head and upper neck, with its triangles and operators."""

    def __init__(self, ind, bone_points):
        skin, tris = ind["skin"], ind["tris"]
        self.ind = ind
        low = ind["rig"]["spine.005"]["head"][2]
        mask = skin[:, 2] > low
        keep = mask[tris].all(axis=1)
        self.tris_all = tris[keep]
        self.ids = np.flatnonzero(mask)
        index = -np.ones(len(skin), np.int64)
        index[self.ids] = np.arange(len(self.ids))
        self.index = index
        self.tris = index[self.tris_all]
        self.v = skin[self.ids]
        self.graph = edge_graph(self.v, self.tris)
        # Uniform weights: MPFB's lips have very thin triangles, and cotangent weights tear them.
        adj = (self.graph > 0).astype(float)
        self.L = sp.diags(np.asarray(adj.sum(axis=1)).ravel()) - adj
        self.A = (self.L.T @ self.L).tocsc()
        self.scale = float(np.median(self.A.diagonal()))
        self.normals = vertex_normals(self.v, self.tris)
        self.tree = cKDTree(bone_points)
        self.thick, _ = self.tree.query(self.v)
        self.anchors = np.zeros(len(self.v))
        self._set_anchors()

    def near(self, p, radius):
        return np.flatnonzero(np.linalg.norm(self.v - np.asarray(p), axis=1) < radius)

    def rig_point(self, name, end="head"):
        return np.array(self.ind["rig"][name][end])

    def _set_anchors(self):
        rig = self.ind["rig"]
        a = self.anchors
        # hard: the boundary with the rest of the body, the ears, the scalp behind the crown, the nose's bridge
        back = self.rig_point("ear.L")[1]
        a[self.v[:, 1] > back + 0.015] = HARD
        a[self.v[:, 2] < self.rig_point("spine.005")[2] + 0.015] = HARD
        for s in "LR":
            a[self.near(self.rig_point(f"ear.{s}.002"), 0.035)] = HARD
        a[self.near(self.rig_point("nose"), 0.008)] = HARD
        # the nose has bone and cartilage inside it, so a pull nearby doesn't widen it
        tip = self.rig_point("nose.001")
        a[self.near(tip, 0.022)] = np.maximum(a[self.near(tip, 0.022)], NOSE_STIFFNESS)
        # lids follow only their own muscles
        self.lids = np.zeros(len(self.v), bool)
        for s in "LR":
            self.lids |= np.linalg.norm(self.v - self.rig_point(f"eye.{s}", "tail"), axis=1) < 0.017
        # retaining ligaments: bands from bone to skin
        for s in "LR":
            sign = 1 if s == "L" else -1
            for p, r in ((self.rig_point(f"cheek.T.{s}") + np.array([-sign * 0.006, -0.008, -0.012]), 0.008),  # zygomatic
                         (self.rig_point(f"chin.{s}") + np.array([sign * 0.010, 0.004, -0.004]), 0.007),  # mandibular
                         (self.rig_point(f"jaw.{s}.001") + np.array([-sign * 0.002, -0.012, 0.018]), 0.008)):  # masseteric
                idx = self.near(p, r)
                a[idx] = np.maximum(a[idx], LIGAMENT_STIFFNESS)
            # orbital ligament: a ring around the eye
            eye = self.rig_point(f"eye.{s}", "tail")
            dist = np.linalg.norm(self.v - eye, axis=1)
            ring = (dist > 0.024) & (dist < 0.030)
            a[ring] = np.maximum(a[ring], LIGAMENT_STIFFNESS)

    def patch(self, vertex, radius):
        """Weights around a vertex by distance along the skin, so a lip's patch doesn't jump across the mouth to the other lip."""
        d = dijkstra(self.graph, indices=int(self.index[vertex]), limit=radius * 2.5)
        w = np.exp(-(d / radius) ** 2)
        w[~np.isfinite(d)] = 0.0
        return w

    def solve(self, targets, weights, hold_lids=True):
        """Displacement of every region vertex: targets (n,3) where weights (n) are above zero."""
        anchors = self.anchors + (LIDS_STIFFNESS * self.lids if hold_lids else 0.0)
        w = sp.diags((anchors + weights * HARD) * self.scale)
        lu = splu((self.A + w).tocsc())
        rhs = (weights * HARD * self.scale)[:, None] * targets
        return np.column_stack([lu.solve(rhs[:, k]) for k in range(3)])

    def tangent(self, vec):
        n = self.normals
        return vec - (vec * n).sum(axis=1, keepdims=True) * n * 0.8

    def add_bulge(self, u):
        """Compressed skin thickens outward; then skin is kept from sinking into bone."""
        area0 = vertex_areas(self.v, self.tris)
        area1 = vertex_areas(self.v + u, self.tris)
        ratio = np.clip(area1 / np.maximum(area0, 1e-12), 0.3, 3.0)
        # only tissue held against bone bunches: under the jaw there's nothing to push against
        h = np.minimum(self.thick, THICK_CAP) * (self.thick < NO_BONE)
        delta = np.clip(BULGE_GAIN * h * (1.0 / ratio - 1.0), 0.0, BULGE_MAX)
        for _ in range(8):
            delta = smooth(self.graph, delta)
        out = u + self.normals * delta[:, None]
        new = self.v + out
        d1, _ = self.tree.query(new)
        min_d = 0.6 * self.thick
        push = np.maximum(min_d - d1, 0.0)
        return out + self.normals * push[:, None]

    def add_folds(self, u, m):
        """Wrinkles as ripples on the skin where a muscle compresses it: across the forehead for frontalis, fanning from the eye's corner for orbicularis oculi. Too coarse a mesh below the wavelength, so subdivide when rendering."""
        name = m["name"]
        if not (name.startswith("frontalis") or name.startswith("orbicularis_oculi_orbital")):
            return u
        area0 = vertex_areas(self.v, self.tris)
        area1 = vertex_areas(self.v + u, self.tris)
        press = np.clip(1.0 - area1 / np.maximum(area0, 1e-12), 0.0, 0.5) / 0.5
        for _ in range(4):
            press = smooth(self.graph, press)
        if name.startswith("frontalis"):
            phase = self.v[:, 2] / FOLD_WAVE_FOREHEAD
        else:
            sign = 1 if name.endswith("_L") else -1
            corner = self.rig_point(f"lid.T.{'L' if sign > 0 else 'R'}.003", "tail")
            rel = self.v - corner
            mask = sign * rel[:, 0] > 0
            phase = np.arctan2(rel[:, 2], sign * rel[:, 0]) / (2 * np.pi) * FOLD_RAYS
            press = press * mask * np.exp(-(np.linalg.norm(rel, axis=1) / 0.028) ** 2)
        ripple = np.cos(2 * np.pi * phase) * press * FOLD_DEPTH
        return u + self.normals * ripple[:, None]

    def field(self, m):
        """Full-activation displacement of one muscle from the muscle list, for the region's vertices."""
        n = len(self.v)
        origin, insertion = np.array(m["points"][0]), np.array(m["points"][1])
        kind = m.get("kind", "linear")
        vid = int(m["parents"][1].split(":")[1])
        r = m["patch"]
        length = np.linalg.norm(origin - insertion)
        weights = np.zeros(n)
        targets = np.zeros((n, 3))
        if kind == "linear":
            weights = self.patch(vid, r)
            direction = (origin - insertion) / length
            t = np.broadcast_to(direction * m["contraction"] * length, (n, 3)).copy()
            targets = self.tangent(t) * weights[:, None]
            weights = (weights > 0.15) * weights
        elif kind in ("sphincter", "pucker", "lid"):
            weights = self.patch(vid, r)
            weights = (weights > 0.1) * weights
            to_centre = origin - self.v
            targets = to_centre * m["contraction"] * weights[:, None]
            if kind == "pucker":
                targets += np.array([0, -0.010, 0]) * weights[:, None]
            elif kind == "sphincter":
                targets = self.tangent(targets)
        u = self.solve(targets, weights, hold_lids=kind != "lid" and not m["name"].startswith("orbicularis_oculi"))
        return self.add_folds(self.add_bulge(u), m)


def smooth(graph, x):
    deg = np.maximum(np.asarray((graph > 0).sum(axis=1)).ravel(), 1)
    return 0.5 * x + 0.5 * ((graph > 0).astype(float) @ x) / deg


def cotan(v, t):
    """Cotangent Laplacian and lumped mass."""
    a, b, c = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    def cot(p, q, r):
        x, y = q - p, r - p
        return (x * y).sum(axis=1) / np.maximum(np.linalg.norm(np.cross(x, y), axis=1), 1e-12)
    ca, cb, cc = cot(a, b, c), cot(b, c, a), cot(c, a, b)
    i = np.concatenate([t[:, 1], t[:, 2], t[:, 2], t[:, 0], t[:, 0], t[:, 1]])
    j = np.concatenate([t[:, 2], t[:, 1], t[:, 0], t[:, 2], t[:, 1], t[:, 0]])
    w = 0.5 * np.concatenate([ca, ca, cb, cb, cc, cc])
    w = np.clip(w, 0.0, 5.0)  # negative weights on bad triangles destabilize the solve
    n = len(v)
    W = sp.coo_matrix((w, (i, j)), shape=(n, n)).tocsr()
    L = sp.diags(np.asarray(W.sum(axis=1)).ravel()) - W
    return L, vertex_areas(v, t)


def vertex_areas(v, t):
    area = 0.5 * np.linalg.norm(np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]]), axis=1)
    out = np.zeros(len(v))
    for k in range(3):
        np.add.at(out, t[:, k], area / 3)
    return out


def vertex_normals(v, t):
    fn = np.cross(v[t[:, 1]] - v[t[:, 0]], v[t[:, 2]] - v[t[:, 0]])
    out = np.zeros_like(v)
    for k in range(3):
        np.add.at(out, t[:, k], fn)
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)


def edge_graph(v, t):
    e = np.vstack([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]])
    d = np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1)
    n = len(v)
    G = sp.coo_matrix((d, (e[:, 0], e[:, 1])), shape=(n, n)).tocsr()
    return G.maximum(G.T)


def build_fields(ind, bones, muscles):
    points = np.vstack([bones[n]["verts"] for n in ("cranium", "mandible") if n in bones])
    region = Region(ind, points[:: max(1, len(points) // 40000)])
    out = {}
    for m in muscles:
        if m["group"] != "face":
            continue
        out[m["name"]] = region.field(m)
    return region, out


def peak_mm(field):
    return float(np.linalg.norm(field, axis=1).max() * 1000)

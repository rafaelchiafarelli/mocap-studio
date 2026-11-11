"""Soft tissue as tetrahedra, simulated with XPBD on the GPU through NVIDIA Warp (Apache 2.0). Runs in the GPU image: hm.sh --gpu.
The material is Neo-Hookean, with Young's modulus and Poisson's ratio per tetrahedron, as two constraints per tetrahedron
(Macklin and Müller 2021, "A Constraint-based Formulation of Stable Neo-Hookean Materials").
Each substep: predict under gravity, one Gauss-Seidel pass over the tetrahedra one colour at a time (no two tetrahedra of a colour share a node),
the floor, then velocities. Small steps with one pass each keep XPBD stable (Macklin et al. 2019, "Small Steps in Physics Simulation").
The first version, edges and volumes solved together and averaged, held too little: a cube lost up to 93% of its volume (docs/muscle-physics.md)."""
import numpy as np
import warp as wp


@wp.kernel
def _predict(x: wp.array(dtype=wp.vec3), v: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3),
             inv_mass: wp.array(dtype=float), gravity: wp.vec3, dt: float):
    i = wp.tid()
    x_prev[i] = x[i]
    if inv_mass[i] > 0.0:
        v[i] = v[i] + gravity * dt
        x[i] = x[i] + v[i] * dt


@wp.func
def _project(x: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float), a: int, b: int, c: int, d: int,
             g1: wp.vec3, g2: wp.vec3, g3: wp.vec3, C: float, alpha: float):
    g0 = -(g1 + g2 + g3)
    w = inv_mass[a] * wp.dot(g0, g0) + inv_mass[b] * wp.dot(g1, g1) + inv_mass[c] * wp.dot(g2, g2) + inv_mass[d] * wp.dot(g3, g3)
    if w + alpha > 0.0:
        dl = -C / (w + alpha)
        x[a] = x[a] + g0 * (dl * inv_mass[a])
        x[b] = x[b] + g1 * (dl * inv_mass[b])
        x[c] = x[c] + g2 * (dl * inv_mass[c])
        x[d] = x[d] + g3 * (dl * inv_mass[d])


@wp.kernel
def _neo_hookean(x: wp.array(dtype=wp.vec3), tets: wp.array(dtype=wp.vec4i), inv_rest: wp.array(dtype=wp.mat33), rest_volume: wp.array(dtype=float),
                 mu: wp.array(dtype=float), lam: wp.array(dtype=float), inv_mass: wp.array(dtype=float), dt: float, start: int):
    t = start + wp.tid()
    a, b, c, d = tets[t][0], tets[t][1], tets[t][2], tets[t][3]
    Dm_inv = inv_rest[t]
    vol = rest_volume[t]
    # Deviatoric: resists change of shape. C = |F|, its gradient F / |F|. A node's gradient is a column of dC/dF times Dm^-T
    F = wp.matrix_from_cols(x[b] - x[a], x[c] - x[a], x[d] - x[a]) * Dm_inv
    r = wp.sqrt(wp.ddot(F, F))
    if r > 1.0e-9:
        G = (F / r) * wp.transpose(Dm_inv)
        _project(x, inv_mass, a, b, c, d, wp.vec3(G[0, 0], G[1, 0], G[2, 0]), wp.vec3(G[0, 1], G[1, 1], G[2, 1]), wp.vec3(G[0, 2], G[1, 2], G[2, 2]),
                 r, 1.0 / (mu[t] * vol * dt * dt))
    # Hydrostatic: resists change of volume. C = det F - (1 + mu / lambda), its gradient the cofactor of F
    F = wp.matrix_from_cols(x[b] - x[a], x[c] - x[a], x[d] - x[a]) * Dm_inv
    f1 = wp.vec3(F[0, 0], F[1, 0], F[2, 0])
    f2 = wp.vec3(F[0, 1], F[1, 1], F[2, 1])
    f3 = wp.vec3(F[0, 2], F[1, 2], F[2, 2])
    cof = wp.matrix_from_cols(wp.cross(f2, f3), wp.cross(f3, f1), wp.cross(f1, f2))
    G = cof * wp.transpose(Dm_inv)
    _project(x, inv_mass, a, b, c, d, wp.vec3(G[0, 0], G[1, 0], G[2, 0]), wp.vec3(G[0, 1], G[1, 1], G[2, 1]), wp.vec3(G[0, 2], G[1, 2], G[2, 2]),
             wp.determinant(F) - 1.0 - mu[t] / lam[t], 1.0 / (lam[t] * vol * dt * dt))


@wp.kernel
def _clear_gradient(gradient: wp.array(dtype=wp.vec3), ids: wp.array(dtype=int)):
    gradient[ids[wp.tid()]] = wp.vec3(0.0, 0.0, 0.0)


@wp.kernel
def _clear_groups(volume: wp.array(dtype=float), weight: wp.array(dtype=float)):
    volume[wp.tid()] = 0.0
    weight[wp.tid()] = 0.0


@wp.kernel
def _sum_volume(x: wp.array(dtype=wp.vec3), tets: wp.array(dtype=wp.vec4i), ids: wp.array(dtype=int), group: wp.array(dtype=int),
                volume: wp.array(dtype=float), gradient: wp.array(dtype=wp.vec3)):
    k = wp.tid()
    t = tets[ids[k]]
    e1, e2, e3 = x[t[1]] - x[t[0]], x[t[2]] - x[t[0]], x[t[3]] - x[t[0]]
    wp.atomic_add(volume, group[k], wp.dot(wp.cross(e1, e2), e3) / 6.0)
    g1, g2, g3 = wp.cross(e2, e3) / 6.0, wp.cross(e3, e1) / 6.0, wp.cross(e1, e2) / 6.0
    wp.atomic_add(gradient, t[0], -(g1 + g2 + g3))
    wp.atomic_add(gradient, t[1], g1)
    wp.atomic_add(gradient, t[2], g2)
    wp.atomic_add(gradient, t[3], g3)


@wp.kernel
def _sum_weight(gradient: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float), ids: wp.array(dtype=int), group: wp.array(dtype=int), weight: wp.array(dtype=float)):
    k = wp.tid()
    n = ids[k]
    wp.atomic_add(weight, group[k], inv_mass[n] * wp.dot(gradient[n], gradient[n]))


@wp.kernel
def _apply_volume(x: wp.array(dtype=wp.vec3), gradient: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float), ids: wp.array(dtype=int), group: wp.array(dtype=int),
                  volume: wp.array(dtype=float), rest: wp.array(dtype=float), weight: wp.array(dtype=float)):
    k = wp.tid()
    n, g = ids[k], group[k]
    if weight[g] > 0.0:
        x[n] = x[n] + gradient[n] * ((rest[g] - volume[g]) / weight[g] * inv_mass[n])


@wp.kernel
def _floor(x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), floor: float):
    i = wp.tid()
    if x[i][2] < floor:
        # Resting contact with friction: the point stays where it touched
        x[i] = wp.vec3(x_prev[i][0], x_prev[i][1], floor)


@wp.kernel
def _velocity(x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), v: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float),
              dt: float, damping: wp.array(dtype=float)):
    i = wp.tid()
    if inv_mass[i] > 0.0:
        v[i] = (x[i] - x_prev[i]) / dt * (1.0 - damping[i] * dt)


@wp.kernel
def _velocity_relative(x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), v: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float),
                       rest: wp.array(dtype=wp.vec3), bone: wp.array(dtype=int), T0: wp.array(dtype=wp.mat44), T1: wp.array(dtype=wp.mat44),
                       frame: float, dt: float, damping: wp.array(dtype=float)):
    """Damps only the motion relative to the node's bone: a limb carried at speed isn't slowed, as if by air."""
    i = wp.tid()
    if inv_mass[i] > 0.0:
        b = bone[i]
        carried = (wp.transform_point(T1[b], rest[i]) - wp.transform_point(T0[b], rest[i])) / frame
        own = (x[i] - x_prev[i]) / dt - carried
        v[i] = carried + own * (1.0 - damping[i] * dt)


@wp.kernel
def _place(x: wp.array(dtype=wp.vec3), ids: wp.array(dtype=int), positions: wp.array(dtype=wp.vec3)):
    i = wp.tid()
    x[ids[i]] = positions[i]


@wp.kernel
def _drive(x: wp.array(dtype=wp.vec3), ids: wp.array(dtype=int), rest: wp.array(dtype=wp.vec3), bone: wp.array(dtype=int),
           T0: wp.array(dtype=wp.mat44), T1: wp.array(dtype=wp.mat44), a: float):
    i = wp.tid()
    b = bone[i]
    M = T0[b] * (1.0 - a) + T1[b] * a
    x[ids[i]] = wp.transform_point(M, rest[i])


def volumes(nodes, tets):
    v = nodes[tets]
    return np.einsum("ij,ij->i", np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), v[:, 3] - v[:, 0]) / 6


def lame(young, poisson):
    """Young's modulus (Pa) and Poisson's ratio to the Lamé parameters mu and lambda."""
    young, poisson = np.asarray(young, float), np.asarray(poisson, float)
    return young / (2 * (1 + poisson)), young * poisson / ((1 + poisson) * (1 - 2 * poisson))


def colours(tets, n_nodes):
    """A colour per tetrahedron, so that no two of one colour share a node. Greedy, in order."""
    used = [set() for _ in range(n_nodes)]
    out = np.empty(len(tets), np.int32)
    for t, nodes in enumerate(tets.tolist()):
        taken = used[nodes[0]] | used[nodes[1]] | used[nodes[2]] | used[nodes[3]]
        c = 0
        while c in taken:
            c += 1
        out[t] = c
        for n in nodes:
            used[n].add(c)
    return out


def voxel_colours(vox, tet_voxel):
    """The same for tetrahedra from layers.tetrahedra, at once: voxels two apart share no node, so the voxel's parity times its six tetrahedra."""
    parity = (vox[:, 0] % 2) + 2 * (vox[:, 1] % 2) + 4 * (vox[:, 2] % 2)
    return (parity[tet_voxel] * 6 + np.arange(len(tet_voxel)) % 6).astype(np.int32)


class Solver:
    """nodes (n x 3, m), tets (m x 4, positive volume), colours (from colours or voxel_colours), and per tetrahedron:
    density (kg/m3), Young's modulus (Pa), Poisson's ratio. Pinned nodes don't move by themselves; set_pinned moves them."""

    def __init__(self, nodes, tets, tet_colours, density, young, poisson, pinned=None, damping=0.0, floor=-1e9, device="cuda:0", sealed=None):
        self.device = device
        nodes = np.asarray(nodes, np.float64)
        order = np.argsort(tet_colours, kind="stable")
        tets = np.asarray(tets, np.int32)[order]
        per_tet = lambda value: np.broadcast_to(np.asarray(value, float), len(order))[order] if np.ndim(value) else np.full(len(order), float(value))
        density, young, poisson = per_tet(density), per_tet(young), per_tet(poisson)
        self.order = order
        self.slices = np.concatenate([[0], np.cumsum(np.bincount(np.asarray(tet_colours)[order]))])
        vol = volumes(nodes, tets)
        Dm = np.stack([nodes[tets[:, k]] - nodes[tets[:, 0]] for k in (1, 2, 3)], axis=2)
        mass = np.zeros(len(nodes))
        np.add.at(mass, tets.ravel(), np.repeat(vol * density / 4, 4))
        inv = np.where(mass > 0, 1 / np.maximum(mass, 1e-12), 0.0)
        if pinned is not None:
            inv[pinned] = 0.0
        mu, lam = lame(young, poisson)
        a = lambda arr, t: wp.array(np.ascontiguousarray(arr, np.int32 if t in (wp.vec4i, int) else np.float32), dtype=t, device=device)
        self.n = len(nodes)
        self.x, self.x_prev = a(nodes, wp.vec3), a(nodes, wp.vec3)
        self.v = wp.zeros(self.n, dtype=wp.vec3, device=device)
        self.inv_mass = a(inv, float)
        self.tets, self.rest_volume = a(tets, wp.vec4i), a(vol, float)
        self.inv_rest = a(np.linalg.inv(Dm), wp.mat33)
        self.mu, self.lam = a(mu, float), a(lam, float)
        # one value per node, or the same for all
        self.damping, self.floor = a(np.full(len(nodes), float(damping)) if np.ndim(damping) == 0 else np.asarray(damping, float), float), floor
        self.gravity = wp.vec3(0.0, 0.0, -9.81)
        self.rest_total = float(vol.sum())
        self.tets_host = tets
        self._graph, self._compiled = None, False
        self.drive_ids, self.all_rest = None, None
        self.sealed = None
        if sealed is not None:
            self._seal(np.asarray(sealed, np.int32)[order], tets, vol, len(nodes))

    def _seal(self, sealed, tets, vol, n_nodes):
        """sealed: per tetrahedron, in the solver's order, the sealed body it belongs to, or -1. Each body keeps its whole volume exactly, through one constraint, whatever its tetrahedra do: a bag of liquid, which holds its volume but not its shape."""
        ids = np.flatnonzero(sealed >= 0)
        groups = int(sealed.max()) + 1
        node_ids, first = np.unique(tets[ids].ravel(), return_index=True)
        a = lambda arr, t: wp.array(np.ascontiguousarray(arr, np.int32 if t is int else np.float32), dtype=t, device=self.device)
        self.sealed = {"tets": a(ids, int), "tet_group": a(sealed[ids], int), "nodes": a(node_ids, int), "node_group": a(sealed[ids][first // 4], int),
                       "rest": a(np.bincount(sealed[ids], vol[ids], groups), float), "volume": wp.zeros(groups, dtype=float, device=self.device),
                       "weight": wp.zeros(groups, dtype=float, device=self.device), "gradient": wp.zeros(n_nodes, dtype=wp.vec3, device=self.device), "groups": groups}
        self.sealed_rest = np.bincount(sealed[ids], vol[ids], groups)
        self.sealed_tets = [tets[ids[sealed[ids] == g]] for g in range(groups)]

    def _hold_sealed(self):
        q = self.sealed
        wp.launch(_clear_gradient, len(q["nodes"]), [q["gradient"], q["nodes"]], device=self.device)
        wp.launch(_clear_groups, q["groups"], [q["volume"], q["weight"]], device=self.device)
        wp.launch(_sum_volume, len(q["tets"]), [self.x, self.tets, q["tets"], q["tet_group"], q["volume"], q["gradient"]], device=self.device)
        wp.launch(_sum_weight, len(q["nodes"]), [q["gradient"], self.inv_mass, q["nodes"], q["node_group"], q["weight"]], device=self.device)
        wp.launch(_apply_volume, len(q["nodes"]), [self.x, q["gradient"], self.inv_mass, q["nodes"], q["node_group"], q["volume"], q["rest"], q["weight"]], device=self.device)

    def sealed_volumes(self):
        """Each sealed body's volume now, in m3."""
        x = self.positions().astype(float)
        return [float(volumes(x, t).sum()) for t in self.sealed_tets]

    def set_pinned(self, ids, positions):
        """Moves pinned nodes to these positions for the next step."""
        wp.launch(_place, len(ids), [self.x, wp.array(np.asarray(ids, np.int32), dtype=int, device=self.device),
                                     wp.array(np.asarray(positions, np.float32), dtype=wp.vec3, device=self.device)], device=self.device)

    def drive(self, ids, rest, all_rest=None, bone=None, all_bone=None, n_bones=1):
        """These nodes follow a rigid transform from now on: each frame, set_drive gives the transform at its start and end,
        and every substep places them part of the way, so a bone moves smoothly within the frame. Their mass is set to infinite.
        all_rest, every node's position in the same rest frame, makes damping act only on motion relative to that frame.
        Without it, damping slows the absolute velocity, like air: a block carried at walking speed trailed by 12 mm (thigh_walk_v1).
        With several bones, bone gives each driven node's bone and all_bone each node's nearest, whose motion its damping follows;
        set_drive then takes one transform per bone. Left out, everything follows bone 0."""
        ids = np.asarray(ids, np.int32)
        inv = self.inv_mass.numpy()
        inv[ids] = 0.0
        self.inv_mass.assign(inv)
        self.drive_ids = wp.array(ids, dtype=int, device=self.device)
        self.drive_rest = wp.array(np.asarray(rest, np.float32), dtype=wp.vec3, device=self.device)
        self.drive_bone = wp.array(np.zeros(len(ids), np.int32) if bone is None else np.asarray(bone, np.int32), dtype=int, device=self.device)
        self.node_bone = wp.array(np.zeros(self.n, np.int32) if all_bone is None else np.asarray(all_bone, np.int32), dtype=int, device=self.device)
        eye = np.repeat(np.eye(4, dtype=np.float32)[None], n_bones, axis=0)
        self.T0 = wp.array(eye, dtype=wp.mat44, device=self.device)
        self.T1 = wp.array(eye, dtype=wp.mat44, device=self.device)
        if all_rest is not None:
            self.all_rest = wp.array(np.asarray(all_rest, np.float32), dtype=wp.vec3, device=self.device)

    def set_drive(self, start, end):
        """The driven nodes' transform (4 x 4, from rest, or one per bone) at the start and the end of the next frame."""
        self.T0.assign(np.asarray(start, np.float32).reshape(-1, 4, 4))
        self.T1.assign(np.asarray(end, np.float32).reshape(-1, 4, 4))

    def step(self, dt, substeps):
        self.frame = dt
        return self._step(dt, substeps)

    def _step(self, dt, substeps):
        """One frame. On the GPU, the second call records the frame's launches as a CUDA graph and later calls replay it:
        a frame is about a thousand small launches, and launching them one by one cost more than the work (gpu_bench_v2)."""
        key = (dt, substeps)
        if not self.device.startswith("cuda"):
            return self._substeps(dt / substeps, substeps)
        if self._graph is not None and self._graph[0] == key:
            return wp.capture_launch(self._graph[1])
        if self._compiled:
            with wp.ScopedCapture(device=self.device) as capture:
                self._substeps(dt / substeps, substeps)
            self._graph = (key, capture.graph)
            return wp.capture_launch(capture.graph)
        self._substeps(dt / substeps, substeps)
        self._compiled = True

    def _substeps(self, h, substeps):
        for k in range(substeps):
            if self.drive_ids is not None:
                wp.launch(_drive, len(self.drive_ids), [self.x, self.drive_ids, self.drive_rest, self.drive_bone, self.T0, self.T1, (k + 1) / substeps],
                          device=self.device)
            wp.launch(_predict, self.n, [self.x, self.v, self.x_prev, self.inv_mass, self.gravity, h], device=self.device)
            for c in range(len(self.slices) - 1):
                start, stop = int(self.slices[c]), int(self.slices[c + 1])
                wp.launch(_neo_hookean, stop - start, [self.x, self.tets, self.inv_rest, self.rest_volume, self.mu, self.lam, self.inv_mass, h, start],
                          device=self.device)
            if self.sealed is not None:
                self._hold_sealed()
            wp.launch(_floor, self.n, [self.x, self.x_prev, self.floor], device=self.device)
            if self.all_rest is not None:
                wp.launch(_velocity_relative, self.n, [self.x, self.x_prev, self.v, self.inv_mass, self.all_rest, self.node_bone, self.T0, self.T1,
                                                       self.frame, h, self.damping],
                          device=self.device)
            else:
                wp.launch(_velocity, self.n, [self.x, self.x_prev, self.v, self.inv_mass, h, self.damping], device=self.device)

    def positions(self):
        return self.x.numpy()

    def volume(self, which=None):
        """Total volume now; which selects tetrahedra in the order they were given."""
        v = volumes(self.positions().astype(float), self.tets_host)
        if which is None:
            return float(v.sum())
        return float(v[np.argsort(self.order)][which].sum())

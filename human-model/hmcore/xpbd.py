"""Soft tissue as tetrahedra, simulated with XPBD on the GPU through NVIDIA Warp (Apache 2.0). Runs in the GPU image: hm.sh --gpu.
Each substep: predict under gravity, one pass of edge and volume constraints solved together (Jacobi, averaged per node), the floor, then velocities.
Small steps with one pass each are the XPBD way to stay stable (Macklin et al. 2019, "Small Steps in Physics Simulation")."""
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


@wp.kernel
def _edges(x: wp.array(dtype=wp.vec3), edges: wp.array(dtype=wp.vec2i), rest: wp.array(dtype=float), compliance: wp.array(dtype=float),
           inv_mass: wp.array(dtype=float), dt: float, delta: wp.array(dtype=wp.vec3), count: wp.array(dtype=float)):
    e = wp.tid()
    i, j = edges[e][0], edges[e][1]
    w = inv_mass[i] + inv_mass[j]
    d = x[i] - x[j]
    length = wp.length(d)
    if w == 0.0 or length < 1.0e-9:
        return
    n = d / length
    dl = -(length - rest[e]) / (w + compliance[e] / (dt * dt))
    wp.atomic_add(delta, i, n * (dl * inv_mass[i]))
    wp.atomic_add(delta, j, n * (-dl * inv_mass[j]))
    wp.atomic_add(count, i, 1.0)
    wp.atomic_add(count, j, 1.0)


@wp.kernel
def _volumes(x: wp.array(dtype=wp.vec3), tets: wp.array(dtype=wp.vec4i), rest: wp.array(dtype=float), compliance: wp.array(dtype=float),
             inv_mass: wp.array(dtype=float), dt: float, delta: wp.array(dtype=wp.vec3), count: wp.array(dtype=float)):
    t = wp.tid()
    a, b, c, d = tets[t][0], tets[t][1], tets[t][2], tets[t][3]
    x0, x1, x2, x3 = x[a], x[b], x[c], x[d]
    g1 = wp.cross(x2 - x0, x3 - x0) / 6.0
    g2 = wp.cross(x3 - x0, x1 - x0) / 6.0
    g3 = wp.cross(x1 - x0, x2 - x0) / 6.0
    g0 = -(g1 + g2 + g3)
    w = inv_mass[a] * wp.dot(g0, g0) + inv_mass[b] * wp.dot(g1, g1) + inv_mass[c] * wp.dot(g2, g2) + inv_mass[d] * wp.dot(g3, g3)
    if w == 0.0:
        return
    volume = wp.dot(wp.cross(x1 - x0, x2 - x0), x3 - x0) / 6.0
    dl = -(volume - rest[t]) / (w + compliance[t] / (dt * dt))
    wp.atomic_add(delta, a, g0 * (dl * inv_mass[a]))
    wp.atomic_add(delta, b, g1 * (dl * inv_mass[b]))
    wp.atomic_add(delta, c, g2 * (dl * inv_mass[c]))
    wp.atomic_add(delta, d, g3 * (dl * inv_mass[d]))
    for k in range(4):
        wp.atomic_add(count, tets[t][k], 1.0)


@wp.kernel
def _apply(x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), delta: wp.array(dtype=wp.vec3), count: wp.array(dtype=float),
           relax: float, floor: float):
    i = wp.tid()
    if count[i] > 0.0:
        x[i] = x[i] + delta[i] * (relax / count[i])
    delta[i] = wp.vec3(0.0)
    count[i] = 0.0
    p = x[i]
    if p[2] < floor:
        # Resting contact with friction: the point stays where it touched
        x[i] = wp.vec3(x_prev[i][0], x_prev[i][1], floor)


@wp.kernel
def _velocity(x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), v: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float),
              dt: float, damping: float):
    i = wp.tid()
    if inv_mass[i] > 0.0:
        v[i] = (x[i] - x_prev[i]) / dt * (1.0 - damping * dt)


def tet_edges(tets):
    """Every edge of the tetrahedra once, and for each the tetrahedra it belongs to (as a list of the first one, for its material)."""
    pairs = np.sort(tets[:, [[0, 1], [0, 2], [0, 3], [1, 2], [1, 3], [2, 3]]].reshape(-1, 2), axis=1)
    edges, first = np.unique(pairs, axis=0, return_index=True)
    return edges, first // 6


def volumes(nodes, tets):
    v = nodes[tets]
    return np.einsum("ij,ij->i", np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), v[:, 3] - v[:, 0]) / 6


class Solver:
    """nodes (n x 3, m), tets (m x 4, positive volume), per tetrahedron: density (kg/m3), edge and volume compliance (m/N and 1/Pa, 0 is rigid).
    pinned nodes don't move by themselves; set_pinned moves them."""

    def __init__(self, nodes, tets, density, edge_compliance, volume_compliance, pinned=None, damping=0.0, floor=-1e9, device="cuda:0"):
        self.device = device
        nodes = np.asarray(nodes, np.float32)
        tets = np.asarray(tets, np.int32)
        vol = volumes(nodes.astype(float), tets)
        mass = np.zeros(len(nodes))
        np.add.at(mass, tets.ravel(), np.repeat(vol * np.broadcast_to(density, len(tets)) / 4, 4))
        inv = np.where(mass > 0, 1 / np.maximum(mass, 1e-12), 0.0)
        if pinned is not None:
            inv[pinned] = 0.0
        edges, owner = tet_edges(tets)
        rest_len = np.linalg.norm(nodes[edges[:, 0]] - nodes[edges[:, 1]], axis=1)
        a = lambda arr, t: wp.array(arr, dtype=t, device=device)
        self.n = len(nodes)
        self.x, self.x_prev = a(nodes, wp.vec3), a(nodes, wp.vec3)
        self.v = wp.zeros(self.n, dtype=wp.vec3, device=device)
        self.inv_mass = a(inv.astype(np.float32), float)
        self.edges, self.edge_rest = a(edges.astype(np.int32), wp.vec2i), a(rest_len.astype(np.float32), float)
        self.edge_compliance = a(np.broadcast_to(edge_compliance, len(tets))[owner].astype(np.float32), float)
        self.tets, self.tet_rest = a(tets, wp.vec4i), a(vol.astype(np.float32), float)
        self.tet_compliance = a(np.broadcast_to(volume_compliance, len(tets)).astype(np.float32), float)
        self.delta = wp.zeros(self.n, dtype=wp.vec3, device=device)
        self.count = wp.zeros(self.n, dtype=float, device=device)
        self.damping, self.floor = damping, floor
        self.gravity = wp.vec3(0.0, 0.0, -9.81)
        self.rest_volume = float(vol.sum())

    def set_pinned(self, ids, positions):
        """Moves pinned nodes to these positions for the next step."""
        x = self.x.numpy()
        x[ids] = positions
        self.x.assign(x)

    def step(self, dt, substeps, relax=1.0):
        h = dt / substeps
        for _ in range(substeps):
            wp.launch(_predict, self.n, [self.x, self.v, self.x_prev, self.inv_mass, self.gravity, h], device=self.device)
            wp.launch(_edges, len(self.edges), [self.x, self.edges, self.edge_rest, self.edge_compliance, self.inv_mass, h, self.delta, self.count], device=self.device)
            wp.launch(_volumes, len(self.tets), [self.x, self.tets, self.tet_rest, self.tet_compliance, self.inv_mass, h, self.delta, self.count], device=self.device)
            wp.launch(_apply, self.n, [self.x, self.x_prev, self.delta, self.count, relax, self.floor], device=self.device)
            wp.launch(_velocity, self.n, [self.x, self.x_prev, self.v, self.inv_mass, h, self.damping], device=self.device)

    def positions(self):
        return self.x.numpy()

    def volume(self):
        return float(volumes(self.positions().astype(float), self.tets.numpy()).sum())

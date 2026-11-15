"""hmcore.xpbd.Solver with what the graded tissue needs (step 11), kept here while it is an investigation:
- damping per node (each group has its own), always relative to the node's bone, as xpbd's _velocity_relative;
- glue between the bands: a node of a finer band is held at its barycentric place in a coarser band's tetrahedron
  (a tiny compliance, GLUE_COMPLIANCE), solved Jacobi-style with each node's correction divided by how many glue constraints touch it.
GPU image only (hm.sh --gpu)."""
import numpy as np
import warp as wp

from hmcore import xpbd


@wp.kernel
def _velocity_relative_nodes(x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), v: wp.array(dtype=wp.vec3),
                             inv_mass: wp.array(dtype=float), rest: wp.array(dtype=wp.vec3), bone: wp.array(dtype=int),
                             T0: wp.array(dtype=wp.mat44), T1: wp.array(dtype=wp.mat44), frame: float, dt: float,
                             damping: wp.array(dtype=float)):
    i = wp.tid()
    if inv_mass[i] > 0.0:
        b = bone[i]
        carried = (wp.transform_point(T1[b], rest[i]) - wp.transform_point(T0[b], rest[i])) / frame
        own = (x[i] - x_prev[i]) / dt - carried
        v[i] = carried + own * wp.max(0.0, 1.0 - damping[i] * dt)


@wp.kernel
def _glue(x: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float), node: wp.array(dtype=int), tet: wp.array(dtype=wp.vec4i),
          w: wp.array(dtype=wp.vec4), dx: wp.array(dtype=wp.vec3), alpha: float):
    i = wp.tid()
    n = node[i]
    t = tet[i]
    ww = w[i]
    p = ww[0] * x[t[0]] + ww[1] * x[t[1]] + ww[2] * x[t[2]] + ww[3] * x[t[3]]
    C = x[n] - p
    denom = inv_mass[n] + ww[0] * ww[0] * inv_mass[t[0]] + ww[1] * ww[1] * inv_mass[t[1]] + ww[2] * ww[2] * inv_mass[t[2]] + ww[3] * ww[3] * inv_mass[t[3]]
    if denom > 0.0:
        lam = C / (denom + alpha)
        wp.atomic_add(dx, n, -inv_mass[n] * lam)
        for k in range(4):
            wp.atomic_add(dx, t[k], ww[k] * inv_mass[t[k]] * lam)


@wp.kernel
def _apply(x: wp.array(dtype=wp.vec3), dx: wp.array(dtype=wp.vec3), share: wp.array(dtype=float)):
    i = wp.tid()
    x[i] = x[i] + dx[i] * share[i]
    dx[i] = wp.vec3(0.0, 0.0, 0.0)


# The glue's compliance (m/N): next to nothing, but never zero. With zero, a glue whose only free node had a weight of 3e-15
# (the embedded node and the other three driven) divided by ~1e-25 and threw that node to 1e13 m in one substep (2026-11-14).
GLUE_COMPLIANCE = 1e-8
WEIGHT_FLOOR = 1e-6  # glue weights below this are taken as zero


class GradedSolver(xpbd.Solver):
    def __init__(self, nodes, tets, colours, density, young, poisson, node_damping, emb_node, emb_tets, emb_w, glue_passes=2, device="cuda:0"):
        super().__init__(nodes, tets, colours, density, young, poisson, damping=0.0, device=device)
        self.node_damping = wp.array(np.asarray(node_damping, np.float32), dtype=float, device=device)
        self.emb_node = wp.array(np.asarray(emb_node, np.int32), dtype=int, device=device)
        self.emb_tets = wp.array(np.asarray(emb_tets, np.int32), dtype=wp.vec4i, device=device)
        emb_w = np.where(np.abs(emb_w) < WEIGHT_FLOOR, 0.0, emb_w)
        self.emb_w = wp.array(np.asarray(emb_w, np.float32), dtype=wp.vec4, device=device)
        count = np.bincount(np.concatenate([np.asarray(emb_node).ravel(), np.asarray(emb_tets).ravel()]), minlength=self.n)
        self.share = wp.array((1.0 / np.maximum(count, 1)).astype(np.float32), dtype=float, device=device)
        self.dx = wp.zeros(self.n, dtype=wp.vec3, device=device)
        self.glue_passes = glue_passes

    def _substeps(self, h, substeps):
        for k in range(substeps):
            wp.launch(xpbd._drive, len(self.drive_ids), [self.x, self.drive_ids, self.drive_rest, self.drive_bone, self.T0, self.T1, (k + 1) / substeps],
                      device=self.device)
            wp.launch(xpbd._predict, self.n, [self.x, self.v, self.x_prev, self.inv_mass, self.gravity, h], device=self.device)
            for c in range(len(self.slices) - 1):
                start, stop = int(self.slices[c]), int(self.slices[c + 1])
                if stop > start:
                    wp.launch(xpbd._neo_hookean, stop - start, [self.x, self.tets, self.inv_rest, self.rest_volume, self.mu, self.lam, self.inv_mass, h, start],
                              device=self.device)
            for _ in range(self.glue_passes):
                wp.launch(_glue, len(self.emb_node), [self.x, self.inv_mass, self.emb_node, self.emb_tets, self.emb_w, self.dx,
                                                      GLUE_COMPLIANCE / (h * h)], device=self.device)
                wp.launch(_apply, self.n, [self.x, self.dx, self.share], device=self.device)
            wp.launch(_velocity_relative_nodes, self.n, [self.x, self.x_prev, self.v, self.inv_mass, self.all_rest, self.node_bone, self.T0, self.T1,
                                                         self.frame, h, self.node_damping], device=self.device)

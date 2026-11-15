"""GradedSolver (tissue_solver.py) plus cloth and contact, solved together (step 17, Rafael 2026-11-14: dress the body at rest,
then simulate tissue and clothes as one, so the cloth between arm and flank keeps them apart).

The cloth's vertices are appended to the tissue's nodes, with their real mass (fabric weight times area). Each substep, after the
tissue and the bands' glue:
- the shown skin is read from its tetrahedra (barycentric), and Warp meshes of it are refitted;
- cloth: edges keep their rest length (shrunk by `encolhimento`) and the vertices across each pair of triangles keep theirs, for
  bending; XPBD with a compliance from the sheet's stiffness, Jacobi passes averaged per vertex;
- contact, cloth on skin: a cloth vertex nearer the skin than its thickness is pushed out along the skin's normal, and the skin's
  tetrahedra are pushed back by the same impulse through the skin point's weights (two-way: the softer, lighter side gives);
  friction holds the vertex against the skin's own motion up to `atrito` times the push;
- contact, skin under cloth: a skin point that lay under the cloth at rest is kept under the cloth's triangles, so a nipple
  doesn't come through between its vertices;
- contact, skin on skin: a skin point of one part (trunk, each arm, each leg) nearer than `pele_pele` to the skin of another part is
  pushed out and that skin pushed back, both through their tetrahedra. Points that lie near each other at rest (across the border
  between two parts) aren't contact.
All contact corrections are summed and averaged per node (Jacobi). GPU image only (hm.sh --gpu).
"""
import numpy as np
import warp as wp

from hmcore import xpbd
from tissue_solver import GradedSolver, _apply


# a contact counts only if the point lies along the face's normal: |d| at least this share of its distance to the face
FACING = wp.constant(0.9)


@wp.kernel
def _skin_points(x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), sn: wp.array(dtype=wp.vec4i), sw: wp.array(dtype=wp.vec4),
                 sx: wp.array(dtype=wp.vec3), sx_prev: wp.array(dtype=wp.vec3)):
    j = wp.tid()
    n = sn[j]
    w = sw[j]
    sx[j] = w[0] * x[n[0]] + w[1] * x[n[1]] + w[2] * x[n[2]] + w[3] * x[n[3]]
    sx_prev[j] = w[0] * x_prev[n[0]] + w[1] * x_prev[n[1]] + w[2] * x_prev[n[2]] + w[3] * x_prev[n[3]]


@wp.kernel
def _distance(x: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float), pair: wp.array(dtype=wp.vec2i), rest: wp.array(dtype=float),
              compliance: wp.array(dtype=float), inv_h2: float, dx: wp.array(dtype=wp.vec3)):
    e = wp.tid()
    i = pair[e][0]
    j = pair[e][1]
    d = x[j] - x[i]
    L = wp.length(d)
    w = inv_mass[i] + inv_mass[j]
    if L > 1.0e-9 and w > 0.0:
        n = d / L
        s = (L - rest[e]) / (w + compliance[e] * inv_h2)
        wp.atomic_add(dx, i, n * (inv_mass[i] * s))
        wp.atomic_add(dx, j, -n * (inv_mass[j] * s))


@wp.func
def _surface_weight(t: wp.vec3i, u: float, v: float, sn: wp.array(dtype=wp.vec4i), sw: wp.array(dtype=wp.vec4), inv_mass: wp.array(dtype=float)):
    W = float(0.0)
    for k in range(3):
        b = u
        if k == 1:
            b = v
        if k == 2:
            b = 1.0 - u - v
        n = sn[t[k]]
        w = sw[t[k]]
        for m in range(4):
            c = b * w[m]
            W += c * c * inv_mass[n[m]]
    return W


@wp.func
def _push_surface(t: wp.vec3i, u: float, v: float, sn: wp.array(dtype=wp.vec4i), sw: wp.array(dtype=wp.vec4), inv_mass: wp.array(dtype=float),
                  impulse: wp.vec3, dx: wp.array(dtype=wp.vec3), cnt: wp.array(dtype=float)):
    for k in range(3):
        b = u
        if k == 1:
            b = v
        if k == 2:
            b = 1.0 - u - v
        n = sn[t[k]]
        w = sw[t[k]]
        for m in range(4):
            c = b * w[m]
            if c * inv_mass[n[m]] > 0.0:
                wp.atomic_add(dx, n[m], impulse * (c * inv_mass[n[m]]))
                wp.atomic_add(cnt, n[m], 1.0)


@wp.kernel
def _cloth_contact(mesh: wp.uint64, x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float), c0: int,
                   sx: wp.array(dtype=wp.vec3), sx_prev: wp.array(dtype=wp.vec3), tris: wp.array(dtype=wp.vec3i),
                   sn: wp.array(dtype=wp.vec4i), sw: wp.array(dtype=wp.vec4), orient: float, thick: wp.array(dtype=float), mu: wp.array(dtype=float),
                   max_dist: float, dx: wp.array(dtype=wp.vec3), cnt: wp.array(dtype=float), depth: wp.array(dtype=float)):
    i = wp.tid()
    c = c0 + i
    p = x[c]
    depth[i] = 1.0
    q = wp.mesh_query_point_no_sign(mesh, p, max_dist)
    if q.result:
        t = tris[q.face]
        u = q.u
        v = q.v
        a = sx[t[0]]
        b = sx[t[1]]
        e = sx[t[2]]
        cp = u * a + v * b + (1.0 - u - v) * e
        nrm = wp.normalize(wp.cross(b - a, e - a)) * orient
        d = wp.dot(p - cp, nrm)
        # only in front of (or behind) the face: off an open border (wrist, neck, a part's edge) the nearest point's normal says nothing
        if wp.abs(d) < FACING * wp.length(p - cp):
            return
        depth[i] = d
        C = d - thick[i]
        if C < 0.0:
            W = inv_mass[c] + _surface_weight(t, u, v, sn, sw, inv_mass)
            if W > 0.0:
                s = -C / W
                move = nrm * (inv_mass[c] * s)
                # friction: the vertex's motion along the skin, relative to the skin point's, is held up to mu times the push
                cpp = u * sx_prev[t[0]] + v * sx_prev[t[1]] + (1.0 - u - v) * sx_prev[t[2]]
                rel = (p + move - x_prev[c]) - (cp - cpp)
                tang = rel - nrm * wp.dot(rel, nrm)
                tl = wp.length(tang)
                if tl > 1.0e-12:
                    move = move - tang * wp.min(1.0, mu[i] * wp.length(move) / tl)
                wp.atomic_add(dx, c, move)
                wp.atomic_add(cnt, c, 1.0)
                _push_surface(t, u, v, sn, sw, inv_mass, -nrm * s, dx, cnt)


@wp.kernel
def _skin_contact(mesh: wp.uint64, ids: wp.array(dtype=int), x: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float),
                  sx: wp.array(dtype=wp.vec3), sub_rest: wp.array(dtype=wp.vec3), tris: wp.array(dtype=wp.vec3i),
                  sn: wp.array(dtype=wp.vec4i), sw: wp.array(dtype=wp.vec4), orient: float, thick: float, far_rest: float,
                  max_dist: float, dx: wp.array(dtype=wp.vec3), cnt: wp.array(dtype=float), depth: wp.array(dtype=float)):
    k = wp.tid()
    j = ids[k]
    p = sx[j]
    depth[j] = 1.0
    q = wp.mesh_query_point_no_sign(mesh, p, max_dist)
    if q.result:
        t = tris[q.face]
        u = q.u
        v = q.v
        rp = u * sub_rest[t[0]] + v * sub_rest[t[1]] + (1.0 - u - v) * sub_rest[t[2]]
        if wp.length(sub_rest[j] - rp) < far_rest:
            return
        a = sx[t[0]]
        b = sx[t[1]]
        e = sx[t[2]]
        cp = u * a + v * b + (1.0 - u - v) * e
        nrm = wp.normalize(wp.cross(b - a, e - a)) * orient
        d = wp.dot(p - cp, nrm)
        if wp.abs(d) < FACING * wp.length(p - cp):
            return
        depth[j] = d
        C = d - thick
        if C < 0.0:
            nj = sn[j]
            wj = sw[j]
            W = _surface_weight(t, u, v, sn, sw, inv_mass)
            for m in range(4):
                W += wj[m] * wj[m] * inv_mass[nj[m]]
            if W > 0.0:
                s = -C / W
                for m in range(4):
                    if wj[m] * inv_mass[nj[m]] > 0.0:
                        wp.atomic_add(dx, nj[m], nrm * (wj[m] * inv_mass[nj[m]] * s))
                        wp.atomic_add(cnt, nj[m], 1.0)
                _push_surface(t, u, v, sn, sw, inv_mass, -nrm * s, dx, cnt)


@wp.kernel
def _copy_cloth(x: wp.array(dtype=wp.vec3), c0: int, pts: wp.array(dtype=wp.vec3)):
    i = wp.tid()
    pts[i] = x[c0 + i]


@wp.kernel
def _skin_under_cloth(mesh: wp.uint64, ids: wp.array(dtype=int), x: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float), c0: int,
                      sx: wp.array(dtype=wp.vec3), sn: wp.array(dtype=wp.vec4i), sw: wp.array(dtype=wp.vec4), ctris: wp.array(dtype=wp.vec3i),
                      sub_rest: wp.array(dtype=wp.vec3), cloth_rest: wp.array(dtype=wp.vec3), near_rest: float,
                      vpart: wp.array(dtype=int), ctri_part: wp.array(dtype=int),
                      thick: float, max_dist: float, dx: wp.array(dtype=wp.vec3), cnt: wp.array(dtype=float)):
    """A skin point that lay under the cloth at rest stays under it: a nipple doesn't come through between the cloth's vertices.
    The cloth's triangles are wound so their normal points away from the body. Only cloth that lay over this point at rest
    (within near_rest) counts: with the arms down, the inner arm's nearest cloth became the top's side, and pushing the arm under
    it drove it into the trunk (teste_3). And only cloth over the same part (a sleeve's triangle over the arm, not the flank): in
    the armpit, arm and flank both held the sleeve and stretched it 50% (teste_4)."""
    k = wp.tid()
    j = ids[k]
    p = sx[j]
    q = wp.mesh_query_point_no_sign(mesh, p, max_dist)
    if q.result:
        if ctri_part[q.face] != vpart[j]:
            return
        t = ctris[q.face]
        u = q.u
        v = q.v
        rcp = u * cloth_rest[t[0]] + v * cloth_rest[t[1]] + (1.0 - u - v) * cloth_rest[t[2]]
        if wp.length(sub_rest[j] - rcp) > near_rest:
            return
        a = x[c0 + t[0]]
        b = x[c0 + t[1]]
        e = x[c0 + t[2]]
        cp = u * a + v * b + (1.0 - u - v) * e
        nrm = wp.normalize(wp.cross(b - a, e - a))
        d = wp.dot(p - cp, nrm)
        if wp.abs(d) < FACING * wp.length(p - cp):
            return
        over = d + thick
        if over > 0.0:
            nj = sn[j]
            wj = sw[j]
            W = float(0.0)
            for m in range(4):
                W += wj[m] * wj[m] * inv_mass[nj[m]]
            bu = wp.vec3(u, v, 1.0 - u - v)
            for m in range(3):
                W += bu[m] * bu[m] * inv_mass[c0 + t[m]]
            if W > 0.0:
                s = over / W
                for m in range(4):
                    if wj[m] * inv_mass[nj[m]] > 0.0:
                        wp.atomic_add(dx, nj[m], -nrm * (wj[m] * inv_mass[nj[m]] * s))
                        wp.atomic_add(cnt, nj[m], 1.0)
                for m in range(3):
                    wp.atomic_add(dx, c0 + t[m], nrm * (bu[m] * inv_mass[c0 + t[m]] * s))
                    wp.atomic_add(cnt, c0 + t[m], 1.0)


@wp.kernel
def _apply_mean(x: wp.array(dtype=wp.vec3), dx: wp.array(dtype=wp.vec3), cnt: wp.array(dtype=float)):
    i = wp.tid()
    if cnt[i] > 0.0:
        x[i] = x[i] + dx[i] / cnt[i]
    dx[i] = wp.vec3(0.0, 0.0, 0.0)
    cnt[i] = 0.0


class ClothTissueSolver(GradedSolver):
    """GradedSolver's arguments for the tissue (nodes, node_damping, all per node, cover the tissue only), then:
    cloth_x (c x 3) and cloth_mass (c) the cloth's vertices; pairs (p x 2, indices into cloth_x), rest lengths, compliances (m/N):
    edges and bending pairs together; cloth_damping (c); cloth_thick, cloth_mu (c), per vertex;
    skin: sn (s x 4 node indices), sw (s x 4 weights), sub_rest (s x 3), tris (k x 3 into the skin), part (k, each triangle's part),
    vertex_part (s); skin_thick, far_rest (m)."""

    def __init__(self, nodes, tets, colours, density, young, poisson, node_damping, emb_node, emb_tets, emb_w,
                 cloth_x, cloth_mass, pairs, rest, compliance, cloth_damping, cloth_thick, cloth_mu,
                 sn, sw, sub_rest, tris, part, vertex_part, skin_thick, far_rest, cloth_tris=None, covered=None, cloth_tri_part=None, cloth_passes=2, device="cuda:0"):
        self.c0 = len(nodes)
        all_nodes = np.concatenate([np.asarray(nodes, float), np.asarray(cloth_x, float)])
        damping = np.concatenate([np.asarray(node_damping, np.float32), np.asarray(cloth_damping, np.float32)])
        super().__init__(all_nodes, tets, colours, density, young, poisson, damping, emb_node, emb_tets, emb_w, device=device)
        inv = self.inv_mass.numpy()
        inv[self.c0:] = 1.0 / np.asarray(cloth_mass, float)
        self.inv_mass.assign(inv)
        a = lambda arr, t, dt=np.float32: wp.array(np.ascontiguousarray(arr, dt), dtype=t, device=device)
        self.nc = len(cloth_x)
        self.pairs = a(np.asarray(pairs) + self.c0, wp.vec2i, np.int32)
        self.rest_len, self.compliance = a(rest, float), a(compliance, float)
        self.cloth_thick, self.cloth_mu = a(cloth_thick, float), a(cloth_mu, float)
        self.cloth_passes = cloth_passes
        self.sn, self.sw = a(sn, wp.vec4i, np.int32), a(sw, wp.vec4)
        self.sub_rest = a(sub_rest, wp.vec3)
        self.ns = len(sn)
        self.sx = wp.zeros(self.ns, dtype=wp.vec3, device=device)
        self.sx_prev = wp.zeros(self.ns, dtype=wp.vec3, device=device)
        tris = np.asarray(tris, np.int32)
        self.tris = a(tris, wp.vec3i, np.int32)
        self.skin_thick, self.far_rest = float(skin_thick), float(far_rest)
        self.dxc = wp.zeros(self.n, dtype=wp.vec3, device=device)
        self.cnt = wp.zeros(self.n, dtype=float, device=device)
        self.cloth_depth = wp.zeros(self.nc, dtype=float, device=device)
        self.skin_depth = wp.zeros(self.ns, dtype=float, device=device)
        wp.launch(_skin_points, self.ns, [self.x, self.x_prev, self.sn, self.sw, self.sx, self.sx_prev], device=device)
        # one mesh of the whole skin for the cloth; per part, one of the skin of every other part (its triangles, with the
        # skin's vertex indices: the points are shared), whose own triangle list the query's face indexes
        self.body_mesh = wp.Mesh(points=self.sx, indices=a(tris.ravel(), int, np.int32))
        part, vertex_part = np.asarray(part), np.asarray(vertex_part)
        self.part_meshes = []
        for p in np.unique(vertex_part):
            others = tris[part != p]
            ids = np.flatnonzero(vertex_part == p).astype(np.int32)
            self.part_meshes.append((wp.Mesh(points=self.sx, indices=a(others.ravel(), int, np.int32)), a(ids, int, np.int32),
                                     a(others, wp.vec3i, np.int32)))
        self.orient = 1.0
        self.max_dist = 0.05
        # the cloth as a mesh, for skin points that lay under it at rest (cloth_tris wound outward, covered: those points)
        self.cloth_mesh = None
        if cloth_tris is not None and covered is not None and len(covered):
            self.cloth_pts = a(cloth_x, wp.vec3)
            self.cloth_rest = a(cloth_x, wp.vec3)
            self.ctris = a(cloth_tris, wp.vec3i, np.int32)
            self.cloth_mesh = wp.Mesh(points=self.cloth_pts, indices=a(np.asarray(cloth_tris).ravel(), int, np.int32))
            self.covered = a(covered, int, np.int32)
            self.under_thick = float(np.median(cloth_thick))
            self.vpart = a(vertex_part, int, np.int32)
            self.ctri_part = a(cloth_tri_part, int, np.int32)

    def set_orientation(self):
        """The skin's triangles' winding: +1 if their normal points out. Cloth at rest lies outside the skin."""
        self.orient = 1.0
        self._cloth_contact_pass(1.0e-4, measure_only=True)
        d = self.cloth_depth.numpy()
        d = d[d < 0.99]
        self.orient = 1.0 if np.median(d) > 0 else -1.0
        return self.orient, float(np.median(d) * self.orient)

    def _cloth_contact_pass(self, h, measure_only=False):
        mu = wp.zeros(self.nc, dtype=float, device=self.device) if measure_only else self.cloth_mu
        thick = wp.full(self.nc, -1.0, dtype=float, device=self.device) if measure_only else self.cloth_thick
        wp.launch(_cloth_contact, self.nc, [self.body_mesh.id, self.x, self.x_prev, self.inv_mass, self.c0, self.sx, self.sx_prev, self.tris,
                                            self.sn, self.sw, self.orient, thick, mu, self.max_dist, self.dxc, self.cnt, self.cloth_depth],
                  device=self.device)
        if measure_only:
            self.dxc.zero_()
            self.cnt.zero_()

    def depths(self):
        """Signed distance now of every cloth vertex to the skin, and of every skin point to another part's skin (1.0: none near)."""
        wp.launch(_skin_points, self.ns, [self.x, self.x_prev, self.sn, self.sw, self.sx, self.sx_prev], device=self.device)
        self.body_mesh.refit()
        for mesh, ids, _ in self.part_meshes:
            mesh.refit()
        self._cloth_contact_pass(1.0, measure_only=True)
        for mesh, ids, others in self.part_meshes:
            wp.launch(_skin_contact, len(ids), [mesh.id, ids, self.x, self.inv_mass, self.sx, self.sub_rest, others, self.sn, self.sw,
                                                self.orient, -1.0, self.far_rest, self.max_dist, self.dxc, self.cnt, self.skin_depth], device=self.device)
        self.dxc.zero_()
        self.cnt.zero_()
        return self.cloth_depth.numpy().copy(), self.skin_depth.numpy().copy()

    def skin_now(self):
        wp.launch(_skin_points, self.ns, [self.x, self.x_prev, self.sn, self.sw, self.sx, self.sx_prev], device=self.device)
        return self.sx.numpy()

    def _substeps(self, h, substeps):
        from tissue_solver import _glue, _velocity_relative_nodes, GLUE_COMPLIANCE
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
            for _ in range(self.cloth_passes):
                wp.launch(_distance, len(self.rest_len), [self.x, self.inv_mass, self.pairs, self.rest_len, self.compliance, 1.0 / (h * h), self.dxc],
                          device=self.device)
                wp.launch(_count_pairs, len(self.rest_len), [self.pairs, self.cnt], device=self.device)
                wp.launch(_apply_mean, self.n, [self.x, self.dxc, self.cnt], device=self.device)
            wp.launch(_skin_points, self.ns, [self.x, self.x_prev, self.sn, self.sw, self.sx, self.sx_prev], device=self.device)
            self.body_mesh.refit()
            self._cloth_contact_pass(h)
            for mesh, ids, others in self.part_meshes:
                mesh.refit()
                wp.launch(_skin_contact, len(ids), [mesh.id, ids, self.x, self.inv_mass, self.sx, self.sub_rest, others, self.sn, self.sw,
                                                    self.orient, self.skin_thick, self.far_rest, self.max_dist, self.dxc, self.cnt, self.skin_depth],
                          device=self.device)
            if self.cloth_mesh is not None:
                wp.launch(_copy_cloth, self.nc, [self.x, self.c0, self.cloth_pts], device=self.device)
                self.cloth_mesh.refit()
                wp.launch(_skin_under_cloth, len(self.covered), [self.cloth_mesh.id, self.covered, self.x, self.inv_mass, self.c0, self.sx, self.sn, self.sw,
                                                                 self.ctris, self.sub_rest, self.cloth_rest, 0.02, self.vpart, self.ctri_part,
                                                                 self.under_thick, 0.02,
                                                                 self.dxc, self.cnt], device=self.device)
            wp.launch(_apply_mean, self.n, [self.x, self.dxc, self.cnt], device=self.device)
            wp.launch(_velocity_relative_nodes, self.n, [self.x, self.x_prev, self.v, self.inv_mass, self.all_rest, self.node_bone, self.T0, self.T1,
                                                         self.frame, h, self.node_damping], device=self.device)


@wp.kernel
def _count_pairs(pair: wp.array(dtype=wp.vec2i), cnt: wp.array(dtype=float)):
    e = wp.tid()
    wp.atomic_add(cnt, pair[e][0], 1.0)
    wp.atomic_add(cnt, pair[e][1], 1.0)

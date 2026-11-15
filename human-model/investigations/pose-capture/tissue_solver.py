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


# --- Contact between parts (Rafael, 2026-11-14; design 10_desenho_tecidos.html, "Contato entre superfícies") ---------------------
# Each part (trunk, arms, legs; tissue_mesh.py PARTS) is its own volume. A node on one part's surface that goes inside another
# part's surface, or a hand's, is pushed back out by its share (its inverse mass against the face's); the face's nodes take the
# rest when they are tested against this part. A hand or a driven (rigid) face doesn't yield; the tissue spreads the rest. The skin may be pushed in only so far: each frame, how far the skeleton alone
# carries one surface into the other is measured (the nodes moved rigidly with their bones); past `yield_m` (cede_mm, Rafael:
# 5 mm) that much is allowed to stay inside, so the overlap shows and is counted, as skeleton error, instead of being hidden.

@wp.kernel
def _gather(x: wp.array(dtype=wp.vec3), ids: wp.array(dtype=int), out: wp.array(dtype=wp.vec3)):
    i = wp.tid()
    out[i] = x[ids[i]]


@wp.kernel
def _carried(rest: wp.array(dtype=wp.vec3), bone: wp.array(dtype=int), T1: wp.array(dtype=wp.mat44), out: wp.array(dtype=wp.vec3)):
    i = wp.tid()
    out[i] = wp.transform_point(T1[bone[i]], rest[i])


@wp.kernel
def _lerp(a: wp.array(dtype=wp.vec3), b: wp.array(dtype=wp.vec3), t: float, out: wp.array(dtype=wp.vec3)):
    i = wp.tid()
    out[i] = a[i] * (1.0 - t) + b[i] * t


@wp.func
def _depth_in(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), tri: wp.array(dtype=wp.vec3i), off: int, p: wp.vec3, max_dist: float):
    """How far p is behind the mesh's closest face (positive: inside) and how far it is from it; -1e9 and max_dist if none in reach."""
    q = wp.mesh_query_point_no_sign(mesh, p, max_dist)
    depth = float(-1.0e9)
    dist = float(max_dist)
    if q.result:
        t = tri[off + q.face]
        a = pts[t[0]]
        b = pts[t[1]]
        c = pts[t[2]]
        n = wp.cross(b - a, c - a)
        ln = wp.length(n)
        if ln > 1.0e-12:
            n = n / ln
            cp = a * q.u + b * q.v + c * (1.0 - q.u - q.v)
            dist = wp.length(cp - p)
            depth = wp.dot(cp - p, n)
            if depth < 0.5 * dist:
                depth = float(-1.0e9)  # beside an edge, not under the face: not inside
    return wp.vec2(depth, dist)


@wp.kernel
def _measure(meshes: wp.array(dtype=wp.uint64), n_mesh: int, mesh_pts_x: wp.array(dtype=wp.vec3), mesh_pts_h: wp.array(dtype=wp.vec3),
             tri_local: wp.array(dtype=wp.vec3i), tri_off: wp.array(dtype=int), kinematic: wp.array(dtype=int),
             q_pos: wp.array(dtype=wp.vec3), q_ids: wp.array(dtype=int), q_part: wp.array(dtype=int), skip: wp.array2d(dtype=int),
             max_dist: float, depth_out: wp.array(dtype=float), which: wp.array(dtype=int), near: wp.array(dtype=float)):
    """Per query node: the deepest it is inside any other part's (or hand's) surface, which, and how near the nearest one is."""
    i = wp.tid()
    p = q_pos[q_ids[i]]
    best = float(0.0)
    bm = int(-1)
    nd = float(max_dist)
    for m in range(n_mesh):
        if skip[q_part[i], m] == 0:
            r = wp.vec2()
            if kinematic[m] == 1:
                r = _depth_in(meshes[m], mesh_pts_h, tri_local, tri_off[m], p, max_dist)
            else:
                r = _depth_in(meshes[m], mesh_pts_x, tri_local, tri_off[m], p, max_dist)
            if r[0] > best:
                best = r[0]
                bm = m
            nd = wp.min(nd, r[1])
    depth_out[i] = best
    which[i] = bm
    near[i] = nd


@wp.kernel
def _contact(meshes: wp.array(dtype=wp.uint64), n_mesh: int, x: wp.array(dtype=wp.vec3), hand_x: wp.array(dtype=wp.vec3),
             tri_local: wp.array(dtype=wp.vec3i), tri_global: wp.array(dtype=wp.vec3i), tri_off: wp.array(dtype=int),
             kinematic: wp.array(dtype=int), q_ids: wp.array(dtype=int), q_part: wp.array(dtype=int), skip: wp.array2d(dtype=int),
             allowed: wp.array(dtype=float), inv_mass: wp.array(dtype=float), max_dist: float, near: wp.array(dtype=float),
             near_m: float, max_push: float, dx: wp.array(dtype=wp.vec3), cnt: wp.array(dtype=float), stats: wp.array(dtype=float)):
    i = wp.tid()
    if near[i] > near_m:
        return  # nothing of another part within near_m of it this frame
    node = q_ids[i]
    p = x[node]
    reach = max_dist  # searching only near_m past the allowed depth left nodes that had gone deeper inside for good
    for m in range(n_mesh):
        if skip[q_part[i], m] == 0:
            q = wp.mesh_query_point_no_sign(meshes[m], p, reach)
            if q.result:
                tg = tri_global[tri_off[m] + q.face]
                a = wp.vec3()
                b = wp.vec3()
                c = wp.vec3()
                if kinematic[m] == 1:
                    tl = tri_local[tri_off[m] + q.face]
                    a = hand_x[tl[0]]
                    b = hand_x[tl[1]]
                    c = hand_x[tl[2]]
                else:
                    a = x[tg[0]]
                    b = x[tg[1]]
                    c = x[tg[2]]
                n = wp.cross(b - a, c - a)
                ln = wp.length(n)
                if ln > 1.0e-12:
                    n = n / ln
                    w0 = q.u
                    w1 = q.v
                    w2 = 1.0 - q.u - q.v
                    cp = a * w0 + b * w1 + c * w2
                    dep = wp.dot(cp - p, n)
                    excess = wp.min(dep - allowed[i], max_push)  # a few mm at once turned into metres per second
                    if excess > 0.0 and dep >= 0.5 * wp.length(cp - p):
                        # only the node moves, by its share against the face's (mass-averaged): the face's own nodes are pushed
                        # when they are tested against this part in turn, so both sides yield. Moving the face's three nodes
                        # by their barycentric weights multiplied a push by up to 1/weight and threw a node 215 m at the groin
                        # (teste_contato_v18_preestab, frame 18)
                        wn = inv_mass[node]
                        wf = float(0.0)
                        if kinematic[m] == 0:
                            wf = w0 * inv_mass[tg[0]] + w1 * inv_mass[tg[1]] + w2 * inv_mass[tg[2]]
                        if wn > 0.0:
                            wp.atomic_add(dx, node, n * (excess * wn / (wn + wf)))
                            wp.atomic_add(cnt, node, 1.0)
                            wp.atomic_add(stats, 0, 1.0)
                            wp.atomic_add(stats, 1, excess * wn / (wn + wf))


@wp.kernel
def _apply_contact(x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), dx: wp.array(dtype=wp.vec3), cnt: wp.array(dtype=float)):
    """The push moves the previous position too, so it separates the surfaces without throwing them apart (Macklin et al. 2014,
    "Unified Particle Physics", pre-stabilization). Pushes turned into velocity pumped energy into the groin as the thigh flexed
    against the belly, until the tissue blew up at frame 18 (sim teste_contato_v18)."""
    i = wp.tid()
    if cnt[i] > 0.0:
        x[i] = x[i] + dx[i] / cnt[i]
        x_prev[i] = x_prev[i] + dx[i] / cnt[i]
    dx[i] = wp.vec3(0.0, 0.0, 0.0)
    cnt[i] = 0.0


class ContactSolver(GradedSolver):
    """GradedSolver plus contact between parts and against the hands. coll_tris (global node ids, outward) and coll_part give each
    part's surfaces, coll_nodes/node_part the nodes that collide; hand_tris index hand points set per frame by set_hands.
    skip_pairs: (part, mesh) pairs not tested (a hand against its own arm, which it joins at the wrist)."""

    def __init__(self, *args, coll_tris, coll_part, coll_nodes, node_part, hand_tris, hand_part, n_hand, yield_m=0.005,
                 every=1, max_dist=0.05, near_m=0.03, max_push=0.005, skip_pairs=(), **kw):
        super().__init__(*args, **kw)
        dev = self.device
        self.yield_m, self.every, self.max_dist, self.near_m, self.max_push = yield_m, every, max_dist, near_m, max_push
        meshes, tri_local, tri_global, offs, kin, self._mesh_pts, self._mesh_ids = [], [], [], [], [], [], []
        off = 0
        parts = sorted(set(np.asarray(coll_part).tolist()))
        self.mesh_parts = []
        for p in parts:
            t = np.asarray(coll_tris)[np.asarray(coll_part) == p]
            ids, local = np.unique(t, return_inverse=True)
            pts = wp.array(np.asarray(self.x.numpy()[ids]), dtype=wp.vec3, device=dev)
            idx = wp.array(local.astype(np.int32).ravel(), dtype=int, device=dev)
            meshes.append(wp.Mesh(points=pts, indices=idx))
            self._mesh_pts.append(pts)
            self._mesh_ids.append(wp.array(ids.astype(np.int32), dtype=int, device=dev))
            tri_local.append(local.reshape(-1, 3))
            tri_global.append(t)
            offs.append(off)
            off += len(t)
            kin.append(0)
            self.mesh_parts.append(int(p))
        self.hand_x0 = wp.zeros(n_hand, dtype=wp.vec3, device=dev)
        self.hand_x1 = wp.zeros(n_hand, dtype=wp.vec3, device=dev)
        self.hand_x = wp.zeros(n_hand, dtype=wp.vec3, device=dev)
        self.hand_meshes = []
        for p in sorted(set(np.asarray(hand_part).tolist())):
            t = np.asarray(hand_tris)[np.isin(np.asarray(hand_tris)[:, 0], np.flatnonzero(np.asarray(hand_part) == p))]
            idx = wp.array(t.astype(np.int32).ravel(), dtype=int, device=dev)
            m = wp.Mesh(points=self.hand_x, indices=idx)
            meshes.append(m)
            self.hand_meshes.append(m)
            tri_local.append(t)
            tri_global.append(np.full_like(t, -1))
            offs.append(off)
            off += len(t)
            kin.append(1)
            self.mesh_parts.append(int(p))
        self._meshes = meshes
        self.n_mesh = len(meshes)
        self.mesh_arr = wp.array(np.array([m.id for m in meshes], np.uint64), dtype=wp.uint64, device=dev)
        # a single points array for _measure's lookups: every part mesh's points laid end to end; tri_local offset to match
        self._flat_base = np.concatenate([[0], np.cumsum([len(a) for a in self._mesh_pts])])
        tl = [tri_local[k] + (self._flat_base[k] if kin[k] == 0 else 0) for k in range(len(meshes))]
        self.tri_local = wp.array(np.concatenate(tl).astype(np.int32), dtype=wp.vec3i, device=dev)
        self.tri_global = wp.array(np.concatenate(tri_global).astype(np.int32), dtype=wp.vec3i, device=dev)
        self.tri_off = wp.array(np.array(offs, np.int32), dtype=int, device=dev)
        self.kinematic = wp.array(np.array(kin, np.int32), dtype=int, device=dev)
        self.flat_pts = wp.zeros(int(self._flat_base[-1]), dtype=wp.vec3, device=dev)
        n_parts = 8
        skip = np.zeros((n_parts, self.n_mesh), np.int32)
        for k, p in enumerate(self.mesh_parts):
            skip[p, k] = 1  # never against its own part
            for a, b in skip_pairs:
                if b == p:
                    skip[a, k] = 1
        self.skip = wp.array(skip, dtype=int, device=dev)
        qn = np.asarray(coll_nodes, np.int32)
        self.q_ids = wp.array(qn, dtype=int, device=dev)
        self.q_part = wp.array(np.asarray(node_part)[qn].astype(np.int32), dtype=int, device=dev)
        self.nq = len(qn)
        self.allowed = wp.zeros(self.nq, dtype=float, device=dev)
        self.base = wp.zeros(self.nq, dtype=float, device=dev)  # how deep each node already reads inside at the build pose
        self.near = wp.zeros(self.nq, dtype=float, device=dev)
        self.near_now = wp.zeros(self.nq, dtype=float, device=dev)
        self.stats = wp.zeros(2, dtype=float, device=dev)  # pushes and their total (m), since the last take_stats
        self.now_depth = wp.zeros(self.nq, dtype=float, device=dev)
        self.now_which = wp.zeros(self.nq, dtype=int, device=dev)
        self.skel_depth = wp.zeros(self.nq, dtype=float, device=dev)
        self.skel_which = wp.zeros(self.nq, dtype=int, device=dev)
        self.cnt = wp.zeros(self.n, dtype=float, device=dev)
        self.xc = wp.zeros(self.n, dtype=wp.vec3, device=dev)

    def set_hands(self, start, end):
        """The hands' points at the start and the end of the next frame."""
        self.hand_x0.assign(np.asarray(start, np.float32))
        self.hand_x1.assign(np.asarray(end, np.float32))

    def _refit(self, src):
        for k, pts in enumerate(self._mesh_pts):
            wp.launch(_gather, len(pts), [src, self._mesh_ids[k], pts], device=self.device)
            self._meshes[k].refit()
            wp.copy(self.flat_pts, pts, dest_offset=int(self._flat_base[k]), count=len(pts))

    def _skeleton_overlap(self):
        """Once per frame: the surfaces as their bones alone carry them; how deep each node goes into another part there.
        allowed = what is past the skin's yield, left inside."""
        wp.launch(_carried, self.n, [self.all_rest, self.node_bone, self.T1, self.xc], device=self.device)
        wp.launch(_lerp, len(self.hand_x), [self.hand_x0, self.hand_x1, 1.0, self.hand_x], device=self.device)
        self._refit(self.xc)
        for m in self.hand_meshes:
            m.refit()
        wp.launch(_measure, self.nq, [self.mesh_arr, self.n_mesh, self.flat_pts, self.hand_x, self.tri_local, self.tri_off, self.kinematic,
                                      self.xc, self.q_ids, self.q_part, self.skip, self.max_dist, self.skel_depth, self.skel_which, self.near],
                  device=self.device)
        wp.launch(_allowed, self.nq, [self.skel_depth, self.base, self.yield_m, self.allowed], device=self.device)
        # near is taken from where the tissue is now, too: it swings 25-60 mm from where its bone carries it, and a node that went
        # inside another part while its bone kept it clear was never tested (contact resolved nothing, teste_resolvido_com)
        self._refit(self.x)
        wp.launch(_measure, self.nq, [self.mesh_arr, self.n_mesh, self.flat_pts, self.hand_x, self.tri_local, self.tri_off, self.kinematic,
                                      self.x, self.q_ids, self.q_part, self.skip, self.max_dist, self.now_depth, self.now_which, self.near_now],
                  device=self.device)
        wp.launch(_min, self.nq, [self.near, self.near_now], device=self.device)
        self.active = None

    def take_stats(self):
        v = self.stats.numpy().copy()
        self.stats.zero_()
        return {"pushes": int(v[0]), "pushed_total_m": round(float(v[1]), 3)}

    def set_base(self, depth):
        """What reads as inside at the build pose is the mesh's rest (the voxel staircase where two parts meet), not an overlap."""
        self.base.assign(np.asarray(depth, np.float32))

    def overlap_now(self):
        """After a frame: how deep each colliding node is inside another surface now (the overlap left), and which surface."""
        self._refit(self.x)
        for m in self.hand_meshes:
            m.refit()
        d = wp.zeros(self.nq, dtype=float, device=self.device)
        w = wp.zeros(self.nq, dtype=int, device=self.device)
        nr = wp.zeros(self.nq, dtype=float, device=self.device)
        wp.launch(_measure, self.nq, [self.mesh_arr, self.n_mesh, self.flat_pts, self.hand_x, self.tri_local, self.tri_off, self.kinematic,
                                      self.x, self.q_ids, self.q_part, self.skip, self.max_dist, d, w, nr], device=self.device)
        return d.numpy(), w.numpy(), self.skel_depth.numpy(), self.skel_which.numpy()

    def _substeps(self, h, substeps):
        self._skeleton_overlap()
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
            if (k + 1) % self.every == 0:
                wp.launch(_lerp, len(self.hand_x), [self.hand_x0, self.hand_x1, (k + 1) / substeps, self.hand_x], device=self.device)
                for m in self.hand_meshes:
                    m.refit()
                for kk, pts in enumerate(self._mesh_pts):
                    wp.launch(_gather, len(pts), [self.x, self._mesh_ids[kk], pts], device=self.device)
                    self._meshes[kk].refit()
                wp.launch(_contact, self.nq, [self.mesh_arr, self.n_mesh, self.x, self.hand_x, self.tri_local, self.tri_global, self.tri_off,
                                              self.kinematic, self.q_ids, self.q_part, self.skip, self.allowed, self.inv_mass, self.max_dist,
                                              self.near, self.near_m, self.max_push, self.dx, self.cnt, self.stats], device=self.device)
                wp.launch(_apply_contact, self.n, [self.x, self.x_prev, self.dx, self.cnt], device=self.device)
            wp.launch(_velocity_relative_nodes, self.n, [self.x, self.x_prev, self.v, self.inv_mass, self.all_rest, self.node_bone, self.T0, self.T1,
                                                         self.frame, h, self.node_damping], device=self.device)


@wp.kernel
def _min(a: wp.array(dtype=float), b: wp.array(dtype=float)):
    i = wp.tid()
    a[i] = wp.min(a[i], b[i])


@wp.kernel
def _allowed(depth: wp.array(dtype=float), base: wp.array(dtype=float), yield_m: float, out: wp.array(dtype=float)):
    i = wp.tid()
    out[i] = wp.max(base[i], depth[i] - yield_m)

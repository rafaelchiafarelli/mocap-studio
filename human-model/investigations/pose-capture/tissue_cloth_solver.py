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
- contact, cloth on cloth (Rafael, 2026-11-15: the cloth needs a thickness, 2 mm for top and jeans): a cloth vertex nearer than
  the two pieces' mean `espessura` to a cloth triangle is pushed off it, and the triangle back, on the side the vertex was on in the
  previous substep (so a push never completes a crossing). A triangle of the same piece that lay near the vertex at rest (its own
  neighbourhood, `far_rest_cloth`) is not contact; the other piece's always is (the top's hem rests on the waistband).
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
        depth[i] = wp.min(depth[i], d)
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
def _fill(a: wp.array(dtype=float), v: float):
    a[wp.tid()] = v


@wp.kernel
def _lerp_pts(a: wp.array(dtype=wp.vec3), b: wp.array(dtype=wp.vec3), t: float, out: wp.array(dtype=wp.vec3)):
    i = wp.tid()
    out[i] = a[i] * (1.0 - t) + b[i] * t


@wp.kernel
def _out_of_hand(mesh: wp.uint64, pts: wp.array(dtype=wp.vec3), hand: wp.array(dtype=wp.vec3), htris: wp.array(dtype=wp.vec3i),
                 rest: wp.array(dtype=wp.vec3), hand_rest: wp.array(dtype=wp.vec3), far_rest: float, orient: float, thick: float,
                 max_dist: float, sn: wp.array(dtype=wp.vec4i), sw: wp.array(dtype=wp.vec4), skin: int, c0: int,
                 inv_mass: wp.array(dtype=float), dx: wp.array(dtype=wp.vec3), cnt: wp.array(dtype=float), inside: wp.array(dtype=float)):
    """A hand, moved by the skeleton, pushes skin points (skin = 1: through their tetrahedra) or cloth vertices (skin = 0) out to
    `thick` from its surface; the hand doesn't yield. Points that lay near the hand at rest (the wrist's skin, a long sleeve's cuff)
    are not contact."""
    i = wp.tid()
    p = pts[i]
    q = wp.mesh_query_point_no_sign(mesh, p, max_dist)
    if q.result:
        t = htris[q.face]
        u = q.u
        v = q.v
        rp = u * hand_rest[t[0]] + v * hand_rest[t[1]] + (1.0 - u - v) * hand_rest[t[2]]
        if wp.length(rest[i] - rp) < far_rest:
            return
        a = hand[t[0]]
        b = hand[t[1]]
        e = hand[t[2]]
        cp = u * a + v * b + (1.0 - u - v) * e
        nrm = wp.normalize(wp.cross(b - a, e - a)) * orient
        d = wp.dot(p - cp, nrm)
        if wp.abs(d) < FACING * wp.length(p - cp):
            return
        inside[i] = wp.min(inside[i], d)
        C = d - thick
        if C < 0.0:
            if skin == 1:
                nj = sn[i]
                wj = sw[i]
                W = float(0.0)
                for m in range(4):
                    W += wj[m] * wj[m] * inv_mass[nj[m]]
                if W > 0.0:
                    sc = -C / W
                    for m in range(4):
                        if wj[m] * inv_mass[nj[m]] > 0.0:
                            wp.atomic_add(dx, nj[m], nrm * (wj[m] * inv_mass[nj[m]] * sc))
                            wp.atomic_add(cnt, nj[m], 1.0)
            else:
                wp.atomic_add(dx, c0 + i, nrm * (-C))
                wp.atomic_add(cnt, c0 + i, 1.0)


@wp.kernel
def _drive_blend(x: wp.array(dtype=wp.vec3), ids: wp.array(dtype=int), bones: wp.array(dtype=wp.vec4i), w: wp.array(dtype=wp.vec4),
                 rest: wp.array(dtype=wp.vec3), T0: wp.array(dtype=wp.mat44), T1: wp.array(dtype=wp.mat44), a: float):
    """The nodes at the cuts (wrists, ankles, neck) follow the bones blended by the skin's weights, as Blender skins the hands,
    feet and head next to them: followed by one bone each, the simulated skin came apart from the hand when the wrist bent."""
    i = wp.tid()
    b = bones[i]
    ww = w[i]
    p = wp.vec3(0.0, 0.0, 0.0)
    for k in range(4):
        if ww[k] > 0.0:
            M = T0[b[k]] * (1.0 - a) + T1[b[k]] * a
            p = p + ww[k] * wp.transform_point(M, rest[i])
    x[ids[i]] = p


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


@wp.func
def _closest_bary(p: wp.vec3, a: wp.vec3, b: wp.vec3, c: wp.vec3):
    """Barycentric weights (of a, b, c) of the point of the triangle nearest p (Ericson, Real-Time Collision Detection, 5.1.5)."""
    ab = b - a
    ac = c - a
    ap = p - a
    d1 = wp.dot(ab, ap)
    d2 = wp.dot(ac, ap)
    out = wp.vec3(1.0, 0.0, 0.0)
    done = False
    if d1 <= 0.0 and d2 <= 0.0:
        done = True
    bp = p - b
    d3 = wp.dot(ab, bp)
    d4 = wp.dot(ac, bp)
    if not done and d3 >= 0.0 and d4 <= d3:
        out = wp.vec3(0.0, 1.0, 0.0)
        done = True
    vc = d1 * d4 - d3 * d2
    if not done and vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        out = wp.vec3(1.0 - v, v, 0.0)
        done = True
    cp = p - c
    d5 = wp.dot(ab, cp)
    d6 = wp.dot(ac, cp)
    if not done and d6 >= 0.0 and d5 <= d6:
        out = wp.vec3(0.0, 0.0, 1.0)
        done = True
    vb = d5 * d2 - d1 * d6
    if not done and vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        out = wp.vec3(1.0 - w, 0.0, w)
        done = True
    va = d3 * d6 - d5 * d4
    if not done and va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        out = wp.vec3(0.0, 1.0 - w, w)
        done = True
    if not done:
        den = 1.0 / (va + vb + vc)
        v = vb * den
        w = vc * den
        out = wp.vec3(1.0 - v - w, v, w)
    return out


@wp.kernel
def _cloth_cloth(mesh: wp.uint64, x: wp.array(dtype=wp.vec3), x_prev: wp.array(dtype=wp.vec3), inv_mass: wp.array(dtype=float), c0: int,
                 ctris: wp.array(dtype=wp.vec3i), cloth_rest: wp.array(dtype=wp.vec3), piece: wp.array(dtype=int),
                 thick: wp.array(dtype=float), far_rest: float, measure: int,
                 dx: wp.array(dtype=wp.vec3), cnt: wp.array(dtype=float), close: wp.array(dtype=float)):
    i = wp.tid()
    c = c0 + i
    p = x[c]
    r = thick[i] * 1.5
    close[i] = 1.0
    query = wp.mesh_query_aabb(mesh, p - wp.vec3(r, r, r), p + wp.vec3(r, r, r))
    f = int(0)
    while wp.mesh_query_aabb_next(query, f):
        t = ctris[f]
        if t[0] != i and t[1] != i and t[2] != i:
            a = x[c0 + t[0]]
            b = x[c0 + t[1]]
            e = x[c0 + t[2]]
            bc = _closest_bary(p, a, b, e)
            own = piece[t[0]] == piece[i]
            rp = bc[0] * cloth_rest[t[0]] + bc[1] * cloth_rest[t[1]] + bc[2] * cloth_rest[t[2]]
            if not own or wp.length(cloth_rest[i] - rp) >= far_rest:
                cp = bc[0] * a + bc[1] * b + bc[2] * e
                n = wp.cross(b - a, e - a)
                ln = wp.length(n)
                sep = 0.5 * (thick[i] + thick[t[0]])
                if ln > 1.0e-12 and wp.length(p - cp) < 1.5 * sep:
                    n = n / ln
                    # the side the vertex was on a substep ago
                    ap = x_prev[c0 + t[0]]
                    bpv = x_prev[c0 + t[1]]
                    epv = x_prev[c0 + t[2]]
                    cpp = bc[0] * ap + bc[1] * bpv + bc[2] * epv
                    side = wp.sign(wp.dot(x_prev[c] - cpp, n))
                    if side == 0.0:
                        side = wp.sign(wp.dot(p - cp, n))
                    if side == 0.0:
                        side = 1.0
                    d = wp.dot(p - cp, n) * side
                    close[i] = wp.min(close[i], d)
                    C = sep - d
                    if C > 0.0 and measure == 0:
                        W = inv_mass[c]
                        for k in range(3):
                            W += bc[k] * bc[k] * inv_mass[c0 + t[k]]
                        if W > 0.0:
                            s = C / W
                            wp.atomic_add(dx, c, n * (side * inv_mass[c] * s))
                            wp.atomic_add(cnt, c, 1.0)
                            for k in range(3):
                                if bc[k] > 0.0:
                                    wp.atomic_add(dx, c0 + t[k], -n * (side * bc[k] * inv_mass[c0 + t[k]] * s))
                                    wp.atomic_add(cnt, c0 + t[k], 1.0)


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
                 sn, sw, sub_rest, tris, part, vertex_part, skin_thick, far_rest, cloth_tris=None, covered=None, cloth_tri_part=None, cloth_passes=2,
                 cloth_piece=None, far_rest_cloth=0.0, hand_rest=None, hand_tris=None, hand_side=None,
                 cap_ids=None, cap_bones=None, cap_w=None, device="cuda:0"):
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
        # the cloth tests every part's skin, not only the nearest skin of the whole body: lying 2 mm over the belly, a cloth vertex
        # had the belly as its nearest skin, and a forearm coming down on it was never tested and went through (tet_v9)
        self.cloth_part_meshes = []
        for p in np.unique(part):
            own = tris[part == p]
            self.cloth_part_meshes.append((wp.Mesh(points=self.sx, indices=a(own.ravel(), int, np.int32)), a(own, wp.vec3i, np.int32)))
        self.orient = 1.0
        self.max_dist = 0.05
        # the cuts' nodes, blended like the skin next to them (_drive_blend)
        self.caps = None
        if cap_ids is not None and len(cap_ids):
            self.caps = (a(cap_ids, int, np.int32), a(cap_bones, wp.vec4i, np.int32), a(cap_w, wp.vec4),
                         a(np.asarray(nodes, float)[np.asarray(cap_ids)], wp.vec3))
        # hands: MPFB's skin under the hand and finger bones, moved by the skeleton (set_hands), pushing skin and cloth
        self.hands = []
        if hand_rest is not None and len(hand_rest):
            self.hand_x0 = a(hand_rest, wp.vec3)
            self.hand_x1 = a(hand_rest, wp.vec3)
            self.hand_x = a(hand_rest, wp.vec3)
            self.hand_rest = a(hand_rest, wp.vec3)
            for sd in np.unique(hand_side):
                ht = np.asarray(hand_tris)[np.asarray(hand_side)[np.asarray(hand_tris)[:, 0]] == sd]
                self.hands.append((wp.Mesh(points=self.hand_x, indices=a(ht.ravel(), int, np.int32)), a(ht, wp.vec3i, np.int32)))
            self.hand_cloth_thick = float(np.median(cloth_thick))
            self.skin_in_hand = wp.zeros(self.ns, dtype=float, device=device)
            self.cloth_in_hand = wp.zeros(self.nc, dtype=float, device=device)
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
        # cloth on cloth: each vertex's piece; off when cloth_piece is None
        self.cloth_cloth = cloth_piece is not None and cloth_tris is not None
        if self.cloth_cloth:
            if self.cloth_mesh is None:
                self.cloth_pts = a(cloth_x, wp.vec3)
                self.cloth_rest = a(cloth_x, wp.vec3)
                self.ctris = a(cloth_tris, wp.vec3i, np.int32)
                self.cloth_mesh = wp.Mesh(points=self.cloth_pts, indices=a(np.asarray(cloth_tris).ravel(), int, np.int32))
                self.covered = a(np.zeros(0), int, np.int32)
            self.cloth_piece = a(cloth_piece, int, np.int32)
            self.far_rest_cloth = float(far_rest_cloth)
            self.cloth_close = wp.zeros(self.nc, dtype=float, device=device)

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
        wp.launch(_fill, self.nc, [self.cloth_depth, 1.0], device=self.device)
        for mesh, ptris in self.cloth_part_meshes:
            mesh.refit()
            wp.launch(_cloth_contact, self.nc, [mesh.id, self.x, self.x_prev, self.inv_mass, self.c0, self.sx, self.sx_prev, ptris,
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

    def cloth_gaps(self):
        """Per cloth vertex, its smallest distance to another cloth triangle on its side (1.0: none within reach)."""
        if not self.cloth_cloth:
            return None
        wp.launch(_copy_cloth, self.nc, [self.x, self.c0, self.cloth_pts], device=self.device)
        self.cloth_mesh.refit()
        wp.launch(_cloth_cloth, self.nc, [self.cloth_mesh.id, self.x, self.x_prev, self.inv_mass, self.c0, self.ctris, self.cloth_rest, self.cloth_piece,
                                          self.cloth_thick, self.far_rest_cloth, 1, self.dxc, self.cnt, self.cloth_close], device=self.device)
        return self.cloth_close.numpy().copy()

    def set_hands(self, start, end):
        """The hands' points at the start and the end of the next frame."""
        if self.hands:
            self.hand_x0.assign(np.asarray(start, np.float32))
            self.hand_x1.assign(np.asarray(end, np.float32))

    def _hand_pass(self, t, push=True):
        if not self.hands:
            return
        wp.launch(_lerp_pts, len(self.hand_x), [self.hand_x0, self.hand_x1, t, self.hand_x], device=self.device)
        wp.launch(_fill, self.ns, [self.skin_in_hand, 1.0], device=self.device)
        wp.launch(_fill, self.nc, [self.cloth_in_hand, 1.0], device=self.device)
        th_skin = self.skin_thick if push else -1.0
        th_cloth = self.hand_cloth_thick if push else -1.0
        for mesh, ht in self.hands:
            mesh.refit()
            wp.launch(_out_of_hand, self.ns, [mesh.id, self.sx, self.hand_x, ht, self.sub_rest, self.hand_rest, self.far_rest, self.orient,
                                              th_skin, self.max_dist, self.sn, self.sw, 1, self.c0, self.inv_mass, self.dxc, self.cnt,
                                              self.skin_in_hand], device=self.device)
            if self.cloth_mesh is not None:
                wp.launch(_copy_cloth, self.nc, [self.x, self.c0, self.cloth_pts], device=self.device)
                wp.launch(_out_of_hand, self.nc, [mesh.id, self.cloth_pts, self.hand_x, ht, self.cloth_rest, self.hand_rest, self.far_rest,
                                                  self.orient, th_cloth, self.max_dist, self.sn, self.sw, 0, self.c0, self.inv_mass,
                                                  self.dxc, self.cnt, self.cloth_in_hand], device=self.device)
        if not push:
            self.dxc.zero_()
            self.cnt.zero_()

    def hand_depths(self):
        """Per skin point and per cloth vertex, the signed distance to the nearest hand (1.0: none near)."""
        if not self.hands:
            return None, None
        wp.launch(_skin_points, self.ns, [self.x, self.x_prev, self.sn, self.sw, self.sx, self.sx_prev], device=self.device)
        self._hand_pass(1.0, push=False)
        return self.skin_in_hand.numpy().copy(), self.cloth_in_hand.numpy().copy()

    def skin_now(self):
        wp.launch(_skin_points, self.ns, [self.x, self.x_prev, self.sn, self.sw, self.sx, self.sx_prev], device=self.device)
        return self.sx.numpy()

    def _substeps(self, h, substeps):
        from tissue_solver import _glue, _velocity_relative_nodes, GLUE_COMPLIANCE
        for k in range(substeps):
            wp.launch(xpbd._drive, len(self.drive_ids), [self.x, self.drive_ids, self.drive_rest, self.drive_bone, self.T0, self.T1, (k + 1) / substeps],
                      device=self.device)
            if self.caps is not None:
                wp.launch(_drive_blend, len(self.caps[0]), [self.x, *self.caps, self.T0, self.T1, (k + 1) / substeps], device=self.device)
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
                if len(self.covered):
                    wp.launch(_skin_under_cloth, len(self.covered), [self.cloth_mesh.id, self.covered, self.x, self.inv_mass, self.c0, self.sx, self.sn, self.sw,
                                                                     self.ctris, self.sub_rest, self.cloth_rest, 0.02, self.vpart, self.ctri_part,
                                                                     self.under_thick, 0.02,
                                                                     self.dxc, self.cnt], device=self.device)
                if self.cloth_cloth:
                    wp.launch(_cloth_cloth, self.nc, [self.cloth_mesh.id, self.x, self.x_prev, self.inv_mass, self.c0, self.ctris, self.cloth_rest,
                                                      self.cloth_piece, self.cloth_thick, self.far_rest_cloth, 0, self.dxc, self.cnt, self.cloth_close],
                                  device=self.device)
            self._hand_pass((k + 1) / substeps)
            wp.launch(_apply_mean, self.n, [self.x, self.dxc, self.cnt], device=self.device)
            wp.launch(_velocity_relative_nodes, self.n, [self.x, self.x_prev, self.v, self.inv_mass, self.all_rest, self.node_bone, self.T0, self.T1,
                                                         self.frame, h, self.node_damping], device=self.device)


@wp.kernel
def _count_pairs(pair: wp.array(dtype=wp.vec2i), cnt: wp.array(dtype=float)):
    e = wp.tid()
    wp.atomic_add(cnt, pair[e][0], 1.0)
    wp.atomic_add(cnt, pair[e][1], 1.0)

"""Step 17b: the tissue and the clothes simulated together, from the dressed body at rest to the captured dance.

    human-model/hm.sh --gpu python human-model/investigations/pose-capture/tissue_cloth_sim.py TECIDOS.npz OSSOS.npz ROUPA.npz ROUPAS.json OUT_DIR \
        [pecas=blusinha,jeans] [frames=N] [substeps=160] [ramp=30] [hold=15] [pano_pano=0] [corpo=CORPO_REPOUSO.npz]

TECIDOS.npz: tissue_mesh.py's, built at rest (no pose=). OSSOS.npz: tissue_motion_dump.py's. ROUPA.npz: dress_rest.py's, the
clothes fitted to the same rest body. ROUPAS.json: `solver_tetraedros` (fabric per piece and the contact values).
The body starts in MPFB's A pose, dressed; over `ramp` frames the bones turn to the dance's first frame (the arms come down, the
sleeve between arm and flank), it holds `hold` frames to settle, then the dance plays (tissue_sim.py's schedule). Writes, for the
dance's frames only: pele.pc2 (the shown skin), <piece>.pc2 per piece, and relatorio.json: time per frame; per 10 frames the
volume kept, inverted tetrahedra, cloth vertices inside the skin (and how deep), skin points inside another part's skin, and how
much the cloth's edges stretch; `sob_pano` (tronco, todos, nao): which skin points are kept under the cloth's triangles; the same at the end of the ramp and of the hold. A piece with `encolhimento_cos` has a tighter
waistband: edges within `cos_mm` of its top opening shrink by that instead.
Cloth on cloth (on unless pano_pano=0; Rafael, 2026-11-15): pieces and the cloth itself keep the pieces' `espessura_mm` apart
(2 mm for top and jeans); a piece's own triangles within `pano_pano_longe_em_repouso_mm` of a vertex at rest are its neighbourhood,
not contact. The report adds, per piece, the vertices nearer another cloth triangle than half the thickness.
Hands (corpo=, tissue_export.py's rest body; Rafael, 2026-11-15): the skin under MPFB's hand, palm and finger bones, moved by the
skeleton each frame (skinned by its weights), pushes the skin and the cloth out and doesn't yield. The cloth is tested against every
part's skin (trunk, each arm, each leg), not only the nearest skin of the body. The report adds skin points and cloth vertices
inside a hand.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE))
import warp as wp  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
from hmcore import xpbd  # noqa: E402
from tissue_sim import GROUPS, ramp_transforms, write_pc2  # noqa: E402
from tissue_cloth_solver import ClothTissueSolver  # noqa: E402

PARTS = ("tronco", "braco_E", "braco_D", "perna_E", "perna_D")  # left is +x


def cloth_pairs(tris):
    """Edges, and for each edge between two triangles the pair of vertices across it (bending)."""
    e = np.sort(np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]]), axis=1)
    opp = np.concatenate([tris[:, 2], tris[:, 0], tris[:, 1]])
    order = np.lexsort((e[:, 1], e[:, 0]))
    e, opp = e[order], opp[order]
    same = np.all(e[1:] == e[:-1], axis=1)
    bend = np.stack([opp[:-1][same], opp[1:][same]], axis=1)
    edges = np.unique(e, axis=0)
    return edges, bend


def boundary_loops(F):
    e = np.sort(np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]]), axis=1)
    u, c = np.unique(e, axis=0, return_counts=True)
    adj = {}
    for i, j in u[c == 1]:
        adj.setdefault(i, []).append(j)
        adj.setdefault(j, []).append(i)
    seen, loops = set(), []
    for s0 in adj:
        if s0 in seen:
            continue
        stack, comp = [s0], []
        while stack:
            v = stack.pop()
            if v not in seen:
                seen.add(v)
                comp.append(v)
                stack += adj[v]
        loops.append(np.array(comp))
    return loops


def main(tissue_npz, bones_npz, cloth_npz, params_json, out_dir, opts):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    o = {"frames": 0, "substeps": 160, "ramp": 30, "hold": 15, "pecas": "blusinha,jeans", "sob_pano": "tronco", "pano_pano": 1}
    for item in opts:
        k, v = item.split("=")
        o[k] = v if k in ("pecas", "sob_pano", "corpo") else int(v)
    o.setdefault("costura_rigida", 0)
    m, mo, cl = np.load(tissue_npz), np.load(bones_npz), np.load(cloth_npz)
    P = json.load(open(params_json, encoding="utf-8"))["solver_tetraedros"]
    assert int(m["pose_frame"]) < 1, "the mesh must be built at rest (tissue_mesh.py without pose=)"
    assert list(m["bone_names"]) == list(mo["bone_names"]), "bones differ between mesh and motion"
    T, fps = mo["T"], float(mo["fps"])
    if o["frames"]:
        T = T[: o["frames"]]
    nodes, tets = m["nodes"].astype(float), m["tets"]
    pieces = o["pecas"].split(",")
    sub_rest = m["sub_rest"].astype(float)

    # cloth: vertices, mass, edges and bending pairs, per piece
    xs, mass, pairs, rest, comp, damp, thick, mu, spans, piece_ids = [], [], [], [], [], [], [], [], {}, []
    ctris, vns, band_n = [], [], {}
    base = 0
    for name in pieces:
        q = P["pecas"][name]
        V, F = cl[f"{name}_verts"].astype(float), cl[f"{name}_tris"]
        area = 0.5 * np.linalg.norm(np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]), axis=1)
        mv = np.zeros(len(V))
        np.add.at(mv, F.ravel(), np.repeat(area * q["gramatura_g_m2"] / 1000 / 3, 3))
        edges, bend = cloth_pairs(F)
        # a tighter band at the opening that holds the piece (the jeans' waistband): edges with both ends in it shrink more
        band = np.zeros(len(V), bool)
        if "encolhimento_cos" in q:
            top = max(boundary_loops(F), key=lambda l: V[l, 2].mean())
            band = cKDTree(V[top]).query(V)[0] <= q["cos_mm"] / 1000
        for pr, k in ((edges, q["tracao_N_m"]), (bend, q["flexao_N_m"])):
            shrink = np.where(band[pr[:, 0]] & band[pr[:, 1]], 1 - q.get("encolhimento_cos", 0.0), 1 - q["encolhimento"])
            pairs.append(pr + base)
            rest.append(np.linalg.norm(V[pr[:, 0]] - V[pr[:, 1]], axis=1) * shrink)
            comp.append(np.full(len(pr), 1.0 / k))
        # wound so the normal points away from the body
        nrm = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]])
        out_dir = V[F].mean(axis=1) - sub_rest[cKDTree(sub_rest).query(V[F].mean(axis=1))[1]]
        Fo = F[:, [0, 2, 1]] if np.median(np.einsum("ij,ij->i", nrm, out_dir)) < 0 else F
        ctris.append(Fo + base)
        vn = np.zeros_like(V)
        np.add.at(vn, Fo.ravel(), np.repeat(np.cross(V[Fo[:, 1]] - V[Fo[:, 0]], V[Fo[:, 2]] - V[Fo[:, 0]]), 3, axis=0))
        vns.append(vn / (np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12))
        band_n[name] = int(band.sum())
        xs.append(V), mass.append(mv)
        damp.append(np.full(len(V), q["amortecimento_1_s"])), thick.append(np.full(len(V), q["espessura_mm"] / 1000))
        mu.append(np.full(len(V), q["atrito"]))
        spans[name] = (base, base + len(V), len(edges))
        piece_ids.append(np.full(len(V), len(piece_ids), np.int32))
        base += len(V)
    cloth_x = np.concatenate(xs)
    cloth_piece = np.concatenate(piece_ids)
    cloth_tris, cloth_vn = np.concatenate(ctris), np.concatenate(vns)
    # skin points under the cloth at rest: within 30 mm of a cloth vertex and on its inner side
    dist, near_c = cKDTree(cloth_x).query(sub_rest)
    # (or within 12 mm on the outer side: at rest the nipples' tips already came through between the cloth's vertices)
    under = (dist < 0.03) & ((np.einsum("ij,ij->i", sub_rest - cloth_x[near_c], cloth_vn[near_c]) < 0) | (dist < 0.012))
    covered = np.flatnonzero(under)

    # skin: points from their tetrahedra, triangles, parts
    st, sb = m["sub_tet"], m["sub_bary"].astype(float)
    sn = tets[st]
    q4 = m["sub_faces"]
    tris = np.concatenate([q4[:, [0, 1, 2]], q4[:, [0, 2, 3]]])
    tris = tris[(tris[:, 0] != tris[:, 1]) & (tris[:, 1] != tris[:, 2]) & (tris[:, 0] != tris[:, 2])]
    grp = np.array(GROUPS)[m["group"][st]]
    left = sub_rest[:, 0] > 0
    vpart = np.zeros(len(st), np.int32)
    arm, leg = np.isin(grp, ("braco", "antebraco")), np.isin(grp, ("coxa", "perna"))
    vpart[arm & left], vpart[arm & ~left], vpart[leg & left], vpart[leg & ~left] = 1, 2, 3, 4
    tpart = vpart[tris[:, 0]]
    if o["sob_pano"] == "tronco":
        # only the trunk's skin away from the armpits (5 cm from any arm point at rest): there the rule fought the sleeve (teste_5)
        far_arm = cKDTree(sub_rest[(vpart == 1) | (vpart == 2)]).query(sub_rest[covered])[0] > 0.05
        covered = covered[(vpart[covered] == 0) & far_arm]
    elif o["sob_pano"] == "nao":
        covered = covered[:0]

    # hands from the rest body: the vertices the hand, palm and finger bones carry (MPFB's rig names), and their triangles
    hand_rest = hand_w = hand_tris = hand_side = None
    if o.get("corpo"):
        e = np.load(o["corpo"])
        assert list(e["bone_names"]) == list(m["bone_names"]), "bones differ between the rest body and the mesh"
        W_all, skin_all, tris_all = e["weights"].astype(float), e["skin"].astype(float), e["tris"].astype(np.int64)
        names = list(e["bone_names"])
        hv_all, side_all = [], []
        for sd, suf in ((0, ".L"), (1, ".R")):
            cols = [i for i, nm in enumerate(names) if nm.endswith(suf) and nm.startswith(("hand.", "palm", "f_", "thumb"))]
            hv = np.flatnonzero(W_all[:, cols].sum(axis=1) > 0.5)
            hv_all.append(hv)
            side_all.append(np.full(len(hv), sd))
        hv = np.concatenate(hv_all)
        hand_side = np.concatenate(side_all)
        local = -np.ones(len(skin_all), np.int64)
        local[hv] = np.arange(len(hv))
        keep = (local[tris_all] >= 0).all(axis=1)
        hand_tris = local[tris_all[keep]]
        hand_tris = hand_tris[hand_side[hand_tris[:, 0]] == hand_side[hand_tris[:, 1]]]
        hand_rest, hand_w = skin_all[hv], W_all[hv]
        print(f"hands: {len(hv)} vertices, {len(hand_tris)} triangles", flush=True)

    # the cuts' driven nodes (not those of rigid tetrahedra): blended by the weights of the rest skin nearest them (4, by inverse
    # distance), as Blender skins the hands, feet and head beside them; o["costura_rigida"]=1 keeps one bone each, for comparison
    cap_ids = cap_bones = cap_w = None
    if o.get("corpo") and not o.get("costura_rigida"):
        rigid_nodes = np.unique(tets[m["label"] == 3])
        caps = np.setdiff1d(m["driven"], rigid_nodes)
        dist_c, near_c = cKDTree(skin_all).query(nodes[caps], k=4)
        wv = np.einsum("nk,nkb->nb", 1 / np.maximum(dist_c, 1e-6), W_all[near_c])
        wv /= np.maximum(wv.sum(axis=1, keepdims=True), 1e-12)
        top = np.argsort(-wv, axis=1)[:, :4]
        cap_w = np.take_along_axis(wv, top, axis=1)
        cap_w /= np.maximum(cap_w.sum(axis=1, keepdims=True), 1e-12)
        cap_ids, cap_bones = caps, top
        drive_of = dict(zip(m["driven"].tolist(), m["drive_bone"].tolist()))
        cap_one = np.array([drive_of[c] for c in caps])
        print(f"cut nodes blended: {len(caps)}", flush=True)

    def seam_gap(Tf):
        """How far one bone each puts the cut's nodes from where the blend puts them (mm): the gap the old seam opened."""
        if cap_ids is None:
            return None
        x0 = nodes[cap_ids]
        one = np.einsum("nij,nj->ni", Tf[cap_one][:, :3, :3], x0) + Tf[cap_one][:, :3, 3]
        bl = sum(cap_w[:, k, None] * (np.einsum("nij,nj->ni", Tf[cap_bones[:, k]][:, :3, :3], x0) + Tf[cap_bones[:, k]][:, :3, 3]) for k in range(4))
        g = np.linalg.norm(one - bl, axis=1) * 1000
        return {"p95": round(float(np.percentile(g, 95)), 1), "max": round(float(g.max()), 1)}

    def hands_at(Tf):
        w = hand_w / np.maximum(hand_w.sum(axis=1, keepdims=True), 1e-9)
        out_ = np.zeros_like(hand_rest)
        for b in np.flatnonzero(w.any(axis=0)):
            sel = w[:, b] > 0
            out_[sel] += w[sel, b, None] * (hand_rest[sel] @ Tf[b, :3, :3].T + Tf[b, :3, 3])
        return out_

    # each cloth vertex's bone: that of the skin point nearest it
    near = cKDTree(sub_rest).query(cloth_x)[1]
    cloth_bone = m["node_bone"][sn[near, 0]]

    wp.init()
    t0 = time.time()
    solver = ClothTissueSolver(nodes, tets, m["colours"], m["density"], m["young"], m["poisson"], m["node_damping"],
                               m["emb_node"], m["emb_tets"], m["emb_w"],
                               cloth_x, np.concatenate(mass), np.concatenate(pairs), np.concatenate(rest), np.concatenate(comp),
                               np.concatenate(damp), np.concatenate(thick), np.concatenate(mu),
                               sn, sb, sub_rest, tris, tpart, vpart, P["pele_pele_mm"] / 1000, P["pele_pele_longe_em_repouso_mm"] / 1000,
                               cloth_tris=cloth_tris, covered=covered,
                               cloth_tri_part=vpart[cKDTree(sub_rest).query(cloth_x[cloth_tris].mean(axis=1))[1]],
                               cloth_piece=cloth_piece if o["pano_pano"] else None,
                               far_rest_cloth=P.get("pano_pano_longe_em_repouso_mm", 25.0) / 1000,
                               hand_rest=hand_rest, hand_tris=hand_tris, hand_side=hand_side,
                               cap_ids=cap_ids, cap_bones=cap_bones, cap_w=cap_w)
    all_rest = np.concatenate([nodes, cloth_x])
    all_bone = np.concatenate([m["node_bone"], cloth_bone])
    solver.drive(m["driven"], nodes[m["driven"]], all_rest=all_rest, bone=m["drive_bone"], all_bone=all_bone, n_bones=T.shape[1])
    orient, gap0 = solver.set_orientation()
    setup_s = time.time() - t0
    print(f"setup {setup_s:.1f} s; skin winding {orient:+.0f}; cloth's median gap at rest {gap0*1000:.1f} mm; skin points under cloth {len(covered)};"
          f" waistband vertices {band_n}", flush=True)

    pr_all, rest_all = np.concatenate(pairs), np.concatenate(rest)

    def measure(label, f, Tf=None):
        x = solver.positions().astype(float)
        cd, sd = solver.depths()
        v = xpbd.volumes(x[: solver.c0], solver.tets_host)
        row = {"quadro": label, "volume_kept_pct": round(float(v.sum() / solver.rest_total * 100), 2), "inverted_tets": int((v <= 0).sum()),
               "pele_dentro_de_outra_parte": int((sd < 0).sum()),
               "pele_mais_funda_mm": round(float(max(0.0, -sd.min())) * 1000, 1)}
        cx = x[solver.c0:]
        gaps = solver.cloth_gaps()
        sh, ch = solver.hand_depths()
        if Tf is not None and cap_ids is not None:
            row["costura_uma_vs_mistura_mm"] = seam_gap(Tf.astype(float))
        if sh is not None:
            row["pele_dentro_da_mao"] = int((sh < -0.001).sum())
            row["pele_dentro_da_mao_mm"] = round(float(max(0.0, -sh.min())) * 1000, 1)
            row["pano_dentro_da_mao"] = int((ch < -0.001).sum())
        for name in pieces:
            a, b, ne = spans[name]
            d = cd[a:b]
            e0 = int(sum(len(p) for p in pairs[: 2 * pieces.index(name)]))
            pe = pr_all[e0: e0 + ne]
            stretch = np.linalg.norm(cx[pe[:, 0]] - cx[pe[:, 1]], axis=1) / (rest_all[e0: e0 + ne] / (1 - P["pecas"][name]["encolhimento"]))
            row[name] = {"dentro_da_pele": int((d < 0).sum()), "mais_fundo_mm": round(float(max(0.0, -d.min())) * 1000, 1),
                         "esticado_p95_pct": round(float((np.percentile(stretch, 95) - 1) * 100), 1),
                         "esticado_max_pct": round(float((stretch.max() - 1) * 100), 1)}
            if gaps is not None:
                g = gaps[a:b]
                half = 0.5 * P["pecas"][name]["espessura_mm"] / 1000
                row[name]["pano_mais_perto_que_meia_espessura"] = int((g < half).sum())
                row[name]["pano_mais_perto_mm"] = round(float(g.min()) * 1000, 1)
        print(json.dumps(row, ensure_ascii=False), f"{f}", flush=True)
        return row

    report_frames = [measure("repouso", "-")]
    schedule = np.concatenate([ramp_transforms(T[0], o["ramp"]), np.repeat(T[:1], o["hold"], axis=0), T])
    first_dance = o["ramp"] + o["hold"]
    skins, cloths, times = [], {n: [] for n in pieces}, []
    prev = np.repeat(np.eye(4, dtype=np.float32)[None], T.shape[1], axis=0)
    hands_prev = hands_at(prev.astype(float)) if hand_rest is not None else None
    for f, cur in enumerate(schedule):
        solver.set_drive(prev, cur)
        if hand_rest is not None:
            hands_cur = hands_at(cur.astype(float))
            solver.set_hands(hands_prev, hands_cur)
            hands_prev = hands_cur
        wp.synchronize()
        s = time.time()
        solver.step(1.0 / fps, o["substeps"])
        wp.synchronize()
        times.append(time.time() - s)
        prev = cur
        if f == o["ramp"] - 1:
            report_frames.append(measure("fim_da_rampa", f"{times[-1]*1000:.0f} ms"))
        if f >= first_dance:
            skins.append(solver.skin_now().astype(np.float32))
            x = solver.positions()
            for name in pieces:
                a, b, _ = spans[name]
                cloths[name].append(x[solver.c0 + a: solver.c0 + b].astype(np.float32))
            k = f - first_dance + 1
            if k == 1 or k % 10 == 0 or f == len(schedule) - 1:
                report_frames.append(measure(k, f"{times[-1]*1000:.0f} ms", cur))
    write_pc2(out / "pele.pc2", skins, fps)
    for name in pieces:
        write_pc2(out / f"{name}.pc2", cloths[name], fps)
    rep = {"setup_s": round(setup_s, 1), "substeps": o["substeps"], "ramp": o["ramp"], "hold": o["hold"], "dance_frames": len(skins), "fps": fps,
           "pecas": pieces, "parametros": P, "ms_per_frame_median": round(float(np.median(times[2:]) * 1000), 1),
           "ms_per_frame_max": round(float(np.max(times[2:]) * 1000), 1), "frames": report_frames}
    (out / "relatorio.json").write_text(json.dumps(rep, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("frames", "parametros")}))


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(2)
    main(*sys.argv[1:6], sys.argv[6:])

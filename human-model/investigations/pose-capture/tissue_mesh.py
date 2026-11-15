"""Step 11b: the body's soft tissue as tetrahedra graded from the skin inward, with material per group (limb) and one fat volume
per breast. Design: review/2026-11-14/pose_capture/10_desenho_tecidos.html (agreed with Rafael, 2026-11-14).

    human-model/hm.sh --gpu python human-model/investigations/pose-capture/tissue_mesh.py REST.npz OUT_DIR [pose=OSSOS.npz:FRAME] [group.key=value ...]

With pose=, the body is built in that frame of the motion (tissue_motion_dump.py's), skinned from rest by its weights, instead
of MPFB's A pose; the simulation then moves it relative to that frame.

REST.npz is tissue_export.py's. OUT_DIR gets tecidos.npz (everything the simulation needs), tecidos.json (counts, volumes, the
values used) and cortes/*.png (sections, to check by eye).

How it is built:
1. The skin is cut at the neck (along the rig's head weights), wrists and ankles and capped (hmcore/body.py, layers.py). Head,
   hands and feet stay out and follow the skeleton.
2. Bands (tissue_groups.json mesh.bands_mm): each is a regular grid of its own voxel side, six tetrahedra per voxel, holding the
   voxels whose centre lies at that depth under the skin. A band reaches half a voxel into the band outside it, so the two overlap
   and no gap is left; the tetrahedra of the overlap count half (mass and stiffness), not to be counted twice.
3. The bands are glued: each node of a finer band's innermost layer is embedded in the coarser band's tetrahedron that holds it
   (barycentric weights; slightly outside, extrapolated), and the simulation holds it there (tissue_solver.py).
4. Labels, at each tetrahedron's centre: skin (the first `skin_mm`), fat (to the zone's fat thickness, body_fat_<sex>.json, by eye),
   muscle beneath. Rigid (driven by a rig bone): capsules along the limb bones, the spine, the rib cage below the pectoral and the
   pelvis core. Cavity: the belly's organs, under the abdominal wall. Breast: inside the skin and outside the same body with MPFB's
   least cup and the breast targets off, under a thin fat; one volume per side.
   Only voxels inside the skin: the skin's vertices are tied with weights a little outside their tetrahedron where needed.
5. Groups: the rig bone that moves the nearest skin vertex most, and the zone, give the limb: braco, antebraco, tronco, barriga,
   bumbum, coxa, perna; breasts and cavity are their own. Material per tetrahedron from its group and label.
6. The skin's vertices are tied to the finest band's tetrahedra, and so is the shown skin: MPFB's skin subdivided twice
   (tissue_export.py), the vertices nearest the cut skin, whole faces only; nodes of rigid tetrahedra and at the cut caps are driven by their
   bone; every node damps against the bone of its nearest driven node, the one it rests on.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))
import warp as wp  # noqa: E402
from hmcore import body as hb  # noqa: E402
from hmcore import layers, meshgpu  # noqa: E402

SKIN, FAT, MUSCLE, RIGID, CAVITY, BREAST = 0, 1, 2, 3, 4, 5
LABELS = ("pele", "gordura", "musculo", "rigido", "cavidade", "seio")
ARM_RADIUS_M = 0.07  # skin within this of the upper arm's axis, and past the shoulder joint, is arm (by eye)
ARM_PAST_JOINT_M = 0.02
GROUPS = ("braco", "antebraco", "tronco", "seio_E", "seio_D", "barriga", "cavidade", "bumbum", "coxa", "perna")
DATA = HERE.parent.parent / "data"


def load_config(overrides):
    cfg = json.loads((HERE / "tissue_groups.json").read_text(encoding="utf-8"))
    for item in overrides:
        if item.startswith("pose="):
            continue
        if item.startswith("densidade_neutra="):
            cfg["densidade_neutra"] = float(item.split("=")[1])
            continue
        name, value = item.split("=")
        group, key = name.split(".")
        cfg["groups"][group][key] = float(value)
    return cfg


def limb_of(name):
    for limb in ("upper_arm", "forearm", "thigh", "shin", "hand", "foot", "breast", "shoulder", "pelvis"):
        if name.startswith(limb + "."):
            return limb
    return "trunk" if name.startswith("spine") else "other"


def side_of(name):
    return "E" if name.endswith(".L") else "D" if name.endswith(".R") else ""


def skin_zones(skin, W, names, head, tail):
    """Per skin vertex: its dominant bone, the fat zone of body_fat_<sex>.json and the group (limb)."""
    dom = W.argmax(axis=1)
    bone = np.array(names)[dom]
    B = {n: i for i, n in enumerate(names)}
    z_hip = (head[B["thigh.L"], 2] + head[B["thigh.R"], 2]) / 2
    z_waist, z_ribs, z_neck = head[B["spine.001"], 2], head[B["spine.002"], 2] + 0.02, head[B["spine.004"], 2]
    zone = np.empty(len(skin), object)
    group = np.empty(len(skin), object)
    # arm or trunk by geometry, not by MPFB's weights: those give the upper arm much of the chest's side, which then had no rib
    # cage under it, sagged and was dragged by the arm into a groove down the flank (tecidos_v2, 2026-11-14)
    arm_side = {}
    for s in "LR":
        a, e = head[B[f"upper_arm.{s}"]], tail[B[f"upper_arm.{s}"]]
        u = (e - a) / np.linalg.norm(e - a)
        along = (skin - a) @ u
        arm_side[s] = (along > -ARM_PAST_JOINT_M) & (segment_distance(skin, a, e) < ARM_RADIUS_M)
    for i, (p, b) in enumerate(zip(skin, bone)):
        limb = limb_of(b)
        if limb in ("upper_arm", "shoulder", "trunk", "breast", "other", "pelvis"):
            s = "L" if p[0] > 0 else "R"
            if arm_side[s][i]:
                b, limb = f"upper_arm.{s}", "upper_arm"
            elif limb == "upper_arm":
                limb = "trunk"
        a, t = head[B[b]], tail[B[b]]
        off = p - (a + np.clip((p - a) @ (t - a) / max((t - a) @ (t - a), 1e-9), 0, 1) * (t - a))
        if limb == "upper_arm":
            zone[i], group[i] = ("upper_arm_front" if off[1] < 0 else "upper_arm_back"), "braco"
        elif limb in ("forearm", "hand"):
            zone[i], group[i] = "forearm", "antebraco"
        elif limb == "thigh":
            inner = off[0] * np.sign(a[0]) < 0
            zone[i] = ("thigh_front" if off[1] < 0 else "thigh_back") if abs(off[1]) > abs(off[0]) else ("thigh_inner" if inner else "thigh_outer")
            group[i] = "coxa"
        elif limb in ("shin", "foot"):
            zone[i] = "knee" if np.linalg.norm(p - a) < 0.06 else ("calf_front" if off[1] < 0 else "calf_back")
            group[i] = "perna"
        else:  # trunk, pelvis, shoulder, breast, neck, head
            ang = np.degrees(np.arctan2(abs(p[0]), -p[1]))  # 0 front, 180 back, about the body's midline
            front, back = ang < 55, ang > 125
            if p[2] > z_neck + 0.04:
                zone[i], group[i] = "neck", "tronco"
            elif p[2] < z_hip + 0.06:
                zone[i] = "buttocks" if back else ("belly" if front else "hips")
                group[i] = "barriga" if front else "bumbum"
            elif p[2] < z_ribs:
                zone[i] = "belly" if front else ("lower_back" if back else "flanks")
                group[i] = "tronco" if back else "barriga"
            else:
                zone[i] = "chest" if front else ("upper_back" if back else "flanks")
                group[i] = "tronco"
    return zone, group, bone


def segment_distance(points, a, b):
    d = b - a
    t = np.clip((points - a) @ d / max(d @ d, 1e-12), 0, 1)
    return np.linalg.norm(points - (a + t[:, None] * d), axis=1)


def band_grid(lo, hi, h, a, b, half_in, skin_q, closed_q, chunk_z=40):
    """Voxels of side h whose centre is at depth [a - half_in, b) under the skin, inside the body; the finest band also keeps the
    voxels just outside the skin, so every skin vertex lies in one. Done in slabs of z to bound memory."""
    origin = np.asarray(lo, float) - h
    shape = np.ceil((np.asarray(hi, float) + h - origin) / h).astype(int)
    keep, depth, inside_all = [], [], []
    for z0 in range(0, shape[2], chunk_z):
        z1 = min(shape[2], z0 + chunk_z)
        idx = np.indices((shape[0], shape[1], z1 - z0)).reshape(3, -1).T
        idx[:, 2] += z0
        c = origin + (idx + 0.5) * h
        d, _, _ = skin_q.closest(c)
        near = d < b + h
        if not near.any():
            continue
        idx, c, d = idx[near], c[near], d[near]
        inside = closed_q.inside(c)
        # inside voxels only: voxels just outside the skin, kept earlier so every skin vertex lay in one, bridged the arm to the
        # flank where the two nearly touch at rest, and the arm coming down dragged a groove down the flank (tecidos_v1, 2026-11-14).
        # The skin is tied with barycentric weights a little outside its tetrahedron instead (find_tets).
        sel = inside & (d >= (a - half_in if a > 0 else 0.0)) & (d < b)
        keep.append(idx[sel])
        depth.append(np.where(inside[sel], d[sel], -d[sel]))
    vox = np.concatenate(keep)
    mask = np.zeros(shape, bool)
    mask[tuple(vox.T)] = True
    return origin, shape, mask


def find_tets(points, origin, h, mask, nodes, tets, tet_voxel, vox):
    """For each point, the band's tetrahedron holding it (best of the 6 in its voxel, or of its included neighbours if its voxel
    isn't), with barycentric weights, possibly a little outside. -1 where nothing is near."""
    where = -np.ones(mask.shape, np.int64)
    where[tuple(vox.T)] = np.arange(len(vox))
    cell = np.floor((points - origin) / h).astype(int)
    best_t = -np.ones(len(points), np.int64)
    best_w = np.zeros((len(points), 4))
    score = np.full(len(points), -np.inf)
    offsets = [(0, 0, 0)] + [(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1) if (i, j, k) != (0, 0, 0)]
    for off in offsets:
        c = cell + np.array(off)
        ok = (c >= 0).all(1) & (c < np.array(mask.shape)).all(1)
        vi = -np.ones(len(points), np.int64)
        vi[ok] = where[tuple(c[ok].T)]
        has = vi >= 0
        if off != (0, 0, 0):
            has &= score < -1e-6  # neighbours only for points not already inside a tetrahedron
        if not has.any():
            continue
        for k in range(6):
            t = vi[has] * 6 + k
            w = layers.barycentric(points[has], nodes[tets[t]])
            s = w.min(axis=1)
            better = s > score[has]
            sel = np.flatnonzero(has)[better]
            best_t[sel], best_w[sel], score[sel] = t[better], w[better], s[better]
    return best_t, best_w, score


def lbs(points, weights, T):
    """Linear blend skinning in plain arrays: weights (n x bones), T (bones x 4 x 4)."""
    w = weights / np.maximum(weights.sum(axis=1, keepdims=True), 1e-9)
    out = np.zeros_like(points)
    for b in np.flatnonzero(w.any(axis=0)):
        sel = w[:, b] > 0
        out[sel] += w[sel, b, None] * (points[sel] @ T[b, :3, :3].T + T[b, :3, 3])
    return out


def main(rest_npz, out_dir, overrides):
    t_start = time.time()
    out = Path(out_dir)
    (out / "cortes").mkdir(parents=True, exist_ok=True)
    cfg = load_config(overrides)
    an = cfg["anatomy"]
    fat_mm = json.loads((DATA / "body_fat_female.json").read_text(encoding="utf-8"))["fat_mm"]
    e = np.load(rest_npz)
    skin, flat, tris = e["skin"].astype(float), e["flat"].astype(float), e["tris"].astype(np.int64)
    names, head, tail, W = list(e["bone_names"]), e["bone_head"].astype(float), e["bone_tail"].astype(float), e["weights"]
    # zones, groups and fat thickness are per skin vertex, so they are read at rest and carried to any pose
    zone, group_v, bone_v = skin_zones(skin, W, names, head, tail)
    head_r, tail_r = head.copy(), tail.copy()
    sv, sf = e["sub_verts"].astype(float), e["sub_faces"].astype(np.int64)
    pose = next((o[5:] for o in overrides if o.startswith("pose=")), None)
    T_rest = np.repeat(np.eye(4)[None], len(names), axis=0)
    pose_frame = None
    if pose:
        # built in a frame of the motion instead of MPFB's A pose: from the A pose, arms brought down to the sides folded the
        # armpit's and shoulder's tissue onto itself, which tetrahedra can't do: they turned inside out and opened grooves
        # down the flank (tecidos_v3, 2026-11-14)
        from scipy.spatial import cKDTree
        path, frame = pose.rsplit(":", 1)
        mo = np.load(path)
        assert list(mo["bone_names"]) == names, "bones differ between rest and motion"
        pose_frame = int(frame)
        T_rest = mo["T"][pose_frame - 1].astype(float)
        dist, near = cKDTree(skin).query(sv, k=4)
        wsub = np.einsum("vk,vkb->vb", 1 / np.maximum(dist, 1e-6), W[near]) 
        sv = lbs(sv, wsub, T_rest)
        skin, flat = lbs(skin, W, T_rest), lbs(flat, W, T_rest)
        head = np.einsum("bij,bj->bi", T_rest[:, :3, :3], head) + T_rest[:, :3, 3]
        tail = np.einsum("bij,bj->bi", T_rest[:, :3, :3], tail) + T_rest[:, :3, 3]
    B = {n: i for i, n in enumerate(names)}
    rig = {n: {"head": head[i].tolist(), "tail": tail[i].tolist(), "parent": str(e["bone_parent"][i]) or None} for i, n in enumerate(names)}
    groups_w = {n: [(int(v), float(W[v, i])) for v in np.flatnonzero(W[:, i] > 0)] for i, n in enumerate(names)}
    wp.init()

    # 1. cut and cap
    patch = hb.cut_skin(skin, tris, rig, groups_w)
    ids = np.unique(patch)
    closed_v, closed_t = layers.capped(skin, patch)
    flat_v, flat_t = layers.capped(flat, patch)
    thick = np.zeros(len(skin))
    thick[ids] = [fat_mm[z] / 1000 for z in zone[ids]]
    thick = hb.smooth_on_surface(thick, patch, len(skin), 10)
    skin_q, closed_q, flat_q = meshgpu.Mesh(skin, patch), meshgpu.Mesh(closed_v, closed_t), meshgpu.Mesh(flat_v, flat_t)
    lo, hi = skin[ids].min(axis=0), skin[ids].max(axis=0)

    # 2. bands
    bands = []
    spec = cfg["mesh"]["bands_mm"]
    node_base = 0
    for k, (h_mm, a_mm, b_mm) in enumerate(spec):
        h, a, b = h_mm / 1000, a_mm / 1000, b_mm / 1000
        origin, shape, mask = band_grid(lo, hi, h, a, b, h / 2, skin_q, closed_q)
        nodes, tets, tet_voxel, vox = layers.tetrahedra(mask, origin, h)
        bands.append(dict(h=h, a=a, b=b, origin=origin, shape=shape, mask=mask, nodes=nodes, tets=tets, tet_voxel=tet_voxel, vox=vox,
                          base=node_base))
        node_base += len(nodes)
        print(f"band {h_mm} mm: {len(vox)} voxels, {len(tets)} tetrahedra, {len(nodes)} nodes", flush=True)
    nodes = np.concatenate([bd["nodes"] for bd in bands])
    tets = np.concatenate([bd["tets"] + bd["base"] for bd in bands])
    tet_band = np.concatenate([np.full(len(bd["tets"]), k) for k, bd in enumerate(bands)])
    colours = np.concatenate([((bd["vox"][:, 0] % 2) * 4 + (bd["vox"][:, 1] % 2) * 2 + bd["vox"][:, 2] % 2)[bd["tet_voxel"]] * 6
                              + np.arange(len(bd["tets"])) % 6 for bd in bands]).astype(np.int32)

    # 3. glue: the innermost layer of each finer band embedded in the next band
    emb_node, emb_tets, emb_w = [], [], []
    glue_report = []
    for k in range(len(bands) - 1):
        f, c = bands[k], bands[k + 1]
        d, _, _ = skin_q.closest(f["nodes"])
        inner = np.flatnonzero(d >= c["a"] - f["h"] * 0.5 - 1e-6)
        t, w, s = find_tets(f["nodes"][inner], c["origin"], c["h"], c["mask"], c["nodes"], c["tets"], c["tet_voxel"], c["vox"])
        ok = t >= 0
        emb_node.append(inner[ok] + f["base"])
        emb_tets.append(c["tets"][t[ok]] + c["base"])
        emb_w.append(w[ok])
        glue_report.append({"from_mm": f["h"] * 1000, "to_mm": c["h"] * 1000, "nodes": int(len(inner)), "glued": int(ok.sum()),
                            "outside_by_more_than_10pct": int((s[ok] < -0.1).sum())})
    emb_node, emb_tets, emb_w = np.concatenate(emb_node), np.concatenate(emb_tets), np.concatenate(emb_w)

    # 4. labels and groups at each tetrahedron's centre
    cen = nodes[tets].mean(axis=1)
    # the trunk's rules (heights, front and back, left and right) are read at rest: each centre is carried back by the mid-trunk bone
    Tm = np.linalg.inv(T_rest[B["spine.002"]])
    cr = cen @ Tm[:3, :3].T + Tm[:3, 3]
    d, face, uv = skin_q.closest(cen)
    inside = closed_q.inside(cen)
    depth = np.where(inside, d, 0.0)
    fv = patch[face]
    bw = np.column_stack([uv[:, 0], uv[:, 1], 1 - uv[:, 0] - uv[:, 1]])
    near_v = fv[np.arange(len(fv)), bw.argmax(axis=1)]
    t_fat = np.einsum("ij,ij->i", bw, thick[fv])
    grp = group_v[near_v].astype(object)
    zone_t = zone[near_v]
    label = np.full(len(tets), MUSCLE, np.int8)
    label[depth < t_fat] = FAT
    # breasts: inside the skin, outside the breastless body, under a thin fat
    in_flat = flat_q.inside(cen)
    breast = inside & ~in_flat & (depth > an["breast_skin_fat_m"]) & np.isin(zone_t, ["chest", "flanks"])
    label[breast] = BREAST
    grp[breast] = np.where(cr[breast, 0] > 0, "seio_E", "seio_D")  # left and right at rest: posed, the body may face anywhere
    # cavity: belly, under fat and the abdominal wall, between pelvis and ribs, in front of the spine
    z_hip = (head_r[B["thigh.L"], 2] + head_r[B["thigh.R"], 2]) / 2
    z_ribs = head_r[B["spine.002"], 2] + 0.02
    spine_y = np.interp(cr[:, 2], [head_r[B["spine"], 2], head_r[B["spine.004"], 2]], [head_r[B["spine"], 1], head_r[B["spine.004"], 1]])
    cavity = (np.isin(grp, ["barriga", "tronco"]) & (depth > t_fat + an["abdominal_wall_m"]) & (cr[:, 2] > z_hip + 0.04)
              & (cr[:, 2] < z_ribs) & (cr[:, 1] < spine_y))
    label[cavity] = CAVITY
    grp[cavity] = "cavidade"
    # rigid: limb capsules, spine, rib cage, pelvis core
    rigid_bone = -np.ones(len(tets), np.int64)
    r = an["bone_radius_m"]
    for limb, radius in r.items():
        for s in ("L", "R") if limb != "spine" else ("",):
            bones = [f"{limb}.{s}"] if limb != "spine" else ["spine", "spine.001", "spine.002", "spine.003", "spine.004"]
            for bn in bones:
                i = B[bn]
                hit = segment_distance(cen, head[i], tail[i]) < radius
                rigid_bone[hit & (rigid_bone < 0)] = i
    chest = (np.isin(grp, ["tronco", "barriga"]) & ~breast & (cr[:, 2] >= z_ribs) & (cr[:, 2] < head_r[B["spine.004"], 2] + 0.03)
             & (depth > t_fat + an["pectoral_m"]))
    # the rib cage is one rigid piece on the chest bone: split between spine.002 and spine.003 it sheared along their border
    # as the trunk twisted, a crease across the back (tecidos_v4, 2026-11-14)
    rigid_bone[chest & (rigid_bone < 0)] = B["spine.003"]
    hips_x = abs(head_r[B["thigh.L"], 0]) + 0.03
    pelvis = (np.isin(grp, ["bumbum", "barriga", "tronco"]) & (cr[:, 2] > z_hip - an["pelvis_below_hip_m"]) & (cr[:, 2] < z_hip + 0.08)
              & (np.abs(cr[:, 0]) < hips_x) & (depth > t_fat + an["pelvis_tissue_m"]) & (cr[:, 1] > spine_y - 0.04) & ~cavity)
    rigid_bone[pelvis & (rigid_bone < 0)] = B["spine"]
    label[rigid_bone >= 0] = RIGID
    label[(depth < cfg["mesh"]["skin_mm"] / 1000) & (label != RIGID)] = SKIN

    # 5. material per tetrahedron
    weight = np.ones(len(tets))
    for k, bd in enumerate(bands):
        if k > 0:
            # where band k reaches into band k-1 (depth a - h/2 to a), both bands' tetrahedra count half, so the overlap counts
            # once. Until 2026-11-14 only the coarser half was halved: the overlap weighed and resisted 1.5 times (malha_v1 to v6)
            overlap = (depth >= bd["a"] - bd["h"] / 2) & (depth < bd["a"])
            weight[(tet_band == k) & overlap] = 0.5
            weight[(tet_band == k - 1) & overlap] = 0.5
    young, dens, pois, damp_t = np.zeros(len(tets)), np.zeros(len(tets)), np.zeros(len(tets)), np.zeros(len(tets))
    for g in GROUPS:
        sel = grp == g
        m = cfg["groups"][g]
        young[sel] = np.select([label[sel] == SKIN, (label[sel] == FAT) | (label[sel] == BREAST), label[sel] == CAVITY],
                               [m["skin_young"], m["fat_young"], m["fat_young"]], m["muscle_young"])
        dens[sel] = np.where(np.isin(label[sel], [FAT, BREAST, SKIN]), m["fat_density"], m["muscle_density"])
        pois[sel], damp_t[sel] = m["poisson"], m["damping"]
    if cfg.get("densidade_neutra"):
        dens[:] = float(cfg["densidade_neutra"])  # one density for all soft tissue (tissue_groups.json densidade_neutra)
    rigid = label == RIGID
    young[rigid], dens[rigid], pois[rigid] = 1e6, 1100.0, 0.3
    young *= weight
    dens *= weight

    # 6. skin ties, drives, damping bones
    b0 = bands[0]
    st, sw, ss = find_tets(skin[ids], b0["origin"], b0["h"], b0["mask"], b0["nodes"], b0["tets"], b0["tet_voxel"], b0["vox"])
    skin_untied = int((st < 0).sum())  # MPFB's own skin is only measured here; the shown skin is the subdivided one below
    # the subdivided skin (what is shown): its vertices nearest a vertex of the cut skin, whole faces only, tied the same way
    from scipy.spatial import cKDTree
    in_patch = np.zeros(len(skin), bool)
    in_patch[ids] = True
    _, nearest = cKDTree(skin).query(sv)
    keep_v = in_patch[nearest]
    sub_t, sub_w, sub_s = np.full(len(sv), -1), np.zeros((len(sv), 4)), np.full(len(sv), -np.inf)
    kv = np.flatnonzero(keep_v)
    sub_t[kv], sub_w[kv], sub_s[kv] = find_tets(sv[kv], b0["origin"], b0["h"], b0["mask"], b0["nodes"], b0["tets"], b0["tet_voxel"], b0["vox"])
    keep_v &= sub_t >= 0
    faces_ok = keep_v[sf].all(axis=1)
    used = np.unique(sf[faces_ok])
    remap = -np.ones(len(sv), np.int64)
    remap[used] = np.arange(len(used))
    sub_faces_local = remap[sf[faces_ok]]
    n = len(nodes)
    dn, dface, duv = skin_q.closest(nodes)
    nfv = patch[dface]
    node_v = nfv[np.arange(n), np.column_stack([duv[:, 0], duv[:, 1], 1 - duv.sum(1)]).argmax(axis=1)]
    node_bone = W[node_v].argmax(axis=1)
    drive_bone = -np.ones(n, np.int64)
    rt = tets[rigid]
    drive_bone[rt.ravel()] = np.repeat(rigid_bone[rigid], 4)
    planes = hb.cut_planes(skin, patch)
    for c0, nrm, rad in planes:
        at_cap = (np.abs((nodes - c0) @ nrm) < an["cap_drive_m"]) & (np.linalg.norm(nodes - c0, axis=1) < rad * 1.5)
        drive_bone[at_cap & (drive_bone < 0)] = node_bone[at_cap & (drive_bone < 0)]
    driven = np.flatnonzero(drive_bone >= 0)
    # each node damps against the bone it rests on: the nearest driven node's. MPFB's weights gave the flank to the upper arm,
    # and damping against the arm dragged the flank with it (tecidos_v1)
    from scipy.spatial import cKDTree as _Tree
    _, nearest_driven = _Tree(nodes[driven]).query(nodes)
    node_bone = drive_bone[driven][nearest_driven]
    node_damp = np.zeros(n)
    cnt = np.zeros(n)
    np.add.at(node_damp, tets.ravel(), np.repeat(damp_t, 4))
    np.add.at(cnt, tets.ravel(), 1)
    node_damp /= np.maximum(cnt, 1)

    vol = np.abs(np.einsum("ij,ij->i", np.cross(nodes[tets[:, 1]] - nodes[tets[:, 0]], nodes[tets[:, 2]] - nodes[tets[:, 0]]),
                           nodes[tets[:, 3]] - nodes[tets[:, 0]])) / 6 * weight
    np.savez_compressed(out / "tecidos.npz", nodes=nodes.astype(np.float32), tets=tets.astype(np.int32), colours=colours,
                        tet_band=tet_band.astype(np.int8), label=label, group=np.array([GROUPS.index(g) for g in grp], np.int8),
                        young=young.astype(np.float32), density=dens.astype(np.float32), poisson=pois.astype(np.float32),
                        node_damping=node_damp.astype(np.float32), weight=weight.astype(np.float32),
                        emb_node=emb_node.astype(np.int32), emb_tets=emb_tets.astype(np.int32), emb_w=emb_w.astype(np.float32),
                        skin_ids=ids.astype(np.int32), skin_tet=st.astype(np.int32), skin_bary=sw.astype(np.float32),
                        driven=driven.astype(np.int32), drive_bone=drive_bone[driven].astype(np.int32), node_bone=node_bone.astype(np.int32),
                        bone_names=np.array(names), patch=patch.astype(np.int32),
                        sub_ids=used.astype(np.int32), sub_faces=sub_faces_local.astype(np.int32), sub_rest=sv[used].astype(np.float32),
                        sub_tet=sub_t[used].astype(np.int32), sub_bary=sub_w[used].astype(np.float32),
                        T_rest=T_rest.astype(np.float32), pose_frame=-1 if pose_frame is None else pose_frame)
    report = {"seconds": round(time.time() - t_start, 1), "built_in_frame": pose_frame, "nodes": int(n), "tetrahedra": int(len(tets)),
              "per_band": [{"voxel_mm": bd["h"] * 1000, "tetrahedra": int(len(bd["tets"])), "nodes": int(len(bd["nodes"]))} for bd in bands],
              "glue": glue_report, "driven_nodes": int(len(driven)),
              "skin_vertices": int(len(ids)), "skin_tie_worst_min_bary": float(ss[st >= 0].min()), "skin_vertices_untied": skin_untied,
              "shown_skin_vertices": int(len(used)), "shown_skin_faces": int(faces_ok.sum()), "shown_tie_worst_min_bary": float(sub_s[used].min()),
              "volume_l": {LABELS[k]: round(float(vol[label == k].sum() * 1000), 2) for k in range(len(LABELS))},
              "volume_l_per_group": {g: round(float(vol[(grp == g) & (label != RIGID)].sum() * 1000), 2) for g in GROUPS},
              "breast_volume_ml": {s: round(float(vol[grp == f"seio_{s}"].sum() * 1e6)) for s in "ED"},
              "mass_kg_soft": round(float((vol * dens / np.maximum(weight, 1e-9))[label != RIGID].sum()), 1),
              "config": cfg}
    (out / "tecidos.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "config"}, indent=1, ensure_ascii=False))
    sections(out / "cortes", cr, label, grp, tet_band, bands, head_r, B)


def sections(folder, cen, label, grp, tet_band, bands, head, B):
    """Slices through the tetrahedra's centres, coloured by label and by band, as PNGs."""
    from PIL import Image, ImageDraw
    colors = {SKIN: (185, 120, 92), FAT: (240, 205, 110), MUSCLE: (205, 95, 85), RIGID: (200, 194, 174), CAVITY: (120, 150, 190), BREAST: (215, 100, 145)}
    band_c = [(140, 92, 194), (90, 150, 210), (90, 180, 120), (200, 160, 60)]
    cuts = {"coxa": head[B["thigh.L"], 2] - 0.18, "quadril": (head[B["thigh.L"], 2] + head[B["spine.001"], 2]) / 2,
            "barriga": head[B["spine.001"], 2] + 0.03, "peito": head[B["breast.L"], 2], "braco": head[B["upper_arm.L"], 2] - 0.12}
    px = 2000  # pixels per metre
    for name, z in cuts.items():
        sel = np.abs(cen[:, 2] - z) < 0.0015 + 0.004 * (tet_band > 0)
        if not sel.any():
            continue
        p = cen[sel]
        x0, y0 = p[:, 0].min() - 0.02, p[:, 1].min() - 0.02
        wid, hei = int((p[:, 0].max() - x0 + 0.02) * px), int((p[:, 1].max() - y0 + 0.02) * px)
        for what, col in (("rotulo", lambda i: colors[int(label[sel][i])]), ("faixa", lambda i: band_c[int(tet_band[sel][i])])):
            im = Image.new("RGB", (wid, hei), (250, 250, 247))
            dr = ImageDraw.Draw(im)
            order = np.argsort(-tet_band[sel])
            for i in order:
                u, v = (p[i, 0] - x0) * px, (p[i, 1] - y0) * px
                r = max(1.5, bands[int(tet_band[sel][i])]["h"] * px * 0.35)
                dr.ellipse([u - r, v - r, u + r, v + r], fill=col(i))
            im.save(folder / f"{name}_{what}.png")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2], sys.argv[3:])

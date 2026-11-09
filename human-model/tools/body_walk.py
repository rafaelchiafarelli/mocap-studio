"""The body walks in layers, every bone carrying its tissue, on the GPU: the lower body (task muscle-physics/leg-walk/2) or the whole
body with ABOVE_HIP=10 (task muscle-physics/body-walk/1).
    hm.sh --gpu python human-model/tools/body_walk.py LAYERS.npz BONES.npz WALK_DUMP.npz OUT_DIR [NAME=value ...]
LAYERS.npz is from tools/body_layers.py (on the pushed skin), BONES.npz the build's bones, WALK_DUMP.npz from blender/body_walk_dump.py.
Tissue values from data/body_tissue.json, with its REGIONS table of overrides by tissue and zone (REGIONS=file gives another), how often the volumes are measured and whether bones are tested against the skin from data/simulation.json; NAME=value overrides one, VOLUME_EVERY, BONE_TEST=1, or a constant below, for this run.
Writes OUT_DIR/body_walk.npz (for blender/body_walk_bake.py), body_walk_frames.csv and body_walk.json."""
import csv, json, os, sys, time
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import warp as wp
from hmcore import body, layers, meshgpu, regions as tissue_regions, xpbd

TISSUE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "body_tissue.json")
SIMULATION = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "simulation.json")
TISSUE_KEYS = ("SUBSTEPS", "DAMPING", "FAT_YOUNG", "MUSCLE_YOUNG", "SKIN_YOUNG", "FAT_DENSITY", "MUSCLE_DENSITY", "POISSON", "CAVITY_YOUNG", "CAVITY_DENSITY")
ABOVE_HIP = 0.02  # m above the hip bones' top: where the region is cut at the waist. 10 keeps the whole body
RAMP = 1.0  # s from the rest pose into the walk's first pose, so the tissue isn't jolted
SETTLE = 0.5  # s held in the first pose before frame 1
HOLD = 1.0  # s held in the last pose after the walk
CUT_PIN = 1.0  # voxels: nodes past each cut ring's plane, less this, move with their nearest bone
PAST_CUT = 0.35  # m: how far beyond a cut still counts as past it: the wrists' planes look down the body, and without a limit they caught the shins
CHECK_CLEAR = 0.03  # m: bone points this close to a cut aren't checked against the skin: a bone leaves the cut skin there by design
SKIN_DENSITY = 1100.0  # kg/m3, the band's


def measures_volume(frame, last, every):
    """Whether this frame's volumes are summed: every that many frames, and always the last, since the sum over all tetrahedra took two thirds of the walk's loop."""
    return frame % every == 0 or frame == last


def bone_summary(rows, walking):
    """What the bone-through-skin test found, ours and the current model's, for the run's summary."""
    return {"measured": True, "ours_frames_with_any": sum(r["bone_points_out"] > 0 for r in rows), "ours_max_points": max(r["bone_points_out"] for r in rows),
            "ours_max_depth_mm": max(r["bone_out_depth_mm"] for r in rows),
            "ours_bones": sorted({b for r in rows for b in r["bones_out"].split(";") if b}),
            "current_frames_with_any": sum(r["current_bone_points_out"] > 0 for r in walking),
            "current_max_points": max(r["current_bone_points_out"] for r in walking),
            "current_max_depth_mm": max(r["current_bone_out_depth_mm"] for r in walking),
            "current_bones": sorted({b for r in walking for b in r["current_bones_out"].split(";") if b})}


def region(nodes, tets, z_top):
    """The tetrahedra below z_top, largest connected piece (the legs and pelvis, without what's left of the arms), renumbered.
    Whole voxels only: layers.tetrahedra lists each voxel's six tetrahedra together, and the colouring needs all six."""
    voxel_z = nodes[tets].mean(axis=1)[:, 2].reshape(-1, 6).mean(axis=1)
    keep = np.flatnonzero(np.repeat(voxel_z < z_top, 6))
    t = tets[keep]
    n = len(nodes)
    rows = np.repeat(t[:, 0], 3)
    cols = t[:, 1:].ravel()
    _, comp = connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)), directed=False)
    main = np.bincount(comp[t[:, 0]]).argmax()
    keep = keep[comp[t[:, 0]] == main]
    used, inv = np.unique(tets[keep], return_inverse=True)
    return keep, used, inv.reshape(-1, 4)


def cut_zones(skin, rings, inside_point):
    """Each ring where the skin is cut, as (centre, outward normal, radius): its plane faces away from inside_point."""
    out = []
    for r in rings:
        p = skin[r]
        c = p.mean(axis=0)
        n = np.linalg.svd(p - c, full_matrices=False)[2][2]
        n = n if (c - inside_point) @ n > 0 else -n
        out.append((c, n, float(np.linalg.norm(p - c, axis=1).max())))
    return out


def near_cuts(points, zones, margin):
    """Points past a cut ring's plane, less margin, and within half again its radius of its centre."""
    out = np.zeros(len(points), bool)
    for c, n, radius in zones:
        out |= ((points - c) @ n > -margin) & (np.linalg.norm(points - c, axis=1) < 1.5 * radius + margin)
    return out


def moved(M, p):
    return p @ M[:3, :3].T + M[:3, 3]


def main(layers_npz, bones_npz, dump_npz, out_dir, overrides):
    g = globals()
    raw = json.load(open(TISSUE))
    regions = raw.pop("REGIONS", {})
    tissue = {k: v for k, v in raw.items() if not k.startswith("_")}
    if set(tissue) != set(TISSUE_KEYS):
        raise ValueError(f"{TISSUE} must give exactly {', '.join(TISSUE_KEYS)}")
    g.update(tissue)
    g["SUBSTEPS"] = int(g["SUBSTEPS"])
    settings = json.load(open(SIMULATION))
    g["VOLUME_EVERY"] = int(settings["VOLUME_EVERY_FRAMES"])
    g["BONE_TEST"] = int(settings["BONE_TEST"])
    for o in overrides:
        k, v = o.split("=")
        if k == "REGIONS":  # a file with its own table, for this run
            regions = json.load(open(v))
            continue
        if k not in g or k.startswith("_") or not isinstance(g[k], (int, float)):
            raise ValueError(f"unknown value {k}")
        g[k] = type(g[k])(float(v))
    if VOLUME_EVERY < 1:
        raise ValueError("VOLUME_EVERY must be at least 1")
    os.makedirs(out_dir, exist_ok=True)
    L, B, D = np.load(layers_npz), np.load(bones_npz), np.load(dump_npz)
    h = float(L["h"])
    bones = {k[:-3]: (B[k].astype(float), body.outward(B[k].astype(float), B[k[:-3] + "__f"].astype(np.int64))) for k in B.files if k.endswith("__v")}
    z_top = max(bones[b][0][:, 2].max() for b in ("hip_L", "hip_R")) + ABOVE_HIP
    keep, used, tets = region(L["nodes"].astype(float), L["tets"], z_top)
    nodes = L["nodes"].astype(float)[used]
    label = L["tet_label"][keep]
    zone_of_tet = L["tet_zone"][keep] if "tet_zone" in L.files else None  # layers made before the zones were kept have none

    # Each node's bone: the nearest bone vertex, among bones reaching below the cut
    # Only bones that hold some of the region's bone voxels: the hands hang below the waist in the rest pose but are outside the region,
    # and checking them against the skin counted every finger as poking through (leg_walk v1)
    names = [n for n in sorted(bones) if bones[n][0][:, 2].min() < z_top and f"T_{n}" in D.files]
    pts = np.concatenate([bones[n][0] for n in names])
    owner = np.concatenate([np.full(len(bones[n][0]), i) for i, n in enumerate(names)])
    bone_nodes = np.unique(tets[label == body.BONE])
    holding = np.unique(owner[cKDTree(pts).query(nodes[bone_nodes])[1]])
    names = [names[i] for i in holding]
    pts = np.concatenate([bones[n][0] for n in names])
    owner = np.concatenate([np.full(len(bones[n][0]), i) for i, n in enumerate(names)])
    node_bone = owner[cKDTree(pts).query(nodes)[1]].astype(np.int32)
    walk = np.stack([D[f"T_{n}"] for n in names], axis=1)  # frames x bones x 4 x 4
    fps = float(D["fps"])
    n_walk = len(walk)

    # The skin in the region, its triangles, and the rings where it's cut
    local_tet = np.full(len(L["tets"]), -1)
    local_tet[keep] = np.arange(len(keep))
    tied = local_tet[L["skin_tet"]] >= 0
    skin_ids, skin_tet, bary = L["skin_ids"][tied], local_tet[L["skin_tet"][tied]], L["skin_bary"][tied].astype(float)
    in_region = np.zeros(len(L["skin"]), bool)
    in_region[skin_ids] = True
    patch = L["patch"][in_region[L["patch"]].all(axis=1)]
    patch = layers.cut_patch(L["skin"].astype(float), patch, None, -np.inf, np.inf)
    # Every ring where the skin is cut (the waist, if any, the neck, wrists, ankles) is held by its nearest bone
    cut_rings = cut_zones(L["skin"].astype(float), layers.boundary_loops(patch), nodes.mean(axis=0))
    cut = np.flatnonzero(near_cuts(nodes, cut_rings, CUT_PIN * h))
    driven = np.union1d(bone_nodes, cut)

    vox = np.floor((nodes[tets[::6]].mean(axis=1) - nodes.min(axis=0)) / h).astype(int)
    table = tissue_regions.defaults({**g, "SKIN_DENSITY": SKIN_DENSITY}, body.LABELS)
    values = tissue_regions.per_tet(label, zone_of_tet if zone_of_tet is not None else np.zeros(len(label), np.int16), np.arange(len(tets)) // 6, vox, table, regions, body.LABELS, body.ZONES)
    young, density = values["young"], values["density"]
    if len(tets) % 6:
        raise ValueError("the region must keep whole voxels")
    colours = xpbd.voxel_colours(vox, np.arange(len(tets)) // 6)

    wp.init()
    s = xpbd.Solver(nodes, tets, colours, density, young, values["poisson"], damping=tissue_regions.node_values(tets, values["damping"], len(nodes)))
    s.drive(driven, nodes[driven], all_rest=nodes, bone=node_bone[driven], all_bone=node_bone, n_bones=len(names))
    dt = 1 / fps
    eye = np.repeat(np.eye(4)[None], len(names), axis=0)
    ramp = int(round(RAMP * fps))
    previous = eye
    for i in range(1, ramp + 1):
        now = eye + (walk[0] - eye) * (i / ramp)
        s.set_drive(previous, now)
        s.step(dt, SUBSTEPS)
        previous = now
    for _ in range(int(round(SETTLE * fps))):
        s.set_drive(walk[0], walk[0])
        s.step(dt, SUBSTEPS)
    wp.synchronize()

    # Bone points to check against the skin: bones inside the region, away from the cuts
    check = list(range(len(names)))
    check_pts = [bones[names[i]][0] for i in check]
    keep_pts = [~near_cuts(p, cut_rings, CHECK_CLEAR) for p in check_pts]
    # The head's and hands' bones hold the voxels at the cuts but lie past them, so the section video leaves out any bone mostly past those cuts.
    # The ankles' cuts face down and don't count: the feet stay in the videos, driven by the rig (Rafael, 2026-11-08).
    upper_cuts = [r for r in cut_rings if r[1][2] > -0.7]
    shown = np.array([np.any([((p - c) @ n > 0) & (np.linalg.norm(p - c, axis=1) < PAST_CUT) for c, n, _ in upper_cuts], axis=0).mean() <= 0.5 for p in check_pts])
    frames = np.concatenate([walk, np.repeat(walk[-1:], int(round(HOLD * fps)), axis=0)])
    skin_rest = L["skin"].astype(float)
    current_all = D["skins"].astype(float)
    zone = L["zone"][skin_ids]
    label_vol = {k: label == i for i, k in enumerate(body.LABELS) if (label == i).any()}
    rest_vol = {k: s.volume(m) for k, m in label_vol.items()}
    back = nodes[tets].mean(axis=1)[:, 1] > np.median(nodes[:, 1])
    cut_faces = {k: layers.boundary_faces(tets[back & (label == i)]) for i, k in enumerate(body.LABELS) if (back & (label == i)).any()}
    cut_nodes = np.unique(np.concatenate([f.ravel() for f in cut_faces.values()]))

    def poking(skin_now, f):
        closed = meshgpu.Mesh(*layers.capped(skin_now, patch))
        surface = meshgpu.Mesh(skin_now, patch)
        out = {}
        for i, p, k in zip(check, check_pts, keep_pts):
            q = moved(frames[f][i], p[k])
            inside = closed.inside(q)
            if (~inside).any():
                out[names[i]] = (int((~inside).sum()), round(float(surface.closest(q[~inside])[0].max()) * 1000, 1))
        return out

    rows, skins, cut_frames, ms = [], [], [], []
    first = None
    for f in range(len(frames)):
        s.set_drive(frames[max(f - 1, 0)], frames[f])
        wp.synchronize()
        t0 = time.perf_counter()
        s.step(dt, SUBSTEPS)
        wp.synchronize()
        ms.append((time.perf_counter() - t0) * 1000)
        x = s.positions().astype(float)
        ours = np.einsum("ik,ikd->id", bary, x[tets[skin_tet]])
        skin_now = skin_rest.copy()
        skin_now[skin_ids] = ours
        # What the tissue adds: the skin's motion since the first frame, less the current model's, whose skin only follows the bones (bug human-model/14)
        cur_now = current_all[min(f, n_walk - 1)][skin_ids]
        first = (ours.copy(), cur_now) if first is None else first
        motion = np.linalg.norm((ours - first[0]) - (cur_now - first[1]), axis=1) * 1000
        v = x[tets]
        det = np.einsum("ij,ij->i", np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), v[:, 3] - v[:, 0])
        bone_out = {}
        if BONE_TEST:
            ours_poke = poking(skin_now, f)
            bone_out = {"bone_points_out": sum(v[0] for v in ours_poke.values()), "bone_out_depth_mm": max([v[1] for v in ours_poke.values()], default=0.0),
                        "bones_out": ";".join(sorted(ours_poke))}
        volumes = {f"{k}_volume": round(s.volume(m) / rest_vol[k], 4) for k, m in label_vol.items()} if measures_volume(f, len(frames) - 1, VOLUME_EVERY) else {}
        row = {"frame": f + 1, "walking": f < n_walk, "ms": round(ms[-1], 2), "inverted_tetrahedra": int((det <= 0).sum()),
               **bone_out, "skin_motion_max_mm": round(float(motion.max()), 1),
               **volumes}
        if BONE_TEST and f < n_walk:
            current = skin_rest.copy()
            current[skin_ids] = current_all[f][skin_ids]
            cur = poking(current, f)
            row.update(current_bone_points_out=sum(v[0] for v in cur.values()), current_bone_out_depth_mm=max([v[1] for v in cur.values()], default=0.0),
                       current_bones_out=";".join(sorted(cur)))
        rows.append(row)
        skins.append(ours.astype(np.float32))
        cut_frames.append(x[cut_nodes].astype(np.float32))
        zone_motion = {z: float(motion[zone == z].max()) for z in np.unique(zone)}
        row["zone_motion"] = zone_motion
        print(json.dumps({k: v for k, v in row.items() if k != "zone_motion"}), flush=True)

    walking = [r for r in rows if r["walking"]]
    zones = sorted({z for r in rows for z in r["zone_motion"]})
    summary = {"declared": {k: g[k] for k in TISSUE_KEYS + ("ABOVE_HIP", "RAMP", "SETTLE", "HOLD", "CUT_PIN", "CHECK_CLEAR", "SKIN_DENSITY", "VOLUME_EVERY", "BONE_TEST")}, "regions": regions,
               "cuts": len(cut_rings),
               "gpu": wp.get_device("cuda:0").name, "tetrahedra": int(len(tets)), "nodes": int(len(nodes)), "driven_nodes": int(len(driven)),
               "bones": names, "frames_walking": n_walk, "ms_per_frame": {"median": round(float(np.median(ms)), 1), "max": round(float(np.max(ms)), 1)},
               "peak_vram_mib": round(wp.get_mempool_used_mem_high("cuda:0") / 2 ** 20, 1),
               "bone_through_skin": bone_summary(rows, walking) if BONE_TEST else {"measured": False},
               "inverted_tetrahedra_max": max(r["inverted_tetrahedra"] for r in rows),
               "skin_motion_peak_by_zone_mm": {z: round(max(r["zone_motion"].get(z, 0.0) for r in walking), 1) for z in zones},
               "volume_range": {k: [min(r[f"{k}_volume"] for r in rows if f"{k}_volume" in r), max(r[f"{k}_volume"] for r in rows if f"{k}_volume" in r)] for k in label_vol}}
    np.savez_compressed(f"{out_dir}/body_walk.npz", skins=np.array(skins), skin_ids=skin_ids, patch=patch, cut_nodes=cut_nodes,
                        cut_frames=np.array(cut_frames), frames_walking=n_walk, fps=fps, bone_names=np.array(names), shown_bones=shown, transforms=frames,
                        **{f"cut_{k}": np.searchsorted(cut_nodes, f) for k, f in cut_faces.items()})
    keys = [k for k in rows[-1] if k != "zone_motion"] + [k for k in walking[0] if k not in rows[-1]]
    with open(f"{out_dir}/body_walk_frames.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    with open(f"{out_dir}/body_walk.json", "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])

"""The layered thigh walks: the femur is moved, muscle, fat and skin follow on the GPU (task muscle-physics/thigh/3).
    hm.sh --gpu python human-model/tools/thigh_walk.py LAYERS.npz WALK_DUMP.npz OUT_DIR [NAME=value overrides the constants below]
LAYERS.npz is from tools/thigh_layers.py, WALK_DUMP.npz from blender/thigh_walk_dump.py on the same person's walk_review file.
Writes OUT_DIR/thigh_walk.npz (skin and nodes per frame, for blender/thigh_bake.py), thigh_walk_frames.csv and thigh_walk.json."""
import csv, json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import warp as wp
from scipy.spatial import cKDTree
from hmcore import fit, layers, xpbd

SUBSTEPS = 160  # per frame: converged here, 40 and 80 weren't (docs/muscle-physics.md)
SETTLE = 1.0  # s in the first frame's pose before frame 1, so the tissue hangs under gravity first
HOLD = 1.0  # s in the last frame's pose after the walk, to see the tissue settle
# Declared, by look, no measured tissue data yet (tissue-research): passive muscle stiffer than fat
MUSCLE_YOUNG, FAT_YOUNG = 15000.0, 3000.0  # Pa
POISSON = 0.45
MUSCLE_DENSITY, FAT_DENSITY = 1060.0, 900.0  # kg/m3
# Skin holds the fat in. Without it the fat swung up to 10 cm at each step (thigh_walk_v2). Real skin is far stiffer but 1 to 2 mm thick;
# here it's the band of tetrahedra within SKIN_BAND voxels of the surface, so its modulus is lowered to match: about 0.5 MPa x 1.5 mm / 5 mm. Declared
SKIN_YOUNG = 150000.0  # Pa; 0 leaves the band as fat
SKIN_BAND = 1.0  # voxels
DAMPING = 5.0  # 1/s
CUT_PIN = 1.0  # voxels: the ends move with the femur, as the contract says: every node past the skin's end ring, and this far inside it


def bone_through_skin(bone, skin, patch, spacing):
    """How many of these bone points are outside the closed skin patch, and the deepest of them, in mm."""
    cv, ct = layers.capped(skin, patch)
    out = fit.winding_number(bone, cv, ct) <= 0.5
    if not out.any():
        return 0, 0.0
    depth = cKDTree(layers.surface_samples(skin, patch, spacing)).query(bone[out])[0]
    return int(out.sum()), round(float(depth.max()) * 1000, 2)


def main(layers_npz, dump_npz, out_dir, overrides):
    g = globals()
    for o in overrides:
        k, v = o.split("=")
        g[k] = type(g[k])(float(v))
    os.makedirs(out_dir, exist_ok=True)
    L, D = np.load(layers_npz), np.load(dump_npz)
    nodes, tets, label = L["nodes"].astype(float), L["tets"], L["tet_label"]
    h = float(np.min(np.ptp(nodes[tets[:6]].reshape(-1, 3), axis=0)))  # the voxel's side: layers.tetrahedra gives six per voxel, in order
    patch, skin_ids, skin_tet, bary = L["patch"], L["skin_ids"], L["skin_tet"], L["skin_bary"].astype(float)
    T = D["transforms"]
    fps = float(D["fps"])
    hold = int(round(HOLD * fps))
    T = np.concatenate([T, np.repeat(T[-1:], hold, axis=0)])
    n_walk = len(D["transforms"])

    # The bone, and the tissue at the cuts, follow the femur
    bone_nodes = np.unique(tets[label == layers.BONE])
    # The ring at the crotch slopes, so the ends are taken from each ring's own span, not from the highest and lowest node:
    # pinning only the nodes nearest the extremes left most of the top end loose, like a sleeve (thigh_walk_v1)
    z = nodes[:, 2]
    rings = sorted((L["skin"][loop, 2] for loop in layers.boundary_loops(L["patch"])), key=np.mean)
    cut = np.flatnonzero((z < rings[0].max() + CUT_PIN * h) | (z > rings[-1].min() - CUT_PIN * h))
    driven = np.union1d(bone_nodes, cut)
    young = np.where(label == layers.FAT, FAT_YOUNG, MUSCLE_YOUNG)
    near_skin = cKDTree(layers.surface_samples(L["skin"].astype(float), L["patch"], h / 3)).query(nodes[tets].mean(axis=1))[0] < SKIN_BAND * h
    skin_band = near_skin & (label == layers.FAT)
    if SKIN_YOUNG > 0:
        young = np.where(skin_band, SKIN_YOUNG, young)
    density = np.where(label == layers.FAT, FAT_DENSITY, MUSCLE_DENSITY)

    def moved(M, p):
        return p @ M[:3, :3].T + M[:3, 3]

    wp.init()
    start = moved(T[0], nodes)
    vox = np.floor((nodes[tets[::6]].mean(axis=1) - nodes.min(axis=0)) / h).astype(int)
    colours = xpbd.voxel_colours(vox, np.arange(len(tets)) // 6)
    s = xpbd.Solver(start, tets, colours, density, young, POISSON, damping=DAMPING)
    s.drive(driven, nodes[driven], all_rest=nodes)
    dt = 1 / fps
    s.set_drive(T[0], T[0])
    for _ in range(int(round(SETTLE * fps))):
        s.step(dt, SUBSTEPS)
    wp.synchronize()

    # Femur points between the skin's two rings at rest, where skin surrounds the bone
    femur = L["femur_v"].astype(float)
    rings = [L["skin"][loop, 2] for loop in layers.boundary_loops(patch)]
    lo, hi = float(min(rings, key=np.mean).max()), float(max(rings, key=np.mean).min())
    femur = femur[(femur[:, 2] > lo) & (femur[:, 2] < hi)]
    skin_all = L["skin"].astype(float)
    spacing = h / 3
    fat_tets, muscle_tets = label == layers.FAT, label == layers.MUSCLE
    rest_fat, rest_muscle = s.volume(fat_tets), s.volume(muscle_tets)

    rows, skins, node_frames, ms = [], [], [], []
    local_first = None
    for f in range(len(T)):
        s.set_drive(T[max(f - 1, 0)], T[f])
        wp.synchronize()
        t0 = time.perf_counter()
        s.step(dt, SUBSTEPS)
        wp.synchronize()
        ms.append((time.perf_counter() - t0) * 1000)
        x = s.positions().astype(float)
        ours = np.einsum("ik,ikd->id", bary, x[tets[skin_tet]])
        skin_now = skin_all.copy()
        skin_now[skin_ids] = ours
        Minv = np.linalg.inv(T[f])
        local = moved(Minv, ours)
        if local_first is None:
            local_first = local
        motion = np.linalg.norm(local - local_first, axis=1) * 1000
        n_out, depth = bone_through_skin(moved(T[f], femur), skin_now, patch, spacing)
        row = {"frame": f + 1, "walking": f < n_walk, "ms": round(ms[-1], 2), "bone_out_points": n_out, "bone_out_depth_mm": depth,
               "skin_motion_mean_mm": round(float(motion.mean()), 2), "skin_motion_max_mm": round(float(motion.max()), 2),
               "fat_volume": round(s.volume(fat_tets) / rest_fat, 5), "muscle_volume": round(s.volume(muscle_tets) / rest_muscle, 5)}
        if f < n_walk:
            current = D["skins"][f].astype(float)
            c_out, c_depth = bone_through_skin(moved(T[f], femur), current, patch, spacing)
            c_motion = np.linalg.norm(moved(Minv, current[skin_ids]) - moved(np.linalg.inv(T[0]), D["skins"][0].astype(float)[skin_ids]), axis=1) * 1000
            row.update(current_bone_out_points=c_out, current_bone_out_depth_mm=c_depth, current_skin_motion_max_mm=round(float(c_motion.max()), 2))
        rows.append(row)
        skins.append(ours.astype(np.float32))
        node_frames.append(x.astype(np.float32))
        print(json.dumps(row), flush=True)

    walk = [r for r in rows if r["walking"]]
    after = [r["skin_motion_max_mm"] for r in rows[n_walk:]]
    final = after[-1] if after else 0.0
    settle = next((i for i in range(len(after)) if all(abs(a - final) < 1.0 for a in after[i:])), None)
    peak = max(walk, key=lambda r: r["skin_motion_max_mm"])
    summary = {"declared": {k: g[k] for k in ("SUBSTEPS", "SETTLE", "HOLD", "MUSCLE_YOUNG", "FAT_YOUNG", "POISSON", "MUSCLE_DENSITY", "FAT_DENSITY",
                                              "DAMPING", "CUT_PIN", "SKIN_YOUNG", "SKIN_BAND")},
               "gpu": wp.get_device("cuda:0").name, "tetrahedra": int(len(tets)), "nodes": int(len(nodes)), "driven_nodes": int(len(driven)), "skin_band_tetrahedra": int(skin_band.sum()) if SKIN_YOUNG > 0 else 0,
               "frames_walking": n_walk, "frames_holding": hold,
               "ms_per_frame": {"median": round(float(np.median(ms)), 2), "max": round(float(np.max(ms)), 2)},
               "peak_vram_mib": round(wp.get_mempool_used_mem_high("cuda:0") / 2 ** 20, 1),
               "bone_through_skin": {"ours_frames_with_any": sum(r["bone_out_points"] > 0 for r in rows), "ours_max_points": max(r["bone_out_points"] for r in rows),
                                     "ours_max_depth_mm": max(r["bone_out_depth_mm"] for r in rows),
                                     "current_frames_with_any": sum(r["current_bone_out_points"] > 0 for r in walk),
                                     "current_max_points": max(r["current_bone_out_points"] for r in walk),
                                     "current_max_depth_mm": max(r["current_bone_out_depth_mm"] for r in walk)},
               "skin_motion_in_femur_frame": {"ours_peak_mm": peak["skin_motion_max_mm"], "ours_peak_frame": peak["frame"],
                                              "current_peak_mm": max(r["current_skin_motion_max_mm"] for r in walk),
                                              "after_stop_settles_in_s": round(settle / fps, 2) if settle is not None else None},
               "volume_range": {"fat": [min(r["fat_volume"] for r in rows), max(r["fat_volume"] for r in rows)],
                                "muscle": [min(r["muscle_volume"] for r in rows), max(r["muscle_volume"] for r in rows)]}}
    np.savez_compressed(f"{out_dir}/thigh_walk.npz", skins=np.array(skins), nodes=np.array(node_frames), transforms=T, frames_walking=n_walk, fps=fps)
    with open(f"{out_dir}/thigh_walk_frames.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) + [k for k in walk[0] if k not in rows[0]] if walk else list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(f"{out_dir}/thigh_walk.json", "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])

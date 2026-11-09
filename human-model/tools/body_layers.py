"""The whole woman in layers, at rest (task muscle-physics/body-at-rest/1).
    hm.sh --gpu python human-model/tools/body_layers.py BUILD_DIR NAME OUT_DIR [fat.<zone>=mm ...] [structure.<name>=value ...] [VOXEL=m] [SKIN=skin_fit.npz]
SKIN takes the skin from tools/skin_over_bone.py in place of the build's.
Reads <NAME>.export.npz, .export.json and .bones.npz from BUILD_DIR, the fat per zone from data/body_fat_<sex>.json and the cube's size from data/simulation.json (VOXEL=m overrides it for this run).
Writes to OUT_DIR, every step numbered: 01_skin_cut.ply, 02_skin_capped.ply, 03_zones.ply, 04_fat_thickness.ply (coloured),
05_raw_<label>.ply (voxel centres), 06_<label>_surface.ply, 07_cutaway_<label>.ply (the back half), <NAME>.body_layers.npz and .json."""
import json, os, sys, time
import numpy as np
from scipy.spatial import cKDTree
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import warp as wp
from hmcore import body, fit, layers, meshgpu

N_BODY = 13380  # MakeHuman's body vertices come first; helpers follow, as in blender/export_blend.py
DATA =os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
COLORS = {"bone": (230, 220, 190), "muscle": (155, 30, 25), "fat": (240, 205, 90), "skin": (215, 165, 140), "cavity": (110, 140, 200)}


def zone_colors(zone_names):
    rng = np.random.default_rng(7)
    palette = {z: rng.integers(40, 255, 3) for z in body.ZONES}
    return np.array([palette[z] if z in palette else (128, 128, 128) for z in zone_names])


def ramp(values, lo, hi):
    t = np.clip((values - lo) / max(hi - lo, 1e-9), 0, 1)[:, None]
    return (1 - t) * np.array([40, 60, 200]) + t * np.array([250, 220, 40])


def measure(r, skin, bones, fat_mm, gpu_mesh, rig):
    labels = r["tet_label"]
    v = r["nodes"][r["tets"]]
    vol = np.einsum("ij,ij->i", np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), v[:, 3] - v[:, 0]) / 6
    litres = {name: round(float(vol[labels == k].sum()) * 1000, 2) for k, name in enumerate(body.LABELS)}
    cv, ct = r["capped_verts"], r["capped_tris"]
    enclosed = abs(float(np.einsum("ij,ij->i", cv[ct[:, 0]], np.cross(cv[ct[:, 1]], cv[ct[:, 2]])).sum()) / 6)
    pv = skin[r["patch"]]
    area = float(np.linalg.norm(np.cross(pv[:, 1] - pv[:, 0], pv[:, 2] - pv[:, 0]), axis=1).sum() / 2)

    closed = gpu_mesh(r["capped_verts"], r["capped_tris"])
    surface = gpu_mesh(skin, r["patch"])
    planes = body.cut_planes(skin, r["patch"])
    report = {}
    for name in r["bone_names"]:
        bv = bones[name][0]
        inside = closed.inside(bv)
        if inside.mean() < 0.5:
            continue  # beyond the cuts: head, hands, feet
        d = surface.closest(bv)[0]
        cut = body.near_a_cut(bv, rig, planes)
        poking = ~inside & ~cut
        report[name] = {"points_outside_skin": int(poking.sum()), "deepest_mm": round(float(d[poking].max()) * 1000, 1) if poking.any() else 0.0,
                        "points_at_a_cut": int((~inside & cut).sum()),
                        "closest_to_skin_mm": round(float(d[inside].min()) * 1000, 1) if inside.any() else None}
    outside = {k: v for k, v in sorted(report.items(), key=lambda kv: -kv[1]["points_outside_skin"]) if v["points_outside_skin"]}
    closest = sorted(((v["closest_to_skin_mm"], k) for k, v in report.items() if v["closest_to_skin_mm"] is not None))[:10]

    grid_lab = r["labels_clean"]
    under = r["centres"][(grid_lab == body.MUSCLE) | (grid_lab == body.CAVITY) | (grid_lab == body.BONE)]
    ids = r["skin_ids"]
    actual = cKDTree(under).query(skin[ids])[0] - r["h"] / 2
    fat = {}
    for z in body.ZONES:
        m = r["zone"][ids] == z
        if m.any():
            fat[z] = {"declared_mm": fat_mm[z], "median_mm": round(float(np.median(actual[m])) * 1000, 1),
                      "p10_mm": round(float(np.percentile(actual[m], 10)) * 1000, 1), "p90_mm": round(float(np.percentile(actual[m], 90)) * 1000, 1),
                      "skin_points": int(m.sum())}
    return {"litres": litres, "enclosed_litres": round(enclosed * 1000, 2), "skin_area_m2": round(area, 4), "tetrahedra": {name: int((labels == k).sum()) for k, name in enumerate(body.LABELS)}, "nodes": int(len(r["nodes"])),
            "islands_moved": r["moved"], "skin_points_tied": int(len(ids)), "skin_tie_worst_weight": round(float(r["skin_score"].min()), 6),
            "bones_measured": len(report), "bones_with_points_outside_skin": outside, "bones_closest_to_skin_mm": closest, "fat": fat}


def main(build_dir, name, out_dir, overrides):
    global VOXEL
    VOXEL = json.load(open(os.path.join(DATA, "simulation.json")))["VOXEL_M"]
    skin_file = None
    os.makedirs(out_dir, exist_ok=True)
    meta = json.load(open(os.path.join(build_dir, f"{name}.export.json")))
    sex = "female" if meta["macros"]["gender"] < 0.5 else "male"
    with open(os.path.join(DATA, f"body_fat_{sex}.json")) as fh:
        cfg = json.load(fh)
    fat_mm, structure = cfg["fat_mm"], cfg["structure"]
    for o in overrides:
        k, val = o.split("=")
        if k == "VOXEL":
            VOXEL = float(val)
            continue
        if k == "SKIN":
            skin_file = val
            continue
        group, _, key = k.partition(".")
        table = {"fat": fat_mm, "structure": structure}.get(group)
        if table is None or key not in table:
            raise ValueError(f"unknown value {k}")
        table[key] = float(val)
    e = np.load(os.path.join(build_dir, f"{name}.export.npz"))
    skin = (np.load(skin_file)["verts"] if skin_file else e["verts"]).astype(float)[:N_BODY]
    tris = fit.triangles(e["starts"], e["sizes"], e["loops"])
    tris = tris[tris.max(axis=1) < N_BODY]
    b = np.load(os.path.join(build_dir, f"{name}.bones.npz"))
    bones = {k[:-3]: (b[k].astype(float), b[k[:-3] + "__f"].astype(np.int64)) for k in b.files if k.endswith("__v")}

    wp.init()
    t0 = time.time()
    r = body.build(skin, tris, meta["bones"], bones, fat_mm, structure, VOXEL, meshgpu.Mesh, groups=meta["groups"])
    seconds = time.time() - t0
    m = measure(r, skin, bones, fat_mm, meshgpu.Mesh, meta["bones"])

    ids = r["skin_ids"]
    local = np.full(len(skin), -1)
    local[ids] = np.arange(len(ids))
    layers.write_ply(f"{out_dir}/01_skin_cut.ply", skin, r["patch"])
    layers.write_ply(f"{out_dir}/02_skin_capped.ply", r["capped_verts"], r["capped_tris"])
    layers.write_ply(f"{out_dir}/03_zones.ply", skin[ids], local[r["patch"]], zone_colors(r["zone"][ids]))
    layers.write_ply(f"{out_dir}/04_fat_thickness.ply", skin[ids], local[r["patch"]], ramp(r["thickness"][ids], 0.0, 0.03))
    for k, label in enumerate(body.LABELS):
        layers.write_ply(f"{out_dir}/05_raw_{label}.ply", r["centres"][r["labels_raw"] == k])
    surfaces = {}
    back = r["nodes"][r["tets"]].mean(axis=1)[:, 1] > np.median(r["nodes"][:, 1])
    for k, label in enumerate(body.LABELS):
        surfaces[label] = layers.boundary_faces(r["tets"][r["tet_label"] == k])
        layers.write_ply(f"{out_dir}/06_{label}_surface.ply", r["nodes"], surfaces[label])
        surfaces[f"cutaway_{label}"] = layers.boundary_faces(r["tets"][back & (r["tet_label"] == k)])
        layers.write_ply(f"{out_dir}/07_cutaway_{label}.ply", r["nodes"], surfaces[f"cutaway_{label}"])

    np.savez_compressed(f"{out_dir}/{name}.body_layers.npz", nodes=r["nodes"].astype(np.float32), tets=r["tets"].astype(np.int32),
                        tet_label=r["tet_label"].astype(np.int8), tet_zone=r["tet_zone"].astype(np.int16), zone_names=np.array(body.ZONES), skin_ids=ids.astype(np.int32), skin_tet=r["skin_tet"].astype(np.int32),
                        skin_bary=r["skin_bary"].astype(np.float32), patch=r["patch"].astype(np.int32), skin=skin.astype(np.float32),
                        zone=np.array([z or "" for z in r["zone"]]), thickness=r["thickness"].astype(np.float32),
                        origin=r["origin"], shape=r["shape"], h=r["h"], labels_clean=r["labels_clean"],
                        **{f"surface_{k}": v.astype(np.int32) for k, v in surfaces.items()})
    report = {"name": name, "sex": sex, "skin_source": skin_file or "build", "declared": {"voxel_m": VOXEL, "fat_mm": fat_mm, "structure": structure}, "seconds": round(seconds, 1), **m}
    with open(f"{out_dir}/{name}.body_layers.json", "w") as fh:
        json.dump(report, fh, indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])

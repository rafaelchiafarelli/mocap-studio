"""One thigh built from the inside out: femur, muscle, fat, skin, as tetrahedra (task muscle-physics/thigh/2).
    hm.sh python human-model/tools/thigh_layers.py BUILD_DIR NAME OUT_DIR [NAME=value overrides the constants below]
Reads <NAME>.export.npz and <NAME>.bones.npz from BUILD_DIR. Writes to OUT_DIR, keeping every step, numbered in order:
01_skin_cut.ply, 02_skin_capped.ply, 03_voxels_inside.ply, 04_raw_<layer>.ply, 05_dropped.ply, 06_<layer>_surface.ply, 07_cutaway_<layer>.ply (back half),
<prefix>.thigh_layers.npz (what task 3 reads) and <prefix>.thigh_layers.json (the measures and the declared values)."""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from hmcore import fit, layers

N_BODY = 13380  # MakeHuman's body vertices come first; helpers follow, as in blender/export_blend.py
SIDE = 1  # +1 is the left thigh (+X); agreed with Rafael 2026-11-07
VOXEL = 0.005  # m
BELOW_CROTCH = 0.02  # m: the top cut, under the crotch so the slab holds one leg only. Declared
ABOVE_KNEE = 0.08  # m above the femur's lowest point: the bottom cut, clear of the knee. Declared
# Declared by eye, no measured data yet (task 2, "Agreed with Rafael"): a neutral adult woman's thigh, more at the back and inside
FAT_FRONT, FAT_BACK, FAT_INNER, FAT_OUTER = 15.0, 25.0, 25.0, 22.0  # mm


def main(build_dir, name, out_dir, overrides):
    g = globals()
    for o in overrides:
        k, v = o.split("=")
        g[k] = type(g[k])(float(v))
    os.makedirs(out_dir, exist_ok=True)
    prefix = os.path.join(out_dir, name)
    e = np.load(os.path.join(build_dir, f"{name}.export.npz"))
    skin = e["verts"].astype(float)[:N_BODY]
    tris = fit.triangles(e["starts"], e["sizes"], e["loops"])
    tris = tris[tris.max(axis=1) < N_BODY]
    b = np.load(os.path.join(build_dir, f"{name}.bones.npz"))
    key = "femur_L" if SIDE > 0 else "femur_R"
    bone, bone_tris = b[f"{key}__v"].astype(float), b[f"{key}__f"].astype(np.int64)

    z_hi = layers.crotch_z(skin) - BELOW_CROTCH
    z_lo = float(bone[:, 2].min()) + ABOVE_KNEE
    fat = dict(front=FAT_FRONT, back=FAT_BACK, inner=FAT_INNER, outer=FAT_OUTER)
    t0 = time.time()
    r = layers.build(skin, tris, bone, bone_tris, SIDE, z_lo, z_hi, VOXEL, fat)
    seconds = time.time() - t0
    m = layers.measure(r, skin, bone, SIDE, fat)

    layers.write_ply(f"{out_dir}/01_skin_cut.ply", skin, r["patch"])
    layers.write_ply(f"{out_dir}/02_skin_capped.ply", r["capped_verts"], r["capped_tris"])
    layers.write_ply(f"{out_dir}/03_voxels_inside.ply", r["centres"][r["included"]])
    for k, label in enumerate(layers.LABELS):
        layers.write_ply(f"{out_dir}/04_raw_{label}.ply", r["centres"][r["labels_raw"] == k])
    layers.write_ply(f"{out_dir}/05_dropped.ply", r["centres"][r["dropped_bone"] | r["dropped_muscle"]])
    surfaces = {}
    for k, label in enumerate(layers.LABELS):
        f = layers.boundary_faces(r["tets"][r["tet_label"] == k])
        surfaces[label] = f
        layers.write_ply(f"{out_dir}/06_{label}_surface.ply", r["nodes"], f)
    # The back half only, seen from the front: the layers in section. The cut runs along the femur's axis, which leans, so the bone shows its whole length
    normal = np.cross(r["axis_direction"], [1.0, 0.0, 0.0])
    normal = normal * np.sign(normal[1]) / np.linalg.norm(normal)
    back = (r["nodes"][r["tets"]].mean(axis=1) - r["axis_centre"]) @ normal > 0
    for k, label in enumerate(layers.LABELS):
        f = layers.boundary_faces(r["tets"][back & (r["tet_label"] == k)])
        surfaces[f"cutaway_{label}"] = f
        layers.write_ply(f"{out_dir}/07_cutaway_{label}.ply", r["nodes"], f)

    np.savez_compressed(f"{prefix}.thigh_layers.npz", nodes=r["nodes"].astype(np.float32), tets=r["tets"].astype(np.int32),
                        tet_label=r["tet_label"].astype(np.int8), skin_ids=r["skin_ids"].astype(np.int32), skin_tet=r["skin_tet"].astype(np.int32),
                        skin_bary=r["skin_bary"].astype(np.float32), patch=r["patch"].astype(np.int32), skin=skin.astype(np.float32),
                        femur_v=bone.astype(np.float32), femur_f=bone_tris.astype(np.int32),
                        **{f"surface_{k}": v.astype(np.int32) for k, v in surfaces.items()})
    report = {"name": name, "side": "left" if SIDE > 0 else "right", "declared": {"voxel_m": VOXEL, "below_crotch_m": BELOW_CROTCH,
              "above_knee_m": ABOVE_KNEE, "fat_mm": fat}, "cuts_z_m": [round(z_lo, 4), round(z_hi, 4)], "seconds": round(seconds, 1), **m}
    with open(f"{prefix}.thigh_layers.json", "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])

"""The skin as the result of the layers, on the same 13,380 points and the same rig (epic volumes-outward): bones, then muscle by zone, then fat up to the sheet's percentage, and the skin moved onto what results.
    hm.sh --gpu python human-model/tools/outward_skin.py BUILD_DIR NAME SHEET.json OUT_DIR [VOXEL=m]
SHEET.json is {"resolved": hmcore.character.resolve's result, "character": the character file}. Reads the build's skin, bones and rig; the muscle and fat tables from data/.
Writes OUT_DIR/<NAME>.skin_fit.npz (the new body, for tools/body_layers.py, as skin_over_bone.py's), <NAME>.fat_table.json (each zone's fat after reaching the percentage, for body_layers.py's FAT_TABLE=), <NAME>.regions.json (per-region tissue values, for body_walk.py's REGIONS=) and <NAME>.skin_fit.json (the report)."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import warp as wp
from hmcore import body, character as ch, fit, layers, meshgpu, outward, shapes

N_BODY = 13380  # as in blender/export_blend.py
HERE = os.path.dirname(os.path.abspath(__file__))
MARGIN = 0.08  # m around the first shape: how far the new surface may reach
MOST_MOVE = 0.08  # m, the most a skin point moves
RING_REACH = 0.05  # m over which the move fades out to the cut rings


def past_cuts(point, planes, reach=0.35):
    """Whether a bone's centre lies beyond a cut's plane: the head's, a hand's or a foot's bones are left out of the layers."""
    return any((point - c) @ n > 0 and np.linalg.norm(point - c) < reach for c, n, _ in planes)


def thickness_per_vertex(table, zone, patch, n_verts, iterations):
    values = np.zeros(n_verts)
    ids = np.unique(patch)
    values[ids] = [table[z] / 1000 for z in zone[ids]]
    return body.smooth_on_surface(values, patch, n_verts, iterations)


def main(build_dir, name, sheet_json, out_dir, overrides):
    voxel = json.load(open(os.path.join(HERE, "..", "data", "simulation.json")))["VOXEL_M"]
    for o in overrides:
        k, v = o.split("=")
        if k != "VOXEL":
            raise ValueError(f"unknown value {k}")
        voxel = float(v)
    os.makedirs(out_dir, exist_ok=True)
    sheet = json.load(open(sheet_json, encoding="utf-8"))
    fields, character = sheet["resolved"]["fields"], sheet["character"]
    meta = json.load(open(os.path.join(build_dir, f"{name}.export.json")))
    sex = character["sex"]
    cfg = json.load(open(os.path.join(HERE, "..", "data", f"body_fat_{sex}.json")))
    fat_mm = dict(cfg["fat_mm"])
    for zone, values in (character.get("regions") or {}).items():
        if "fat_mm" in values:
            fat_mm[zone] = values["fat_mm"]
    muscle_mm = json.load(open(os.path.join(HERE, "..", "data", f"muscle_mm_{sex}.json")))["muscle_mm"]
    data = os.path.join(HERE, "..", "data")
    if character.get("gluteus"):
        fat_mm, muscle_mm = shapes.gluteus(fat_mm, muscle_mm, character["gluteus"]["shape"], json.load(open(os.path.join(data, "gluteus_shapes.json"))))
    regions_out, structure_out = {}, {}
    if sex == "female":
        base = ch.base_measures("female")
        cup_ratio = (fields["bust"]["value"] - fields["underbust"]["value"]) / (base["bust"] - base["underbust"])
        fat_mm, regions_out, structure_out = shapes.breast(fat_mm, character.get("breast") or {}, json.load(open(os.path.join(data, "breast_shapes.json"))), cup_ratio)
    e = np.load(os.path.join(build_dir, f"{name}.export.npz"))
    skin = e["verts"].astype(float)[:N_BODY]
    tris = fit.triangles(e["starts"], e["sizes"], e["loops"])
    tris = tris[tris.max(axis=1) < N_BODY]
    b = np.load(os.path.join(build_dir, f"{name}.bones.npz"))
    bones = {k[:-3]: (b[k].astype(float), body.outward(b[k].astype(float), b[k[:-3] + "__f"].astype(np.int64))) for k in b.files if k.endswith("__v")}
    patch = body.cut_skin(skin, tris, meta["bones"], meta["groups"])
    ids = np.unique(patch)
    zone = np.empty(len(skin), object)
    zone[ids] = body.divide_zones(skin[ids], body.zones(skin, ids, meta["bones"], bones))
    iters = int(cfg["structure"]["smoothing_iterations"])
    fat_v = thickness_per_vertex(fat_mm, zone, patch, len(skin), iters)
    muscle_v = thickness_per_vertex(muscle_mm, zone, patch, len(skin), iters)
    planes = body.cut_planes(skin, patch)
    region = [n for n, (v, _) in bones.items() if not past_cuts(v.mean(axis=0), planes)]

    wp.init()
    origin, shape, centres = layers.grid(skin[ids].min(axis=0) - MARGIN, skin[ids].max(axis=0) + MARGIN, voxel)
    keep = (~body.near_a_cut(centres, meta["bones"], planes)).reshape(shape)
    bv, bt, n = [], [], 0
    for name_b in region:
        v, t = bones[name_b]
        bv.append(v); bt.append(t + n); n += len(v)
    in_bone = meshgpu.Mesh(np.concatenate(bv), np.concatenate(bt)).inside(centres).reshape(shape)
    hull_points = np.concatenate([bones[x][0] for x in body.TRUNK_BONES])
    core = outward.core_mask(centres, hull_points, in_bone.ravel()).reshape(shape)
    muscle_cell = outward.per_cell(skin[ids], muscle_v[ids], centres).reshape(shape)
    fat_cell = outward.per_cell(skin[ids], fat_v[ids], centres).reshape(shape)
    muscle = outward.muscle_layer(core, muscle_cell, fields["muscle"]["value"], keep, voxel)
    pv = skin[patch]
    area = float(np.linalg.norm(np.cross(pv[:, 1] - pv[:, 0], pv[:, 2] - pv[:, 0]), axis=1).sum() / 2)
    target = fields["body_fat_percent"]["value"]
    result = outward.fat_to_percent(in_bone, core, muscle, keep, fat_cell, target, voxel, area)
    solid = core | muscle | result["fat"]
    sdf = outward.signed_distance(solid, voxel)
    normals = outward.vertex_normals(skin, patch)
    moved = outward.project(skin[ids], normals[ids], sdf, origin, voxel, MOST_MOVE)
    new = skin.copy()
    disp = np.zeros(skin.shape)
    disp[ids] = moved - skin[ids]
    disp = np.column_stack([body.smooth_on_surface(disp[:, k], patch, len(skin), iters) for k in range(3)])
    rings = layers.boundary_loops(patch)
    fade = outward.ring_fade(skin[ids], [skin[r] for r in rings], RING_REACH)
    new[ids] = skin[ids] + disp[ids] * fade[:, None]
    full = e["verts"].astype(np.float32).copy()
    full[:N_BODY] = new
    push = np.linalg.norm(new - skin, axis=1)
    np.savez_compressed(os.path.join(out_dir, f"{name}.skin_fit.npz"), verts=full, push=push.astype(np.float32), patch=patch.astype(np.int32))
    with open(os.path.join(out_dir, f"{name}.fat_table.json"), "w") as f:
        json.dump({"fat_mm": {z: round(v * result["scale"], 2) for z, v in fat_mm.items()}, "scale": round(result["scale"], 3), "structure": structure_out, "regions": regions_out}, f, indent=1)
    keys = {"young_pa": "young", "poisson": "poisson", "density": "density", "damping": "damping"}
    for zone, values in (character.get("regions") or {}).items():
        typed = {keys[k]: v for k, v in values.items() if k in keys}
        if typed:
            regions_out.setdefault("fat", {}).setdefault(zone, {}).update(typed)
    with open(os.path.join(out_dir, f"{name}.regions.json"), "w") as f:
        json.dump(regions_out, f, indent=1)
    report = {"name": name, "voxel_m": voxel, "target_percent": target, "percent": round(result["percent"], 2), "reached_within_0_5": bool(result["reached"]), "fat_scale": round(result["scale"], 3),
              "muscle_scale": fields["muscle"]["value"], "skin_points_moved": int(len(ids)), "largest_move_mm": round(float(push.max()) * 1000, 1), "mean_move_mm": round(float(push[ids].mean()) * 1000, 1),
              "ring_steps_mm": outward.ring_steps(skin, new, rings), "triangles_turned_over": outward.folded(skin, new, patch), "triangles": int(len(patch)), "regions_bones": len(region)}
    with open(os.path.join(out_dir, f"{name}.skin_fit.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])

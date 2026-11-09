"""The body's inside and its skin, on the same 13,380 points and the same rig (epics volumes-outward and muscle-bodies): bones, the trunk's cavity and the muscles attached to the bones, and the first shape's skin moved out only where they need it. What lies between them and the skin is fat, and the percentage is reported, not forced (Rafael, 2026-11-09).
    hm.sh --gpu python human-model/tools/outward_skin.py BUILD_DIR NAME SHEET.json OUT_DIR [VOXEL=m]
SHEET.json is {"resolved": hmcore.character.resolve's result, "character": the character file}. Reads the build's skin, bones, rig and muscles.
Writes OUT_DIR/<NAME>.skin_fit.npz (the new body, for tools/body_layers.py), <NAME>.fat_table.json (its FAT_TABLE=), <NAME>.tissue.npz (its TISSUE=: the muscles and breast as grids), <NAME>.regions.json (body_walk.py's REGIONS=) and <NAME>.skin_fit.json (the report)."""
import json, os, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import warp as wp
from hmcore import body, fit, layers, meshgpu, muscle_bodies, outward, shapes

N_BODY = 13380  # as in blender/export_blend.py
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
MARGIN = 0.08  # m around the first shape: how far the new surface may reach
RING_REACH = 0.05  # m over which the move fades out to the cut rings
SKIN_OVER_LAYERS = 0.005  # m, declared: the least tissue kept over bones and muscles. Without it, bone points of the neutral woman came through the skin at rest


def past_cuts(point, planes, reach=0.35):
    """Whether a bone's centre lies beyond a cut's plane: the head's, a hand's or a foot's bones are left out of the layers."""
    return any((point - c) @ n > 0 and np.linalg.norm(point - c) < reach for c, n, _ in planes)


def main(build_dir, name, sheet_json, out_dir, overrides):
    voxel = json.load(open(os.path.join(DATA, "simulation.json")))["VOXEL_M"]
    for o in overrides:
        k, v = o.split("=")
        if k != "VOXEL":
            raise ValueError(f"unknown value {k}")
        voxel = float(v)
    os.makedirs(out_dir, exist_ok=True)
    sheet = json.load(open(sheet_json, encoding="utf-8"))
    fields, character = sheet["resolved"]["fields"], sheet["character"]
    sex = character["sex"]
    cfg = json.load(open(os.path.join(DATA, f"body_fat_{sex}.json")))
    base_fat_mm = dict(cfg["fat_mm"])
    fat_mm = dict(base_fat_mm)
    typed_fat = {zone: values["fat_mm"] for zone, values in (character.get("regions") or {}).items() if "fat_mm" in values}
    gluteus_factor = {}
    if character.get("gluteus"):
        table = json.load(open(os.path.join(DATA, "gluteus_shapes.json")))
        fat_mm = shapes.gluteus(fat_mm, character["gluteus"]["shape"], table)
        gluteus_factor = {"gl": table[character["gluteus"]["shape"]]["muscle"]}
    regions_out = {}

    meta = json.load(open(os.path.join(build_dir, f"{name}.export.json")))
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
    planes = body.cut_planes(skin, patch)
    region = [n for n, (v, _) in bones.items() if not past_cuts(v.mean(axis=0), planes)]

    wp.init()
    origin, shape, centres = layers.grid(skin[ids].min(axis=0) - MARGIN, skin[ids].max(axis=0) + MARGIN, voxel)
    keep = (~body.near_a_cut(centres, meta["bones"], planes)).reshape(shape)
    bv, bt, n = [], [], 0
    for b_name in region:
        v, t = bones[b_name]
        bv.append(v); bt.append(t + n); n += len(v)
    in_bone = meshgpu.Mesh(np.concatenate(bv), np.concatenate(bt)).inside(centres).reshape(shape)
    chest = np.concatenate([bones[x][0] for x in body.CHEST_BONES + body.SPINE_BONES[:12]])
    trunk = np.concatenate([bones[x][0] for x in body.TRUNK_BONES])
    behind = cfg["structure"]["cavity_behind_spine_front_mm"] / 1000
    front = centres[:, 1] < body.spine_front(bones, centres[:, 2]) + behind
    core = outward.core_mask(centres, chest, trunk, front, in_bone.ravel()).reshape(shape) & (keep | in_bone)
    muscles = muscle_bodies.select(json.load(open(os.path.join(build_dir, f"{name}.muscles.json"))))
    muscle = muscle_bodies.solids(muscles, origin, shape, voxel, fields["muscle"]["value"], gluteus_factor) & keep & ~core
    breast = np.zeros(shape, bool)
    inner = core | muscle | breast

    # The skin stays on the first shape and goes out only where what's inside needs it; the shapes and typed zones change the fat's depth from there
    inner_sdf = outward.signed_distance(inner | outward.grow(inner, SKIN_OVER_LAYERS, keep, voxel), voxel)
    depth_field = ndimage.distance_transform_edt(~inner) * voxel
    depth = np.zeros(len(skin))
    depth[ids] = np.maximum(outward.sample(depth_field, skin[ids], origin, voxel), 0.0)
    extra = np.zeros(len(skin))
    extra[ids] = [depth[v] * (fat_mm[zone[v]] / max(base_fat_mm[zone[v]], 1e-6) - 1) + (typed_fat[zone[v]] / 1000 - depth[v] if zone[v] in typed_fat else 0.0) for v in ids]
    move = np.zeros(len(skin))
    move[ids] = outward.push_needed(skin[ids], inner_sdf, origin, voxel) + extra[ids]
    move = body.smooth_on_surface(move, patch, len(skin), iters)
    normals = outward.vertex_normals(skin, patch)
    rings = layers.boundary_loops(patch)
    fade = outward.ring_fade(skin[ids], [skin[r] for r in rings], RING_REACH)
    new = skin.copy()
    new[ids] = skin[ids] + normals[ids] * (move[ids] * fade)[:, None]
    # Smoothing takes the skin back in over each bump, so whatever is still short goes out once more
    still = outward.push_needed(new[ids], inner_sdf, origin, voxel)
    new[ids] += outward.vertex_normals(new, patch)[ids] * (still * fade)[:, None]

    full = e["verts"].astype(np.float32).copy()
    full[:N_BODY] = new
    push = np.linalg.norm(new - skin, axis=1)
    np.savez_compressed(os.path.join(out_dir, f"{name}.skin_fit.npz"), verts=full, push=push.astype(np.float32), patch=patch.astype(np.int32))
    np.savez_compressed(os.path.join(out_dir, f"{name}.tissue.npz"), origin=origin, shape=np.array(shape), h=voxel, muscle=np.packbits(muscle.ravel()), breast=np.packbits(breast.ravel()))
    final = np.maximum(outward.sample(depth_field, new[ids], origin, voxel), 0.0)
    final_zone = zone[ids]
    with open(os.path.join(out_dir, f"{name}.fat_table.json"), "w") as f:
        json.dump({"fat_mm": {z: round(float(np.median(final[final_zone == z])) * 1000, 2) if (final_zone == z).any() else 0.0 for z in fat_mm}, "structure": {}}, f, indent=1)
    keys = {"young_pa": "young", "poisson": "poisson", "density": "density", "damping": "damping"}
    for z, values in (character.get("regions") or {}).items():
        typed = {keys[k]: v for k, v in values.items() if k in keys}
        if typed:
            regions_out.setdefault("fat", {}).setdefault(z, {}).update(typed)
    with open(os.path.join(out_dir, f"{name}.regions.json"), "w") as f:
        json.dump(regions_out, f, indent=1)
    pv = new[patch]
    area = float(np.linalg.norm(np.cross(pv[:, 1] - pv[:, 0], pv[:, 2] - pv[:, 0]), axis=1).sum() / 2)
    closed = meshgpu.Mesh(*layers.capped(new, patch)).inside(centres).reshape(shape)
    masses = outward.masses_kg(in_bone, core, muscle, closed & ~inner, closed, voxel, area)
    percent, target = outward.fat_percent(masses), fields["body_fat_percent"]["value"]
    report = {"name": name, "voxel_m": voxel, "target_percent": target, "percent": round(percent, 2), "reached_within_0_5": bool(abs(percent - target) <= 0.5), "masses_kg": {k: round(v, 2) for k, v in masses.items()},
              "muscle_scale": fields["muscle"]["value"], "muscles": len(muscles), "skin_points_moved": int(len(ids)), "largest_move_mm": round(float(push.max()) * 1000, 1), "mean_move_mm": round(float(push[ids].mean()) * 1000, 1),
              "ring_steps_mm": outward.ring_steps(skin, new, rings), "triangles_turned_over": outward.folded(skin, new, patch), "triangles": int(len(patch)), "regions_bones": len(region)}
    with open(os.path.join(out_dir, f"{name}.skin_fit.json"), "w") as f:
        json.dump(report, f, indent=1)
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])

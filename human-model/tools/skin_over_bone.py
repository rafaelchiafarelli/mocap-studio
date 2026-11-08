"""The woman's skin pushed out where a bone is too close under it (task muscle-physics/inside-out-skin/1).
    hm.sh --gpu python human-model/tools/skin_over_bone.py BUILD_DIR NAME TAPE.json OUT_DIR [depth.<prefix>=mm ...] [MAX_PUSH_MM=mm]
Reads the build's skin, bones and rig, the depths from data/skin_over_bone_<sex>.json, and the girths' heights from blender/body_tape.py's TAPE.json.
Writes OUT_DIR/01_skin_before.ply, 02_push.ply (coloured by how far each vertex moved), 03_skin_after.ply, <NAME>.skin_fit.npz (the new body
vertices, for tools/body_layers.py) and <NAME>.skin_fit.json (the table)."""
import importlib.util, json, os, sys, time
from types import SimpleNamespace
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import warp as wp
from hmcore import body, fit, layers, meshgpu, skinfit

N_BODY = 13380  # MakeHuman's body vertices come first; helpers follow, as in blender/export_blend.py
HERE = os.path.dirname(os.path.abspath(__file__))
# The editor's tape is plain numpy, but its package's __init__ needs Blender, so the module is loaded from its file
_spec = importlib.util.spec_from_file_location("hm_tape", os.path.join(HERE, "..", "hm_editor", "tape.py"))
tape = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tape)


def tape_topology(starts, sizes, loops):
    """The edges the tape's sections walk, built from the export's polygons: tape.Topology also wants vertex groups the export doesn't have."""
    polys = [loops[s:s + n].tolist() for s, n in zip(starts, sizes)]
    body_polys = [p for p in polys if max(p) < N_BODY]
    face_edges = np.full((len(body_polys), 4), -1, dtype=np.int32)
    index = {}
    for i, p in enumerate(body_polys):
        for k, a in enumerate(p[:4]):
            b = p[(k + 1) % len(p)]
            face_edges[i, k] = index.setdefault((a, b) if a < b else (b, a), len(index))
    return SimpleNamespace(face_edges=face_edges, edges=np.array(list(index), dtype=np.int32))


def girths(topology, verts, heights):
    """The trunk's girths at the tape's heights, as the tape takes them (around the outside, over hollows), and the left thigh's, in cm."""
    out = {}
    for key, z in heights.items():
        loops = tape._horizontal(topology, verts, z)
        if key in ("thigh", "knee", "calf", "ankle"):
            loop = tape._nearest_loop([l for l in loops if l[:, 0].mean() > 0], np.array([0.1, 0.0, z]))
        elif key in ("upper_arm", "wrist", "neck"):
            continue
        else:
            loop = tape._torso(loops)
        out[key] = round(tape.length_of(tape.hull_loop(loop, tape.UP)) * 100, 1) if loop is not None else None
    return out


def per_bone(owner, want, depth):
    rows = {}
    for name in np.unique(owner):
        m = owner == name
        rows[name] = {"least_tissue_mm": round(float(depth[m].min()) * 1000, 1), "wanted_mm": round(float(want[m][0]) * 1000, 1),
                      "points_outside": int((depth[m] < 0).sum()), "points_short": int((depth[m] < want[m] - 1e-3).sum())}
    return rows


def main(build_dir, name, tape_json, out_dir, overrides):
    os.makedirs(out_dir, exist_ok=True)
    meta = json.load(open(os.path.join(build_dir, f"{name}.export.json")))
    sex = "female" if meta["macros"]["gender"] < 0.5 else "male"
    cfg = json.load(open(os.path.join(HERE, "..", "data", f"skin_over_bone_{sex}.json")))
    table, max_push = cfg["least_depth_mm"], cfg["max_push_mm"]
    for o in overrides:
        k, v = o.split("=")
        if k == "MAX_PUSH_MM":
            max_push = float(v)
        elif k.startswith("depth.") and k[6:] in table:
            table[k[6:]] = float(v)
        else:
            raise ValueError(f"unknown value {k}")
    e = np.load(os.path.join(build_dir, f"{name}.export.npz"))
    skin = e["verts"].astype(float)[:N_BODY]
    tris = fit.triangles(e["starts"], e["sizes"], e["loops"])
    tris = tris[tris.max(axis=1) < N_BODY]
    b = np.load(os.path.join(build_dir, f"{name}.bones.npz"))
    bones = {k[:-3]: (b[k].astype(float), body.outward(b[k].astype(float), b[k[:-3] + "__f"].astype(np.int64))) for k in b.files if k.endswith("__v")}
    patch = body.cut_skin(skin, tris, meta["bones"], meta["groups"])

    wp.init()
    t0 = time.time()
    after, push, rec = skinfit.fit(skin, tris, patch, bones, meta["bones"], table, max_push / 1000, meshgpu.Mesh)
    seconds = time.time() - t0
    closed = meshgpu.Mesh(*layers.capped(skin, patch))
    before_depth, _, _ = skinfit.depth_under_skin(rec["points"], closed, meshgpu.Mesh(skin, patch))
    before, now = per_bone(rec["owner"], rec["want"], before_depth), per_bone(rec["owner"], rec["want"], rec["depth_after"])
    misplaced = {k: now[k] for k in rec["misplaced"]}
    still_short = {k: v for k, v in now.items() if v["points_short"] > 0 and k not in rec["misplaced"]}

    heights = json.load(open(tape_json, encoding="utf-8"))["girth_z_m"]
    topo = tape_topology(e["starts"], e["sizes"], e["loops"])
    g0, g1 = girths(topo, skin, heights), girths(topo, after, heights)
    zone = body.zones(skin, np.arange(len(skin))[np.isin(np.arange(len(skin)), np.unique(patch))], meta["bones"], bones)
    zone_of = dict(zip(np.unique(patch), zone))
    top = np.argsort(push)[::-1][:200]
    where = {}
    for v in top:
        where[zone_of.get(v, "?")] = max(where.get(zone_of.get(v, "?"), 0), round(float(push[v]) * 1000, 1))

    ids = np.unique(patch)
    t = np.clip(push[ids] / max(max_push / 1000, 1e-9), 0, 1)[:, None]
    colors = (1 - t) * np.array([235, 235, 235]) + t * np.array([220, 40, 30])
    local = np.full(len(skin), -1)
    local[ids] = np.arange(len(ids))
    layers.write_ply(f"{out_dir}/01_skin_before.ply", skin[ids], local[patch])
    layers.write_ply(f"{out_dir}/02_push.ply", after[ids], local[patch], colors)
    layers.write_ply(f"{out_dir}/03_skin_after.ply", after[ids], local[patch])
    full = e["verts"].astype(np.float32).copy()
    full[:N_BODY] = after
    np.savez_compressed(f"{out_dir}/{name}.skin_fit.npz", verts=full, push=push.astype(np.float32), patch=patch.astype(np.int32))
    report = {"name": name, "declared": {"least_depth_mm": table, "max_push_mm": max_push}, "seconds": round(seconds, 1), "rounds": rec["rounds"],
              "largest_push_mm": round(float(push.max()) * 1000, 1), "vertices_moved_over_1mm": int((push > 1e-3).sum()),
              "largest_push_by_zone_mm": dict(sorted(where.items(), key=lambda kv: -kv[1])),
              "girths_cm": {k: {"before": g0[k], "after": g1[k], "change": round(g1[k] - g0[k], 1) if g0[k] and g1[k] else None} for k in g0},
              "bones_misplaced_left_alone": misplaced, "bones_still_short": still_short,
              "bones_before": {k: v for k, v in before.items() if v["points_short"]}, "bones_after": now}
    with open(f"{out_dir}/{name}.skin_fit.json", "w") as fh:
        json.dump(report, fh, indent=1)
    print(json.dumps({k: report[k] for k in ("seconds", "rounds", "largest_push_mm", "vertices_moved_over_1mm", "largest_push_by_zone_mm", "girths_cm", "bones_misplaced_left_alone", "bones_still_short")}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])

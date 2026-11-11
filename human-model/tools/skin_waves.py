"""The waves on a walking skin. Args: DUMP.npz OUT.npz [NAME.key=value ...]. Values come from data/skin_waves.json; a run can change one, as breast.gain=0.8.
Writes offsets (frames x vertices, metres along the rest normal) and a report per region, in the image with Docker: hm.sh python human-model/tools/skin_waves.py ..."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hmcore import deltamush as dm  # noqa: E402
from hmcore import foot_impact as fi  # noqa: E402
from hmcore import folds as fd  # noqa: E402
from hmcore import skin_waves as sw  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data" / "skin_waves.json"


def load_table(overrides):
    table = json.loads(DATA.read_text(encoding="utf-8"))
    for item in overrides:
        name, value = item.split("=")
        region, key = name.split(".")
        table[region][key] = float(value)  # also impact.size and the like
    return table


def posed_normals(positions, tris):
    return np.stack([dm.vertex_normals(p.astype(float), tris) for p in positions]).astype(np.float32)


def main(args) -> int:
    if len(args) < 2:
        print(__doc__)
        return 2
    d = np.load(args[0])
    positions, rest, tris, fps = d["positions"].astype(float), d["rest"].astype(float), d["tris"], float(d["fps"])
    table = load_table(args[2:])
    adjacency = dm.neighbours(tris, len(rest))
    weights = {k[2:]: d[k].astype(float) for k in d.files if k.startswith("w_")}
    marks = {"hip_joint": float(d["marks"][0]), "ribs": float(d["marks"][1])}
    masks = sw.regions(rest, dm.vertex_normals(rest, tris), weights, marks, adjacency)
    values = sw.values_from(masks, table, len(rest))
    normals = posed_normals(positions, tris)
    drive = sw.inertia(positions, normals, fps)
    impact = table["impact"]
    events, field = [], None
    if impact["size"] > 0:
        edges = fd.edges_of(tris)
        heels = d["feet"][:, :, 2]
        events = [fi.touchdowns(heels[:, i].astype(float), fps) for i in range(2)]
        distance = []
        for foot in d["foot_rest"].astype(float):
            sources = np.nonzero(np.linalg.norm(rest - foot, axis=1) < 0.07)[0]
            distance.append(fd.surface_distance(rest, edges, sources.tolist(), 3.0))
        field = fi.pulses(events, normals, distance, fps, size=impact["size"], width=impact["width_s"], speed=impact["speed"], reach=impact["reach"])
    out, steps = sw.simulate(rest, tris, values, drive, fps, pulses=field)
    dent = np.zeros_like(out)
    if "hands" in d.files:
        dent = sw.contact_dent(positions, d["hands"].astype(float), d["arm"].astype(float), adjacency)
        out = out - dent
    report = {}
    for region, mask in masks.items():
        where = mask > 0.5
        report[region] = {"vertices": int(where.sum()), "peak_mm": float(np.abs(out[:, where]).max() * 1000) if where.any() else 0.0, "rms_mm": float(np.sqrt((out[:, where] ** 2).mean()) * 1000) if where.any() else 0.0}
    np.savez_compressed(args[1], offsets=out, rest=rest.astype(np.float32), tris=tris, first=d["first"], **{f"mask_{k}": v.astype(np.float32) for k, v in masks.items()})
    Path(args[1]).with_suffix(".json").write_text(json.dumps({"substeps": steps, "contact_frames": int((dent.max(axis=1) > 0.0005).sum()), "deepest_dent_mm": float(dent.max() * 1000), "touchdowns_s": events, "peak_drive_ms2": float(np.percentile(np.abs(drive), 99.9)), "regions": report, "table": table}, indent=1), encoding="utf-8")
    print("passos por quadro", steps, "toques no chão", [len(e) for e in events], "quadros com a mão encostada", int((dent.max(axis=1) > 0.0005).sum()), "afundamento máximo %.1f mm" % (dent.max() * 1000))
    for region, r in report.items():
        print(f"{region:10} {r['vertices']:5} vertices  pico {r['peak_mm']:6.1f} mm  rms {r['rms_mm']:5.2f} mm")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

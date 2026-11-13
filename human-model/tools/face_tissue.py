"""The sway of the face's soft parts: cheeks, jowls and lips, each a mass on a spring to its place, pushed by the inertia of its own motion (head turns and nods, the jaw and
the mouth's shapes) and joined to its neighbours (initiative animation-face, epic face-soft-tissue). Args: DUMP.npz OUT.npz [NAME.key=value ...].
DUMP from blender/face_dump.py; values from data/face_tissue.json, a run can change one, as cheek.gain=0.5. Writes offsets (frames x vertices, metres along the rest normal)
for blender/wave_bake.py, and a report per region. In the image with Docker: hm.sh python human-model/tools/face_tissue.py ..."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hmcore import deltamush as dm  # noqa: E402
from hmcore import skin_waves as sw  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data" / "face_tissue.json"


def main(args) -> int:
    if len(args) < 2:
        print(__doc__)
        return 2
    d = np.load(args[0])
    positions, rest, tris, fps = d["positions"].astype(float), d["rest"].astype(float), d["tris"], float(d["fps"])
    table = json.loads(DATA.read_text(encoding="utf-8"))
    for item in args[2:]:
        name, value = item.split("=")
        region, key = name.split(".")
        table[region][key] = float(value)
    adjacency = dm.neighbours(tris, len(rest))
    weights = {k[2:]: d[k].astype(float) for k in d.files if k.startswith("w_")}
    masks = sw.face_regions(weights, adjacency, len(rest))
    values = sw.values_from(masks, table, len(rest))
    normals = np.stack([dm.vertex_normals(p, tris) for p in positions])
    drive = sw.inertia(positions, normals, fps)
    out, steps = sw.simulate(rest, tris, values, drive, fps, limit=table["limit_m"])
    report = {}
    for region, mask in masks.items():
        where = mask > 0.5
        report[region] = {"vertices": int(where.sum()), "peak_mm": float(np.abs(out[:, where]).max() * 1000) if where.any() else 0.0,
                          "rms_mm": float(np.sqrt((out[:, where] ** 2).mean()) * 1000) if where.any() else 0.0,
                          "drive_p99_ms2": float(np.percentile(np.abs(drive[:, where]), 99)) if where.any() else 0.0}
    np.savez_compressed(args[1], offsets=out, rest=rest.astype(np.float32), tris=tris, first=d["first"], **{f"mask_{k}": v.astype(np.float32) for k, v in masks.items()})
    Path(args[1]).with_suffix(".json").write_text(json.dumps({"substeps": steps, "regions": report, "table": table}, indent=1), encoding="utf-8")
    print("passos por quadro", steps)
    for region, r in report.items():
        print(f"{region:6} {r['vertices']:5} vertices  pico {r['peak_mm']:5.2f} mm  rms {r['rms_mm']:5.2f} mm  aceleracao p99 {r['drive_p99_ms2']:6.1f} m/s2")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

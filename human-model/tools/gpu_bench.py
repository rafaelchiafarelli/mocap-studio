"""What soft tissue costs on the GPU (task muscle-physics/thigh/1): a cube of soft tetrahedra dropped on a floor, at several sizes.
    hm.sh --gpu python human-model/tools/gpu_bench.py OUT_DIR [NAME=value overrides the constants below]
Writes OUT_DIR/gpu_bench.json and one gpu_bench_<device>_<tetrahedra>.json per run, and prints the table."""
import json, os, sys, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import warp as wp
from hmcore import layers, xpbd

SIDE = 0.2  # m
DROP = 0.05  # m above the floor
CELLS = [12, 26, 38, 55]  # per side: 6 tetrahedra per cell, so about 10,000, 105,000, 330,000 and 1,000,000
CPU_CELLS = [12]  # the CPU is run on the smallest only
FPS = 24.0
SUBSTEPS = 20  # per frame
SECONDS = 1.0
DENSITY = 1000.0  # kg/m3
EDGE_COMPLIANCE = 1e-6  # m/N: soft
VOLUME_COMPLIANCE = 0.0  # holds its volume
DAMPING = 2.0  # 1/s


def cube(cells):
    h = SIDE / cells
    nodes, tets, _, _ = layers.tetrahedra(np.ones((cells,) * 3, bool), np.array([-SIDE / 2, -SIDE / 2, DROP]), h)
    return nodes, tets


def run(cells, device):
    nodes, tets = cube(cells)
    s = xpbd.Solver(nodes, tets, DENSITY, EDGE_COMPLIANCE, VOLUME_COMPLIANCE, damping=DAMPING, floor=0.0, device=device)
    dt = 1 / FPS
    s.step(dt, SUBSTEPS)  # the first frame compiles the kernels: not timed
    wp.synchronize_device(device)
    frames = int(SECONDS * FPS) - 1
    t0 = time.perf_counter()
    for _ in range(frames):
        s.step(dt, SUBSTEPS)
    wp.synchronize_device(device)
    ms = (time.perf_counter() - t0) / frames * 1000
    x = s.positions()
    peak = wp.get_mempool_used_mem_high(device) / 2 ** 20 if device.startswith("cuda") else None
    return {"device": device, "tetrahedra": int(len(tets)), "nodes": int(len(nodes)), "edges": int(len(s.edges)),
            "ms_per_frame": round(ms, 2), "ms_per_substep": round(ms / SUBSTEPS, 3), "substeps_per_frame": SUBSTEPS,
            "peak_vram_mib": round(peak, 1) if peak is not None else None, "volume_ratio_at_end": round(s.volume() / s.rest_volume, 4),
            "lowest_z_mm": round(float(x[:, 2].min()) * 1000, 2), "highest_z_mm": round(float(x[:, 2].max()) * 1000, 1),
            "finite": bool(np.isfinite(x).all())}


def main(out_dir, overrides):
    g = globals()
    for o in overrides:
        k, v = o.split("=")
        g[k] = type(g[k])(float(v))
    os.makedirs(out_dir, exist_ok=True)
    wp.init()
    rows = []
    for device, sizes in (("cuda:0", CELLS), ("cpu", CPU_CELLS)):
        for cells in sizes:
            r = run(cells, device)
            rows.append(r)
            with open(f"{out_dir}/gpu_bench_{device.replace(':', '')}_{r['tetrahedra']}.json", "w") as f:
                json.dump(r, f, indent=1)
            print(json.dumps(r), flush=True)
    declared = {k: g[k] for k in ("SIDE", "DROP", "FPS", "SUBSTEPS", "SECONDS", "DENSITY", "EDGE_COMPLIANCE", "VOLUME_COMPLIANCE", "DAMPING")}
    with open(f"{out_dir}/gpu_bench.json", "w") as f:
        json.dump({"gpu": wp.get_device("cuda:0").name, "warp": wp.__version__, "declared": declared, "runs": rows}, f, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])

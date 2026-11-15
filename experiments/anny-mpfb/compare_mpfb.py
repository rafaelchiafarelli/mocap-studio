"""Test 1b: Anny with MPFB's formula (mpfb_anny.py) against MPFB 2.0.18's own meshes.
    experiments/anny-mpfb/run.sh python experiments/anny-mpfb/compare_mpfb.py REF.npz REF.json OUT.json
Vertices compared as they are, after one fixed change of axes and units found on the default body."""
import json, sys, time
import numpy as np
import torch
sys.path.insert(0, "experiments/anny-mpfb")
import mpfb_anny

ref = np.load(sys.argv[1])
meta = json.load(open(sys.argv[2]))
t0 = time.time()
m = mpfb_anny.model(dtype=torch.float64)
report = {"build_s": round(time.time() - t0, 1), "cases": {}}


def procrustes(a, b):
    ca, cb = a.mean(0), b.mean(0)
    U, S, Vt = np.linalg.svd((b - cb).T @ (a - ca))
    D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
    R = U @ D @ Vt
    s = (S * np.diag(D)).sum() / ((a - ca) ** 2).sum()
    return R, cb - s * R @ ca, s


align = None
for name, case in meta.items():
    with torch.no_grad():
        av = mpfb_anny.forward(m, case["macros"], case["targets"])["vertices"][0].numpy()
    mp = ref[name]
    if align is None:
        align = procrustes(av, mp)
        report["alignment"] = {"R": np.round(align[0], 5).tolist(), "t_mm": np.round(align[1] * 1000, 2).tolist(), "scale": float(align[2])}
    R, t, s = align
    aa = (s * (R @ av.T)).T + t
    shift = (mp - aa)[:13380].mean(0)
    d = np.linalg.norm(aa + shift - mp, axis=1)[:13380]
    row = {"shift_mm": np.round(shift * 1000, 2).tolist(), "mean_mm": round(float(d.mean()) * 1000, 3), "max_mm": round(float(d.max()) * 1000, 3), "worst_vertex": int(d.argmax()),
           "height_mpfb_m": round(float(np.ptp(mp[:13380, 2])), 4)}
    report["cases"][name] = row
    print(f"{name:20s} media {row['mean_mm']:8.3f} mm  max {row['max_mm']:8.3f} mm  alt {row['height_mpfb_m']}  translacao {row['shift_mm']}")
json.dump(report, open(sys.argv[3], "w"), indent=1)
print("alinhamento", report["alignment"])

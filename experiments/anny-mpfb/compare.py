"""Test 1: does Anny with the MakeHuman topology give MPFB 2.0.18's body for the same macros and targets?
    experiments/anny-mpfb/run.sh python experiments/anny-mpfb/compare.py REF.npz REF.json OUT.json
REF comes from mpfb_reference.py (Blender). Per case: vertex count, and the distance from each MPFB vertex to Anny's,
after one rigid alignment (rotation, translation, and a scale reported apart) found on the default case and kept for all."""
import json, sys, time
import numpy as np
import torch
import anny

ref_npz, ref_json, out_path = sys.argv[1:4]
ref = np.load(ref_npz)
meta = json.load(open(ref_json))
report = {"anny_version": getattr(anny, "__version__", "?")}


def build(**kw):
    t = time.time()
    m = anny.Anny(topology="makehuman", rig="makehuman", local_changes="all", phenotypes="all", **kw).to(dtype=torch.float64)
    return m, time.time() - t


model, secs = build()
report["build_s"] = round(secs, 1)
report["phenotype_labels"] = list(model.phenotype_labels)
report["local_change_count"] = len(model.local_change_labels)
labels = set(model.local_change_labels)
report["local_change_sample"] = sorted(labels)[:12]
report["hips_labels"] = sorted(l for l in labels if "hip" in l)
print("phenotypes", report["phenotype_labels"], "locals", report["local_change_count"])

pose = torch.eye(4, dtype=torch.float64)[None, None].repeat(1, model.bone_count, 1, 1)


def anny_verts(macros, targets):
    ph = {}
    for k in model.phenotype_labels:
        if k in macros:
            ph[k] = float(macros[k])
        elif k in macros.get("race", {}):
            ph[k] = float(macros["race"][k])
        else:
            ph[k] = 0.5
    loc = {}
    missing = []
    for t, v in targets.items():
        if t in labels:
            loc[t] = float(v)
        else:
            missing.append(t)
    with torch.no_grad():
        o = model(pose_parameters=pose, phenotype_kwargs={k: torch.tensor([v], dtype=torch.float64) for k, v in ph.items()},
                  local_changes_kwargs={k: torch.tensor([v], dtype=torch.float64) for k, v in loc.items()})
    return o["vertices"][0].numpy(), ph, missing


def procrustes(a, b):
    """R, t, s with s*R@a+t ~ b."""
    ca, cb = a.mean(0), b.mean(0)
    A, B = a - ca, b - cb
    U, S, Vt = np.linalg.svd(B.T @ A)
    d = np.sign(np.linalg.det(U @ Vt))
    D = np.diag([1, 1, d])
    R = U @ D @ Vt
    s = (S * np.diag(D)).sum() / (A ** 2).sum()
    return R, cb - s * R @ ca, s


cases = {}
align = None
for name in meta:
    mp = ref[name]
    av, ph, missing = anny_verts(meta[name]["macros"], meta[name]["targets"])
    row = {"mpfb_vertices": len(mp), "anny_vertices": len(av), "missing_targets": missing, "phenotypes": ph}
    if len(av) == len(mp):
        if align is None:
            align = procrustes(av, mp)
            report["alignment"] = {"R": np.round(align[0], 4).tolist(), "t": np.round(align[1], 4).tolist(), "scale": round(float(align[2]), 6)}
        R, t, s = align
        d = np.linalg.norm((s * (R @ av.T)).T + t - mp, axis=1)
        aa = (s * (R @ av.T)).T + t
        R2, t2, s2 = procrustes(aa[:13380], mp[:13380])
        d2 = np.linalg.norm((s2 * (R2 @ aa.T)).T + t2 - mp, axis=1)[:13380]
        row.update({"own_align_mean_mm": round(float(d2.mean()) * 1000, 3), "own_align_max_mm": round(float(d2.max()) * 1000, 3), "own_scale": round(float(s2), 4),
                    "shift_mm": np.round(t2 * 1000, 1).tolist(), "height_anny_m": round(float(np.ptp(aa[:13380, 2])), 4)})
        body = d[:13380]
        row.update({"body_mean_mm": round(float(body.mean()) * 1000, 3), "body_max_mm": round(float(body.max()) * 1000, 3),
                    "all_max_mm": round(float(d.max()) * 1000, 3), "height_mpfb_m": round(float(np.ptp(mp[:13380, 2])), 4)})
    cases[name] = row
    print(name, {k: v for k, v in row.items() if k != "phenotypes"})
report["cases"] = cases
json.dump(report, open(out_path, "w"), indent=1)

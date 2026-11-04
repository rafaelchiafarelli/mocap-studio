"""How much stored data replaces the fields: python fit_fields.py FIELDS.npz ACTIV.npz REPORT.json. Time is on this machine's CPU; nothing here needs the GPU."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import retire


def main(fields_npz, activ_npz, report):
    f = np.load(fields_npz)
    names = sorted(k for k in f.files if k.startswith("F_"))
    F = np.stack([f[k] for k in names]).astype(float)
    activ = np.load(activ_npz)["activ_b"]
    rows = []
    full = np.tensordot(activ, F, axes=1)
    for k in (5, 10, 15, 20, 30, 40, len(names)):
        basis, coeff = retire.compress(F, k=k)
        rms, mx = retire.error_mm(F, basis, coeff)
        t = time.perf_counter()
        rec = np.array([retire.reconstruct(basis, coeff, a) for a in activ[:200]])
        ms = (time.perf_counter() - t) / 200 * 1000
        d = np.linalg.norm(rec - full[:200], axis=2)
        rows.append({"components": k, "field_rms_mm": rms, "field_max_mm": mx, "take_rms_mm": float(np.sqrt((d ** 2).mean()) * 1000), "take_max_mm": float(d.max() * 1000), "ms_per_frame": ms, "stored_mb": (basis.nbytes + coeff.nbytes) / 1e6})
        print(rows[-1])
    json.dump(rows, open(report, "w"), indent=0)


if __name__ == "__main__":
    main(*sys.argv[1:])

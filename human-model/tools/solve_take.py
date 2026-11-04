"""Muscle activations for a take, two ways: python solve_take.py FIELDS.npz TAKE.npz EXPORT.npz EXPORT.json MOUTH_DATA.json TRACKER.csv OUT.npz IPD_M REPORT.json
A: fit each expression shape with muscle fields, then use the take's own shape values (the faders' result carried by muscles).
B: solve directly from tracked landmarks, as the plan's least-effort idea."""
import csv, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import activation, skeleton, tongue

# Shapes muscles can't be asked to make: jaw motion is a bone, gaze is the eyes, tongue and lip bite have their own controls.
KEEP = ("jaw", "eyeLook", "tongue", "lipBite")
RESIDUAL_LIMIT = 0.6
CHOSEN_EFFORT = 1e-5


def read_tracker(path):
    rows = [r for r in csv.reader(open(path, newline="")) if r][1:]
    return np.array([[float(v) for v in r[25:25 + 204]] for r in rows]).reshape(len(rows), 68, 3)[:, :, :2]


def rig_vertex(ind, name, end, skin):
    p = np.array(ind["rig"][name][end])
    return int(np.argmin(np.linalg.norm(skin[:13380] - p, axis=1)))


def main(fields_npz, take_npz, export_npz, export_json, mouth_json, tracker_csv, out, ipd, report):
    ipd = float(ipd)
    f = np.load(fields_npz)
    t = np.load(take_npz)
    ids = f["ids"]
    muscles = sorted(k[2:] for k in f.files if k.startswith("F_"))
    fields = np.stack([f[f"F_{m}"] for m in muscles])
    names = [str(n) for n in t["names"]]
    values = t["values"]
    frames = values.shape[0]
    C = {}
    fits = {}
    for j, n in enumerate(names):
        if values[:, j].max() < 0.01 or n.startswith(KEEP):
            continue
        shape = t[f"S_{n}"][ids]
        x, res = activation.shape_fit(fields, shape)
        fits[n] = {"residual": res, "peak_mm": float(np.linalg.norm(shape, axis=1).max() * 1000), "top": [(muscles[i], round(float(x[i]), 2)) for i in np.argsort(-x)[:4] if x[i] > 0.02]}
        C[n] = x
    replaced = [n for n in C if fits[n]["residual"] < RESIDUAL_LIMIT]
    activ_a = np.zeros((frames, len(muscles)))
    for n in replaced:
        activ_a += values[:, names.index(n)][:, None] * C[n][None, :]
    activ_a = np.clip(activ_a, 0, 1.2)
    # B: from landmarks
    ind = skeleton.load_individual(export_npz, export_json)
    L = read_tracker(tracker_csv)
    vertex_of = {}
    for d, (bone, end) in activation.LANDMARKS.items():
        if bone in ind["rig"]:
            v = rig_vertex(ind, bone, end, ind["skin"])
            if v in set(ids.tolist()):
                vertex_of[d] = v
    mouth = json.load(open(mouth_json))
    n = min(len(L), frames)
    jaw = np.array(mouth["tracked_jaw"][:n])
    # what jaw opening does to the tracked points: the jawOpen shape at the vertices
    pos = {v: i for i, v in enumerate(ids.tolist())}
    jaw_shape = t["S_jawOpen"][ids]
    jaw_lower = np.concatenate([[jaw_shape[pos[v], 0], jaw_shape[pos[v], 2]] for v in vertex_of.values()])
    L = np.stack([np.apply_along_axis(lambda c: np.convolve(np.pad(c, 2, mode="edge"), np.ones(5) / 5, mode="valid"), 0, L[:n, i]) for i in range(L.shape[1])], axis=1)
    results = {}
    best = None
    rest = (10, 40)
    for effort in (0.0, 1e-5, 1e-4, 1e-3):
        a, residual = activation.solve_track(L, rest, vertex_of, fields, ids, ipd, effort, jaw_open=jaw, jaw_lower=jaw_lower)
        results[str(effort)] = {"mean_total_activation": float(a.sum(axis=1).mean()), "active_muscles_mean": float((a > 0.05).sum(axis=1).mean()), "median_residual": float(np.median(residual)), "jitter": float(np.median(np.abs(np.diff(a, axis=0)).sum(axis=1)))}
        if effort == CHOSEN_EFFORT:
            best = a
    tong = tongue.track(mouth["script"], frames, mouth["fps"])
    # Hybrid: the faders stay, and muscles add what the shapes barely move: cheeks and folds with the smile, forehead lines with the brows.
    hybrid = np.zeros((frames, len(muscles)))
    val = lambda *ns: sum(values[:, names.index(x)] for x in ns if x in names)
    for side, arkit in (("L", "Left"), ("R", "Right")):
        smile = val(f"mouthSmile{arkit}")
        for muscle_name, gain, src in ((f"orbicularis_oculi_orbital_{side}", 0.6, smile), (f"zygomaticus_major_{side}", 0.25, smile), (f"frontalis_medial_{side}", 0.5, val("browInnerUp")), (f"frontalis_lateral_{side}", 0.5, val(f"browOuterUp{arkit}")), (f"corrugator_{side}", 0.6, val(f"browDown{arkit}"))):
            hybrid[:, muscles.index(muscle_name)] = np.clip(gain * src, 0, 1)
    np.savez_compressed(out, muscles=np.array(muscles), activ_a=activ_a, activ_b=best, activ_h=hybrid, tongue=tong, replaced=np.array(replaced), kept=np.array([x for x in names if x not in replaced]))
    json.dump({"fits": fits, "replaced": replaced, "track": results, "landmarks_used": len(vertex_of)}, open(report, "w"), indent=0)
    print("fit", {k: round(v["residual"], 2) for k, v in fits.items()})
    print("replaced", len(replaced), "of", len(fits))
    print("track", results)


if __name__ == "__main__":
    main(*sys.argv[1:])

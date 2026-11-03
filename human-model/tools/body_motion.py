"""Capture to bone directions in the model's frame, and a report on the capture's quality: python body_motion.py BODY_3D.npy BODY_3D.csv OUT.json REPORT.json FPS [character_hip_height_m]"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import retarget


def main(npy, csv_path, out, report, fps, hip_h=0.92):
    pts = np.load(npy)
    head = open(csv_path).readline().strip().split(",")
    names = [h.rsplit("_", 1)[0].replace("body_", "") for h in head[::3]]
    idx = {n: i for i, n in enumerate(names)}
    frames = []
    # capture axes to model axes: from the first frames' mean trunk, so body position in the room is kept relative
    p0 = np.nanmean(pts[:5], axis=0)
    W = retarget.facing_frame(p0[idx["left_hip"]], p0[idx["right_hip"]], p0[idx["left_shoulder"]], p0[idx["right_shoulder"]])
    mid0 = (p0[idx["left_hip"]] + p0[idx["right_hip"]]) / 2
    leg = np.nanmean(np.linalg.norm(p0[idx["left_hip"]] - p0[idx["left_knee"]]) + np.linalg.norm(p0[idx["left_knee"]] - p0[idx["left_ankle"]]))
    unit = hip_h / leg  # capture units to the character's size, for the root only
    for t in range(pts.shape[0]):
        P = lambda n: W @ pts[t, idx[n]]
        lh, rh, ls, rs = P("left_hip"), P("right_hip"), P("left_shoulder"), P("right_shoulder")
        trunk = retarget.facing_frame(lh, rh, ls, rs).T
        dirs = {}
        for bone, (a, b) in retarget.BODY_CHAINS.items():
            d = P(b) - P(a)
            if np.isfinite(d).all():
                dirs[bone] = d.tolist()
        root = ((lh + rh) / 2 - W @ mid0) * unit
        frames.append({"trunk": trunk.tolist(), "dirs": dirs, "root": root.tolist()})
    json.dump({"fps": float(fps), "frames": frames}, open(out, "w"))
    q = {"frames": int(pts.shape[0]), "unit_to_m": float(unit), "segments": {}, "jitter": {}, "missing_fraction": float(np.isnan(pts[:, [idx[n] for n in ("left_hip", "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle", "left_wrist", "right_wrist")]]).mean())}
    for bone, (a, b) in retarget.BODY_CHAINS.items():
        m, cv = retarget.bone_length_stats(pts, idx[a], idx[b])
        q["segments"][bone] = {"mean_mm": m, "variation_pct": cv * 100}
    for n in ("left_wrist", "left_ankle", "left_hip", "nose"):
        q["jitter"][n] = retarget.jitter_mm(pts[:, idx[n]])
    json.dump(q, open(report, "w"), indent=0)
    print(json.dumps(q)[:1400])


if __name__ == "__main__":
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3], a[4], float(a[5]) if len(a) > 5 else 0.92)

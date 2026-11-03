"""raw blendshape CSV -> cleaned JSON: fill lost frames, take out each channel's resting level, smooth, apply gains."""
import csv, json, sys
import numpy as np
raw, out, cfg = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
rows = list(csv.DictReader(open(raw)))
names = [n for n in rows[0] if n not in ("frame", "detected", "yaw_deg", "pitch_deg", "_neutral")]
data = np.array([[float(r[n]) if r["detected"] == "1" else np.nan for n in names] for r in rows])
for c in range(data.shape[1]):
    bad = np.isnan(data[:, c]); data[bad, c] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), data[~bad, c])
def smooth(v, s):
    r = int(3 * s + 1); k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    return np.convolve(np.pad(v, r, mode="edge"), k, "valid")
res = {}
for c, n in enumerate(names):
    v = data[:, c]
    rest = np.percentile(v, cfg["rest_percentile"]) if not n.startswith("eyeLook") else 0.0
    v = np.clip((v - rest) / max(1 - rest, 1e-6), 0, 1)
    v = smooth(v, cfg["sigma_blink"] if n.startswith("eyeBlink") else cfg["sigma"])
    v = np.clip(v * cfg["gain"].get(n, 1.0), 0, 1)
    res[n] = [round(float(x), 4) for x in v]
json.dump({"fps_num": 24000, "fps_den": 1001, "frames": len(rows), "config": cfg, "channels": res}, open(out, "w"))
for n in ("jawOpen", "eyeBlinkLeft", "eyeBlinkRight", "eyeSquintLeft", "mouthSmileLeft", "mouthPressLeft", "browInnerUp", "browOuterUpRight"):
    a = np.array(res[n]); print(f"{n:18s} mean {a.mean():.2f} p95 {np.percentile(a,95):.2f} max {a.max():.2f} peak_frame {int(a.argmax())+1}")

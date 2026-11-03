"""raw blendshape CSV -> cleaned JSON. Fills lost frames, removes each channel's resting bias, smooths,
then maps MediaPipe's readings onto this face: gains per channel and the mouth rules in the config."""
import csv, json, sys
import numpy as np
raw, out, cfg = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
rows = list(csv.DictReader(open(raw)))
names = [n for n in rows[0] if n not in ("frame", "detected", "yaw_deg", "pitch_deg", "_neutral")]
data = np.array([[float(r[n]) if r["detected"] == "1" else np.nan for n in names] for r in rows])
for c in range(data.shape[1]):
    bad = np.isnan(data[:, c])
    if bad.any():
        data[bad, c] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), data[~bad, c])
def smooth(v, s):
    r = int(3 * s + 1); k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    return np.convolve(np.pad(v, r, mode="edge"), k, "valid")
res = {}
for c, n in enumerate(names):
    v = data[:, c]
    pct = cfg["rest_percentile_look"] if n.startswith("eyeLook") else cfg["rest_percentile"]
    rest = np.percentile(v, pct)
    v = np.clip((v - rest) / max(1 - rest, 1e-6), 0, 1)
    v = smooth(v, cfg["sigma_blink"] if n.startswith("eyeBlink") else cfg["sigma"])
    gain = next((g for prefix, g in cfg["gain"].items() if n.startswith(prefix)), 1.0)
    res[n] = np.clip(v * gain, 0, 1)
jaw = res["jawOpen"]
for n in ("mouthSmileLeft", "mouthSmileRight"):  # a wide-open mouth reads partly as a smile
    res[n] = res[n] * np.clip(1 - cfg["smile_suppress_by_jaw"] * jaw, 0, 1)
for side in ("Left", "Right"):  # gaze-down also shuts the lid; a blink must not count twice
    res["eyeLookDown" + side] = res["eyeLookDown" + side] * np.clip(1 - res["eyeBlink" + side], 0, 1)
    res["mouthLowerDown" + side] = np.clip(res["mouthLowerDown" + side] + cfg["lip_part_from_jaw"] * jaw, 0, 1)
    res["mouthUpperUp" + side] = np.clip(res["mouthUpperUp" + side] + cfg["lip_part_from_jaw"] * jaw, 0, 1)
res = {k: [round(float(x), 4) for x in v] for k, v in res.items()}
json.dump({"fps_num": 24000, "fps_den": 1001, "frames": len(rows), "config": cfg, "channels": res}, open(out, "w"))
for n in ("jawOpen", "eyeBlinkLeft", "eyeLookDownLeft", "eyeSquintLeft", "mouthSmileLeft", "mouthRollUpper", "browDownLeft", "mouthUpperUpLeft"):
    a = np.array(res[n]); print(f"{n:18s} mean {a.mean():.2f} p95 {np.percentile(a,95):.2f} max {a.max():.2f}")

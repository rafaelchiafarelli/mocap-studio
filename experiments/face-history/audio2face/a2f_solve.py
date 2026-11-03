"""Audio2Face geometry -> ARKit weights plus eye rotations, for a character whose eyeLook shapes have measured angles.
Skin: bounded least squares against NVIDIA's own 52-pose rig, using its config. Eyes: SDK rotations + saccades -> eyeLook weights."""
import json, sys
import numpy as np
from scipy.linalg import cholesky, solve_triangular
from scipy.optimize import lsq_linear
model, geo, out, actor, cfg = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], json.loads(sys.argv[5])
pred = np.load(geo)
skin = pred[:, :72006]; eyes = pred[:, 88827:]
z = np.load(f"{model}/bs_skin_{actor}.npz"); c = json.load(open(f"{model}/bs_skin_config_{actor}.json"))["blendshape_params"]
names = [n.decode() if isinstance(n, bytes) else str(n) for n in np.atleast_1d(z["poseNames"]).ravel().tolist()]
if len(names) == 1: names = names[0].split()
neutral = z["neutral"].ravel()
poses = [n for n in names if n != "neutral"]
assert len(poses) == c["numPoses"], (len(poses), c["numPoses"])
active = [i for i, a in enumerate(c["bsSolveActivePoses"]) if a]
A = np.stack([z[poses[i]].ravel() for i in active], axis=1).astype(np.float64)  # the npz stores poses as deltas from neutral
print("active poses", len(active), "inactive", [poses[i] for i, a in enumerate(c["bsSolveActivePoses"]) if not a])
print("pose delta rms check: skin target rms", float(np.sqrt((skin ** 2).mean())), "rig mean pose rms", float(np.sqrt((A ** 2).mean())))
AtA = A.T @ A
reg = c["strengthL2regularization"] + c["strengthTemporalSmoothing"]
H = AtA + np.eye(len(active)) * reg
groups = {}
for pos, i in enumerate(active):
    g = c["bsSolveSymmetryPoses"][i]
    if g >= 0: groups.setdefault(g, []).append(pos)
for g, m in groups.items():
    for a in m:
        for b in m:
            if a != b:
                H[a, a] += c["strengthSymmetry"]; H[a, b] -= c["strengthSymmetry"]
L = cholesky(H, lower=True)
W = np.zeros((len(skin), len(poses)))
prev = np.zeros(len(active)); err = []
for f in range(len(skin)):
    b = A.T @ skin[f] + c["strengthTemporalSmoothing"] * prev - 0.25 * c["strengthL1regularization"]
    y = solve_triangular(L, b, lower=True)
    x = lsq_linear(L.T, y, bounds=(0, 1), method="bvls", tol=1e-5).x
    prev = x; W[f, active] = x
    err.append(np.sqrt(((A @ x - skin[f]) ** 2).mean()))
print("solve residual rms", float(np.mean(err)), "vs target rms", float(np.sqrt((skin ** 2).mean())))
res = {n: W[:, i].copy() for i, n in enumerate(poses)}

# Eyes: right (pitch, yaw), left (pitch, yaw) in degrees, plus saccades (SDK AnimatorEyes::ComputeEyesRotation).
m = np.load(f"{model}/model_data_{actor}.npz"); sac = m["saccade_rot_matrix"]
idx = (np.arange(len(eyes)) + cfg["saccade_start"]) % len(sac)
print("eyes raw deg range", eyes.min(0).round(2), eyes.max(0).round(2), "saccade range", sac.min(0).round(2), sac.max(0).round(2))
g, s = cfg["eye_gain"], cfg["saccade_gain"]
R_p = (eyes[:, 0] - np.median(eyes[:, 0])) * g + s * sac[idx, 0]
R_y = (eyes[:, 1] - np.median(eyes[:, 1])) * g + s * sac[idx, 1]
L_p = (eyes[:, 2] - np.median(eyes[:, 2])) * g + s * sac[idx, 0]
L_y = (eyes[:, 3] - np.median(eyes[:, 3])) * g + s * sac[idx, 1]
deg = cfg["shape_degrees"]
res["eyeLookDownRight"] = np.clip(R_p / deg["down"], 0, 1); res["eyeLookDownLeft"] = np.clip(L_p / deg["down"], 0, 1)
res["eyeLookUpRight"] = np.clip(-R_p / deg["up"], 0, 1); res["eyeLookUpLeft"] = np.clip(-L_p / deg["up"], 0, 1)
# positive yaw looks to the character's own left: outward for the left eye, inward for the right
res["eyeLookOutLeft"] = np.clip(L_y / deg["out"], 0, 1); res["eyeLookInLeft"] = np.clip(-L_y / deg["in"], 0, 1)
res["eyeLookInRight"] = np.clip(R_y / deg["in"], 0, 1); res["eyeLookOutRight"] = np.clip(-R_y / deg["out"], 0, 1)
for sd in ("Left", "Right"):  # lids held open, except while blinking
    res["eyeWide" + sd] = np.clip(res["eyeWide" + sd] + cfg["lid_open"] * (1 - res["eyeBlink" + sd]), 0, 1)
for n, gain in cfg["gain"].items():
    res[n] = np.clip(res[n] * gain, 0, 1)
json.dump({"fps_num": 60, "fps_den": 1, "frames": len(skin), "config": cfg, "channels": {k: [round(float(x), 4) for x in v] for k, v in res.items()}}, open(out, "w"))
for n in ("jawOpen", "mouthClose", "mouthPressLeft", "mouthRollLower", "mouthRollUpper", "mouthFunnel", "mouthPucker", "mouthLowerDownLeft", "mouthUpperUpLeft", "mouthSmileLeft", "eyeBlinkLeft", "eyeWideLeft", "eyeLookOutLeft", "eyeLookDownLeft", "browInnerUp"):
    a = res[n]; print(f"{n:20s} mean {a.mean():.2f} p95 {np.percentile(a,95):.2f} max {a.max():.2f}")
yaw = L_y; print("gaze yaw deg p5/p95", np.percentile(yaw, 5).round(1), np.percentile(yaw, 95).round(1), "pitch", np.percentile(L_p, 5).round(1), np.percentile(L_p, 95).round(1), "eye-dart frames (>0.6 deg/frame):", int((np.abs(np.diff(yaw)) > 0.6).sum()))

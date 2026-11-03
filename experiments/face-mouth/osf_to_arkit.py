"""OpenSeeFace log + video timestamps -> ARKit channels and head rotation at a fixed frame rate.
Args: tracker CSV, pts.txt, output JSON, rest start s, rest end s, lip gap at jawOpen 1, eye distance. Columns are read by position: this build's header doesn't match its rows.
Lip opening is scaled to the character by measurement (measure_mouth.py); the other channels use each channel's own range in the take."""
import csv, json, sys
import cv2
import numpy as np
FPS = 30
src, pts, out = sys.argv[1:4]
rest_from, rest_to = float(sys.argv[4]), float(sys.argv[5])
LIP_M_AT_JAW1, IPD_M = float(sys.argv[6]), float(sys.argv[7])  # lip gap at jawOpen 1 and eye distance, in metres
R = csv.reader(open(src, newline="")); next(R); rows = [r for r in R if r]
T = np.array([float(x.split(",")[0]) for x in open(pts)])
L = np.array([[float(v) for v in r[25:25 + 204]] for r in rows]).reshape(len(rows), 68, 3)[:, :, :2]
rv = np.array([[float(v) for v in r[19:22]] for r in rows])
x, y = L[:, :, 0], L[:, :, 1]
def med(v, r=7): return np.array([np.median(v[max(0, i - r):i + r + 1]) for i in range(len(v))])
def smooth(v, s):
    r = int(3 * s + 1); k = np.exp(-0.5 * (np.arange(-r, r + 1) / s) ** 2); k /= k.sum()
    return np.convolve(np.pad(v, r, mode="edge"), k, "valid")
def dist(a, b): return np.hypot(x[:, a] - x[:, b], y[:, a] - y[:, b])
cR, cL = L[:, 36:42].mean(1), L[:, 42:48].mean(1)  # image left = the subject's right
ipd = med(np.hypot(*(cL - cR).T))
gap = dist(60, 64) / ipd
rest = (T > rest_from) & (T < rest_to)  # the performer is still and neutral here
def rng(v, p=99.5):
    return max(np.percentile(v, p), 1e-4)
def pos(v, floor, p=99.5, cap=0.85):  # positive part, full at the take's near-maximum; the floor keeps small tremors small
    return np.clip(v / max(rng(v, p), floor), 0, 1) * cap
ch = {}
ch["jawOpen"] = np.clip(np.clip(gap - np.percentile(gap, 20), 0, None) * IPD_M / LIP_M_AT_JAW1, 0, 1)
g = np.clip(gap / rng(gap), 0, 1)
cx, cy = (x[:, 60] + x[:, 64]) / 2, (y[:, 60] + y[:, 64]) / 2
wide_l, wide_r = (x[:, 62] - cx) / ipd, (cx - x[:, 58]) / ipd
up_l, up_r = (cy - y[:, 62]) / ipd, (cy - y[:, 58]) / ipd
for n, wide, up in (("Left", wide_l, up_l), ("Right", wide_r, up_r)):
    w = wide - np.median(wide[rest]); u = up - np.median(up[rest])
    ch["mouthSmile" + n] = pos(u, 0.06)
    ch["mouthFrown" + n] = pos(-u, 0.06)
    ch["mouthStretch" + n] = pos(w, 0.06) * (1 - pos(u, 0.06))
pk = (wide_l + wide_r) - np.median((wide_l + wide_r)[rest])
ch["mouthPucker"] = pos(-pk, 0.12)
ch["mouthFunnel"] = ch["mouthPucker"] * g
side = (cx - x[:, 30]) / ipd; side = side - np.median(side[rest])
ch["mouthLeft"], ch["mouthRight"] = pos(side, 0.05), pos(-side, 0.05)
lift = -(y[:, 60] - y[:, 33]) / ipd; lift = lift - np.median(lift[rest])
for n in ("Left", "Right"):
    ch["mouthUpperUp" + n] = pos(lift, 0.05) * 0.4
t_low, t_up = dist(64, 55) / ipd, dist(60, 50) / ipd
ch["mouthRollLower"] = pos(np.median(t_low[rest]) - t_low, 0.03) * 0.5
ch["mouthRollUpper"] = pos(np.median(t_up[rest]) - t_up, 0.03) * 0.5
contact = np.clip(1 - g / 0.08, 0, 1)
for n in ("Left", "Right"):
    ch["mouthPress" + n] = ch["mouthRollLower"] * contact
for n, c, outer, inner in (("Left", cL, 26, 22), ("Right", cR, 17, 21)):
    o, i = (c[:, 1] - y[:, outer]) / ipd, (c[:, 1] - y[:, inner]) / ipd
    o, i = o - np.median(o[rest]), i - np.median(i[rest])
    ch["browOuterUp" + n] = pos(o, 0.05)
    ch["browDown" + n] = pos(-i, 0.05)
    ch["_inner" + n] = i
ch["browInnerUp"] = pos((ch.pop("_innerLeft") + ch.pop("_innerRight")) / 2, 0.05)
blink = {}
for n, a in (("Left", (dist(43, 47) + dist(44, 46)) / 2 / dist(42, 45)), ("Right", (dist(37, 41) + dist(38, 40)) / 2 / dist(36, 39))):
    shut, opened = np.percentile(a, 1), np.median(a)
    blink[n] = np.clip(1 - (a - shut) / (opened - shut), 0, 1)
    ch["eyeBlink" + n] = blink[n]
    ch["eyeWide" + n] = pos(a - opened, 0.08)
h = ((x[:, 67] - cL[:, 0]) / dist(42, 45) + (x[:, 66] - cR[:, 0]) / dist(36, 39)) / 2
v = ((y[:, 67] - cL[:, 1]) / dist(42, 45) + (y[:, 66] - cR[:, 1]) / dist(36, 39)) / 2
h, v = np.clip(h - np.median(h), -0.5, 0.5), np.clip(v - np.median(v), -0.5, 0.5)  # a profile view gives wild values
h, v = smooth(h, 1.0), smooth(v, 1.0)
live = 1 - np.maximum(blink["Left"], blink["Right"])  # a shut eye has no gaze
ch["eyeLookOutLeft"], ch["eyeLookInRight"] = pos(h, 0.15) * live, pos(h, 0.15) * live
ch["eyeLookOutRight"], ch["eyeLookInLeft"] = pos(-h, 0.15) * live, pos(-h, 0.15) * live
for n in ("Left", "Right"):
    ch["eyeLookDown" + n], ch["eyeLookUp" + n] = pos(v, 0.08) * live, pos(-v, 0.08) * live
# Head: rotation relative to the take's median pose, tracker axes -> Blender (subject faces -Y).
Rs = np.array([cv2.Rodrigues(r)[0] for r in rv])
U, _, Vt = np.linalg.svd(np.median(Rs, axis=0)); R0 = U @ Vt
d = np.array([cv2.Rodrigues(r @ R0.T)[0].ravel() for r in Rs])
pnp = np.array([float(r[11]) for r in rows])
good = pnp < 20  # the first frames fit badly and give false turns
for i in range(3):
    d[:, i] = np.interp(np.arange(len(d)), np.flatnonzero(good), d[good, i])
# The tracker stores points as (row, column), so its axes are swapped. Signs checked against a recorded head turn.
head = np.stack([d[:, 1], d[:, 2], -d[:, 0]], 1)
head = np.stack([smooth(head[:, i], 1.0) for i in range(3)], 1)
n_out = int(round(T[-1] * FPS)) + 1
t = np.arange(n_out) / FPS
res = {k: [round(float(a), 4) for a in np.interp(t, T, c)] for k, c in ch.items()}
hd = [[round(float(np.interp(tt, T, head[:, i])), 5) for i in range(3)] for tt in t]
json.dump({"fps": FPS, "frames": n_out, "channels": res, "head_rotvec_world": hd}, open(out, "w"))
print("frames", n_out, "ipd px", round(float(np.median(ipd)), 1))
for k in sorted(res):
    a = np.array(res[k]); print(f"{k:20s} mean {a.mean():.2f} p95 {np.percentile(a, 95):.2f} max {a.max():.2f}")
print("head deg max", np.round(np.degrees(np.abs(head).max(0)), 1))
np.save(out + ".head.npy", np.c_[T, head])

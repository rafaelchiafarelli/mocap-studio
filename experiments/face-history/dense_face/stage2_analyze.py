"""Stage 2: track known skin points in three rendered views, triangulate, compare with the true 3D positions.
Shifting one view by a frame shows what bad camera sync does. Best case: perfect calibration, no real-camera noise, and start points given."""
import glob, json, sys
import cv2, numpy as np, torch
sys.path.insert(0, sys.argv[1])
from tapnet.torch import tapir_model
_, _, O, ckpt = sys.argv
truth = np.load(f"{O}/truth.npy"); cams = json.load(open(f"{O}/cameras.json")); lips = set(np.load(f"{O}/lip_verts.npy").tolist())
n = len(truth); names = ["front", "left", "right"]; RES = 512; SC = RES / 1024
files = {c: sorted(glob.glob(f"{O}/{c}_*.png")) for c in names}; print("frames", n, {c: len(f) for c, f in files.items()})
video = {c: np.stack([cv2.cvtColor(cv2.resize(cv2.imread(f), (RES, RES), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB) for f in files[c]]) for c in names}
P = {c: np.array(cams[c]["K"]) @ np.array(cams[c]["Rt"]) for c in names}
def project(c, X):
    h = (P[c] @ np.c_[X, np.ones(len(X))].T).T; return h[:, :2] / h[:, 2:]
q = n // 2; X0 = truth[q]
# Skin the front camera can see, on the front half of the head.
pf = project("front", X0); inside = (pf[:, 0] > 10) & (pf[:, 0] < 1014) & (pf[:, 1] > 10) & (pf[:, 1] < 1014) & (X0[:, 1] < -0.05) & (X0[:, 2] > 1.41)
cand = np.flatnonzero(inside)
# keep the closest point in each small screen cell, so hidden inner-mouth vertices are skipped
cell = (pf[cand] // 6).astype(int); dist = np.linalg.norm(X0[cand] - (np.linalg.inv(np.array(cams["front"]["Rt"])[:3, :3]) @ -np.array(cams["front"]["Rt"])[:3, 3]), axis=1)
best = {}
for v, ce, de in zip(cand, map(tuple, cell), dist):
    if ce not in best or de < best[ce][1]: best[ce] = (v, de)
pts = np.array([b[0] for b in best.values()]); is_lip = np.array([v in lips for v in pts]); print("points", len(pts), "on lips", int(is_lip.sum()))
dev = "cuda"; model = tapir_model.TAPIR(pyramid_level=1); model.load_state_dict(torch.load(ckpt, map_location="cpu")); model = model.to(dev).eval()
def track(frames, xy):
    qp = np.concatenate([np.full((len(xy), 1), q), xy[:, ::-1]], 1).astype(np.float32); v = torch.tensor(frames).float().to(dev) / 255 * 2 - 1; tr = []
    with torch.inference_mode(), torch.autocast("cuda", dtype=torch.float16):
        for s in range(0, len(qp), 800):
            tr.append(model(v[None], torch.tensor(qp[s:s + 800]).to(dev)[None])["tracks"][0].float().cpu().numpy())
    return np.concatenate(tr).transpose(1, 0, 2) / SC
tracks = {c: track(video[c], project(c, X0[pts]) * SC) for c in names}
err2d = {c: np.linalg.norm(tracks[c] - np.stack([project(c, truth[t][pts]) for t in range(n)]), axis=2) for c in names}
print("2D error px at 1024:", {c: (round(float(np.median(e)), 2), round(float(np.percentile(e, 95)), 2)) for c, e in err2d.items()})
def triangulate(views, frame_of):
    out = np.zeros((n, len(pts), 3))
    for t in range(n):
        for i in range(len(pts)):
            A = []
            for c in views:
                x, y = tracks[c][frame_of(c, t), i]; A += [x * P[c][2] - P[c][0], y * P[c][2] - P[c][1]]
            out[t, i] = np.linalg.lstsq(np.array(A)[:, :3], -np.array(A)[:, 3], rcond=None)[0]
    return out
def report(label, X):
    e = np.linalg.norm(X - truth[:, pts], axis=2) * 1000
    print(f"{label}: all p50 {np.median(e):.2f} p95 {np.percentile(e, 95):.2f} mm | lips p50 {np.median(e[:, is_lip]):.2f} p95 {np.percentile(e[:, is_lip], 95):.2f} mm")
report("3 cameras in sync", triangulate(names, lambda c, t: t))
report("2 cameras in sync (front+left)", triangulate(["front", "left"], lambda c, t: t))
for k, ms in ((1, 42), (2, 83)):
    report(f"3 cameras, one view {k} frame(s) late (~{ms} ms)", triangulate(names, lambda c, t: min(t + k, n - 1) if c == "left" else t))
motion = np.linalg.norm(np.diff(truth[:, pts], axis=0), axis=2) * 1000; print("true skin motion per frame mm: all p95 %.2f; lips p95 %.2f; lips max %.2f" % (np.percentile(motion, 95), np.percentile(motion[:, is_lip], 95), motion[:, is_lip].max()))

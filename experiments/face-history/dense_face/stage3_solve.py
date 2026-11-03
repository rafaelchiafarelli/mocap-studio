"""Stage 3: transfer tracked 2D face motion onto the character mesh, with no 52-value layer.
Args: stage1.npz, stage3 dir, face landmarker model. Writes a PC2 vertex cache plus eye, lash, teeth and tongue channels.
Limit: one camera, so motion is in the image plane; depth motion (pucker, lips forward) is lost."""
import json, struct, sys
import cv2, numpy as np, mediapipe as mp
import scipy.sparse as sp
from scipy.sparse.linalg import splu
from scipy.interpolate import RBFInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree
s1, O, flm = sys.argv[1:4]
CFG = dict(sigma=0.7, min_vis=0.7, radius_px=5.0, w_control=200.0, w_fixed=500.0, jaw_full_m=0.03, gaze_deg_per_ratio=60.0, gaze_gain=1.5,
           shape_deg=dict(i=15.4, o=14.6, d=11.0, u=7.6), stable=[6, 168, 197, 195, 5, 8, 9, 151, 10, 133, 362, 243, 463], front_y=-0.05, closed_frac=0.012, hidden_mm=8.0, edge_inset_px=35.0, max_move_m=0.03)
d = np.load(s1); tr = d["tracks"].astype(np.float64); vis = d["vis"]; lm = d["lmk"].astype(np.float64); q = int(d["q"]); NL = int(d["n_lmk"]); n = len(tr)
tr = gaussian_filter1d(tr, CFG["sigma"], axis=0, mode="nearest")
# Remove head motion in 3D. Rotation per frame comes from MediaPipe's 3D landmarks on points that barely move with expression;
# every tracked point gets a depth, so what a rigid head would do is subtracted, and only the remainder counts as expression.
stab = np.zeros_like(tr); st = CFG["stable"]
L3 = np.load(s1.replace("stage1.npz", "lm3d.npy")).astype(np.float64)
for c in range(3 * 478):
    arr = L3.reshape(n, -1)[:, c]; bad = np.isnan(arr)
    if bad.any(): arr[bad] = np.interp(np.flatnonzero(bad), np.flatnonzero(~bad), arr[~bad])
Z = RBFInterpolator(L3[q, :468, :2], L3[q, :468, 2], kernel="thin_plate_spline", smoothing=1.0)(tr[q])
Rots = np.zeros((n, 3, 3))
A0 = L3[q, st] - L3[q, st].mean(0)
for t in range(n):
    B = L3[t, st] - L3[t, st].mean(0); H_ = A0.T @ B; u, _, vt = np.linalg.svd(H_); dd = np.sign(np.linalg.det(vt.T @ u.T))
    Rots[t] = vt.T @ np.diag([1, 1, dd]) @ u.T
Rots = gaussian_filter1d(Rots, 1.5, axis=0, mode="nearest")
X0 = np.c_[tr[q], Z]; centre = X0[st].mean(0); X0c = X0 - centre
yaw_est = np.degrees(np.arctan2(Rots[:, 0, 2], Rots[:, 2, 2])); print("head rotation estimate yaw deg min %.1f max %.1f" % (yaw_est.min(), yaw_est.max()))
for t in range(n):
    rig_ = X0c @ Rots[t].T
    # scale and shift from the stable points, given that rotation
    a_, b_ = rig_[st, :2], tr[t, st]; ma, mb = a_.mean(0), b_.mean(0)
    sc = ((a_ - ma) * (b_ - mb)).sum() / ((a_ - ma) ** 2).sum()
    pred = sc * (rig_[:, :2] - ma) + mb
    expr = tr[t] - pred
    r2 = Rots[t][:2, :2]; u2, _, v2 = np.linalg.svd(r2); inplane = u2 @ v2   # undo in-plane rotation of the remainder
    stab[t] = tr[q] + (expr @ inplane) / sc
res = np.linalg.norm(stab[:, st] - tr[q, st], axis=2); print("head removal residual px p50 %.2f p95 %.2f" % (np.median(res), np.percentile(res, 95)))
# The same landmarks on the character's neutral render.
img = cv2.cvtColor(cv2.imread(f"{O}/neutral_front.png"), cv2.COLOR_BGR2RGB)
opts = mp.tasks.vision.FaceLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=flm), running_mode=mp.tasks.vision.RunningMode.IMAGE, num_faces=1)
with mp.tasks.vision.FaceLandmarker.create_from_options(opts) as L:
    r = L.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=img))
ant = np.array([(p.x * 1024, p.y * 1024) for p in r.face_landmarks[0]]); print("character landmarks found", len(ant))
tps = RBFInterpolator(lm[q, :468], ant[:468], kernel="thin_plate_spline", smoothing=1.0)
ref_px = tps(tr[q])
tgt = tps(stab.reshape(-1, 2)).reshape(n, -1, 2); dpx = tgt - ref_px
# Mesh: project neutral vertices with the same camera.
Nz = np.load(f"{O}/neutral.npz"); co = Nz["co"]; edges = Nz["edges"]; skin = Nz["skin"]; W = Nz["world"]
cam = json.load(open(f"{O}/camera.json")); K = np.array(cam["K"]); Rt = np.array(cam["Rt"])
wco = (W @ np.c_[co, np.ones(len(co))].T).T[:, :3]
cc = (Rt @ np.c_[wco, np.ones(len(wco))].T).T; px = (K @ cc.T).T; px = px[:, :2] / px[:, 2:]; depth = cc[:, 2]
# Only skin the camera can see: a vertex is hidden when another one nearby on screen is clearly closer.
candidates = np.flatnonzero(skin); pt = cKDTree(px[candidates]); hidden = np.zeros(len(co), bool)
for v in candidates:
    near_v = candidates[pt.query_ball_point(px[v], 6.0)]
    hidden[v] = depth[near_v].min() < depth[v] - CFG["hidden_mm"] / 1000
front = skin & ~hidden & (wco[:, 1] < CFG["front_y"])
region = skin & (wco[:, 2] > 0)
fr = np.flatnonzero(front); ch = wco[fr[np.argmin(np.linalg.norm(px[fr] - ant[152], axis=1))]]
region = skin & (wco[:, 2] > ch[2] - 0.05)
print("region verts", int(region.sum()), "chin z", round(float(ch[2]), 3))
inner = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]
def mouth_line(points):
    o = np.argsort(points[:, 0]); return points[o, 0], points[o, 1]
ax, ay = mouth_line(tr[q, inner]); hx, hy = mouth_line(ant[inner])
act_side = tr[q, :, 1] - np.interp(tr[q, :, 0], ax, ay); his_side = px[:, 1] - np.interp(px[:, 0], hx, hy)
in_mouth_x = (tr[q, :, 0] > ax[0] - 4) & (tr[q, :, 0] < ax[-1] + 4) & (np.abs(act_side) < 45)
idx = np.flatnonzero(region); tree = cKDTree(px[idx])
keep = vis.mean(0) >= CFG["min_vis"]
ctrl, delta = {}, {}
for i in range(tr.shape[1]):
    if not keep[i] or (468 <= i < 478): continue
    cand = idx[tree.query_ball_point(ref_px[i], CFG["radius_px"])]; cand = cand[front[cand]]
    if in_mouth_x[i] and len(cand):
        cand = cand[np.sign(his_side[cand]) == np.sign(act_side[i])] if abs(act_side[i]) > 0.2 else cand
    if not len(cand): continue
    v = cand[np.argmin(depth[cand])]; ctrl.setdefault(int(v), []).append(i)
cv = np.array(sorted(ctrl)); print("control vertices", len(cv), "of", tr.shape[1], "points")
Rc = Rt[:3, :3]
# Face-edge points slide across the turning cheek; drop any that move further than a face plausibly does, then rebuild.
edge_lm = [10,338,297,332,284,251,389,356,454,323,361,288,397,365,379,378,400,377,152,148,176,149,150,136,172,58,132,93,234,127,162,21,54,103,67,109]
hull = cv2.convexHull(ant[edge_lm].astype(np.float32))
inset = np.array([cv2.pointPolygonTest(hull, (float(p_[0]), float(p_[1])), True) for p_ in px[cv]])
maxmove = np.array([np.linalg.norm(dpx[:, ctrl[int(v)]].mean(1), axis=1).max() * depth[v] / K[0, 0] for v in cv])
ok_c = (inset > CFG["edge_inset_px"]) & (maxmove < CFG["max_move_m"])
print("controls dropped: near edge", int((inset <= CFG["edge_inset_px"]).sum()), "too far", int((maxmove >= CFG["max_move_m"]).sum()), "kept", int(ok_c.sum()))
cv = cv[ok_c]
disp = np.zeros((n, len(cv), 3))
for j, v in enumerate(cv):
    dp = dpx[:, ctrl[int(v)]].mean(1)
    cam_xyz = np.c_[dp[:, 0] * depth[v] / K[0, 0], dp[:, 1] * depth[v] / K[1, 1], np.zeros(n)]
    disp[:, j] = cam_xyz @ Rc  # camera axes back to world (R transpose applied on the right)
# Spread over the mesh surface: minimise bending of the displacement, pinned at controls, zero at the back of the head and neck.
rid = -np.ones(len(co), int); rid[idx] = np.arange(len(idx)); m = len(idx)
e = edges[(rid[edges[:, 0]] >= 0) & (rid[edges[:, 1]] >= 0)]
# Cut the mesh along the mouth line for this solve, so each lip moves on its own.
mw = (px[e[:, 0], 0] > hx[0] + 2) & (px[e[:, 0], 0] < hx[-1] - 2) & (px[e[:, 1], 0] > hx[0] + 2) & (px[e[:, 1], 0] < hx[-1] - 2)
across = mw & (his_side[e[:, 0]] * his_side[e[:, 1]] <= 0) & (np.abs(his_side[e[:, 0]]) < 60) & (np.abs(his_side[e[:, 1]]) < 60)
print("edges cut along mouth", int(across.sum())); e = e[~across]; a, b = rid[e[:, 0]], rid[e[:, 1]]
Ad = sp.coo_matrix((np.ones(len(a) * 2), (np.r_[a, b], np.r_[b, a])), shape=(m, m)).tocsr(); Dg = sp.diags(np.asarray(Ad.sum(1)).ravel())
Lp = (Dg - Ad).tocsr(); H = (Lp.T @ Lp).tolil()
back = wco[idx, 1] > CFG["front_y"]
low = wco[idx, 2] < ch[2] - 0.04
fixed = np.flatnonzero(back | low); fset = np.zeros(m); fset[fixed] = CFG["w_fixed"]
cset = np.zeros(m); cidx = rid[cv]; cset[cidx] = CFG["w_control"]
Sys = (H.tocsr() + sp.diags(fset + cset) + sp.eye(m) * 1e-6).tocsc(); lu = splu(Sys)
print("fixed verts", len(fixed))
U = np.zeros((n, len(co), 3), dtype=np.float32)
for t in range(n):
    rhs = np.zeros((m, 3)); rhs[cidx] = CFG["w_control"] * disp[t]
    U[t, idx] = lu.solve(rhs)
err = np.linalg.norm(U[:, cv] - disp, axis=2); print("fit at controls mm p50 %.2f p95 %.2f; largest displacement %.1f mm" % (np.median(err) * 1000, np.percentile(err, 95) * 1000, np.linalg.norm(U, axis=2).max() * 1000))
pos = co[None].astype(np.float32) + np.einsum("ij,tvj->tvi", np.linalg.inv(W[:3, :3]).astype(np.float32), U)
with open(f"{O}/face.pc2", "wb") as f:
    f.write(struct.pack("<12siiffi", b"POINTCACHE2\0", 1, len(co), 1.0, 1.0, n)); f.write(pos.astype("<f4").tobytes())
# Lip gap on the character, on vertices nearest the inner lip landmarks.
near = lambda l, side: (lambda c: c[np.argmin(np.linalg.norm(px[c] - ant[l], axis=1))])(fr[(np.sign(his_side[fr]) == side) & region[fr]])
pairs = [(near(u, -1), near(l, 1)) for u, l in ((82, 87), (13, 14), (312, 317))]
g_ch = np.mean([np.linalg.norm(wco[u] + U[:, u] - wco[l] - U[:, l], axis=1) for u, l in pairs], axis=0) * 1000
g_src = np.mean([np.linalg.norm(lm[:, u] - lm[:, l], axis=1) for u, l in ((82, 87), (13, 14), (312, 317))], axis=0)
fh = np.nanmedian(np.linalg.norm(lm[:, 10] - lm[:, 152], axis=1)); closed = g_src / fh < CFG["closed_frac"]
okf = np.isfinite(g_src); print("lip gap corr to source %.3f; character gap mm p10 %.1f p50 %.1f p90 %.1f max %.1f; on %d source-closed frames p50 %.1f, near closed(<2mm above neutral) %d" % (np.corrcoef(g_src[okf], g_ch[okf])[0, 1], *np.percentile(g_ch, [10, 50, 90, 100]), closed.sum(), np.median(g_ch[closed]), (g_ch[closed] < np.percentile(g_ch, 3) + 2).sum()))
# Channels for meshes the skin cache does not move: eyes, lashes, teeth, tongue.
ch_v = {}
chin = fr[np.argmin(np.linalg.norm(px[fr] - ant[152], axis=1))]
jaw = np.clip(-U[:, chin, 2] / CFG["jaw_full_m"], 0, 1); ch_v["jawOpen"] = jaw
def gaze(iris, c1, c2):
    mid = (lm[:, c1] + lm[:, c2]) / 2; w = np.linalg.norm(lm[:, c1] - lm[:, c2], axis=1, keepdims=True)
    return (lm[:, iris] - mid) / w
rg = gaze(468, 33, 133); lg = gaze(473, 362, 263)
g = np.nan_to_num((rg + lg) / 2); g -= np.median(g, 0); g = gaussian_filter1d(g, 1.0, axis=0) * CFG["gaze_deg_per_ratio"] * CFG["gaze_gain"]
sd = CFG["shape_deg"]; print("gaze deg p5/p95 x %.1f %.1f y %.1f %.1f" % (*np.percentile(g[:, 0], [5, 95]), *np.percentile(g[:, 1], [5, 95])))
ch_v["eyeLookOutLeft"] = np.clip(g[:, 0] / sd["o"], 0, 1); ch_v["eyeLookInRight"] = np.clip(g[:, 0] / sd["i"], 0, 1)
ch_v["eyeLookInLeft"] = np.clip(-g[:, 0] / sd["i"], 0, 1); ch_v["eyeLookOutRight"] = np.clip(-g[:, 0] / sd["o"], 0, 1)
for s_ in ("Left", "Right"):
    ch_v["eyeLookDown" + s_] = np.clip(g[:, 1] / sd["d"], 0, 1); ch_v["eyeLookUp" + s_] = np.clip(-g[:, 1] / sd["u"], 0, 1)
for name, (u, l) in dict(Right=(159, 145), Left=(386, 374)).items():
    gp = np.linalg.norm(stab[:, u] - stab[:, l], axis=1); ch_v["eyeBlink" + name] = np.clip(1 - gp / max(np.percentile(gp, 90), 1e-3), 0, 1)
json.dump({"fps_num": 24000, "fps_den": 1001, "frames": n, "config": CFG, "channels": {k: [round(float(x), 4) for x in v] for k, v in ch_v.items()}}, open(f"{O}/channels.json", "w"))
print("jaw max %.2f, blink max L %.2f R %.2f" % (jaw.max(), ch_v["eyeBlinkLeft"].max(), ch_v["eyeBlinkRight"].max()))

# --- diagnostics at the widest mouth frame ---
wide = int(np.nanargmax(g_src)); print("widest source frame", wide + 1)
for nm, l in (("upper inner 13", 13), ("lower inner 14", 14), ("chin 152", 152), ("nose 1", 1)):
    print(f" {nm}: actor stab delta px", (stab[wide, l] - tr[q, l]).round(1), "tps delta px", dpx[wide, l].round(1), "ctrl?", any(l in v for v in ctrl.values()), "vis %.2f" % vis[wide, l], "keep", bool(keep[l]))
print(" pairs verts", pairs, "world z", [(round(float(wco[u, 2]), 4), round(float(wco[l, 2]), 4)) for u, l in pairs], "U z at wide", [(round(float(U[wide, u, 2]) * 1000, 1), round(float(U[wide, l, 2]) * 1000, 1)) for u, l in pairs])
mag = np.linalg.norm(U, axis=2); t_, v_ = np.unravel_index(mag.argmax(), mag.shape)
print(" biggest displacement frame", t_ + 1, "vert", v_, "world", wco[v_].round(3), "is control", v_ in set(cv.tolist()), "px", px[v_].round(0))
big = np.flatnonzero(mag.max(0) > 0.03); print(" verts over 30 mm:", len(big), "of which control", len(set(big) & set(cv.tolist())), "z range", wco[big, 2].min().round(3) if len(big) else None, wco[big, 2].max().round(3) if len(big) else None)
cd = np.linalg.norm(disp, axis=2); print(" control displacement mm p50 %.1f p95 %.1f max %.1f" % (np.median(cd) * 1000, np.percentile(cd, 95) * 1000, cd.max() * 1000))
print(" K f", K[0, 0].round(0), "depth at mouth", depth[pairs[0][0]].round(3), "m per px", (depth[pairs[0][0]] / K[0, 0]).round(6), "actor face px", np.nanmedian(np.linalg.norm(lm[:, 10] - lm[:, 152], axis=1)).round(0), "character face px", np.linalg.norm(ant[10] - ant[152]).round(0))

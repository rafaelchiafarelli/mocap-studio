"""Judge stage 1: lip behaviour of tracked points against independent per-frame MediaPipe landmarks; make an overlay video."""
import sys
import cv2, numpy as np
video, npz, outv = sys.argv[1:4]
d = np.load(npz); tr, vis, lm = d["tracks"], d["vis"], d["lmk"]; q = int(d["q"]); x0, y0, size = d["crop"]; RES = int(d["res"])
n = len(tr)
face = np.linalg.norm(lm[:, 10] - lm[:, 152], axis=1); fh = np.nanmedian(face); mm = 180.0 / fh  # assume about 18 cm brow-chin scale, only for readable units
inner_u, inner_l = [82, 13, 312], [87, 14, 317]
outer = [61,146,91,181,84,17,314,405,321,375,291,185,40,39,37,0,267,269,270,409]
lips = sorted(set(inner_u + inner_l + outer + [78,95,88,178,317,402,318,324,308,191,80,81,311,310,415]))
g_tr = np.linalg.norm(tr[:, inner_u] - tr[:, inner_l], axis=2).mean(1); g_lm = np.linalg.norm(lm[:, inner_u] - lm[:, inner_l], axis=2).mean(1)
ok = np.isfinite(g_lm)
print("inner lip gap corr tracks vs landmarks: %.3f" % np.corrcoef(g_tr[ok], g_lm[ok])[0, 1])
print("gap mm(approx): tracks p10 %.1f p50 %.1f p90 %.1f | landmarks p10 %.1f p50 %.1f p90 %.1f" % (*(np.percentile(g_tr, [10,50,90]) * mm), *(np.nanpercentile(g_lm, [10,50,90]) * mm)))
closed = g_lm < 0.012 * fh * 8 / 8 * 1.0
print("frames lips closed per landmarks", int(closed.sum()), "of", n, "; tracked gap on those: p50 %.1f p90 %.1f mm" % (np.median(g_tr[closed]) * mm, np.percentile(g_tr[closed], 90) * mm))
err = np.linalg.norm(tr[:, :478] - lm, axis=2)
print("distance tracks to landmarks mm: all p50 %.1f p95 %.1f | lips p50 %.1f p95 %.1f" % (np.nanmedian(err) * mm, np.nanpercentile(err, 95) * mm, np.nanmedian(err[:, lips]) * mm, np.nanpercentile(err[:, lips], 95) * mm))
for name, idx in (("inner lips", inner_u + inner_l), ("outer lips", outer)):
    print(f"visible fraction {name}: mean {vis[:, idx].mean():.2f}; while closed {vis[closed][:, idx].mean():.2f}; while open wide {vis[g_lm > np.nanpercentile(g_lm, 90)][:, idx].mean():.2f}")
print("visible fraction grid: mean %.2f, worst frame %.2f" % (vis[:, 478:].mean(), vis[:, 478:].mean(1).min()))
rt = d["roundtrip"]; print("round trip mm: lmks lips p50 %.2f p95 %.2f; grid p50 %.2f p95 %.2f" % (np.median(rt[lips]) * mm, np.percentile(rt[lips], 95) * mm, np.median(rt[478:]) * mm, np.percentile(rt[478:], 95) * mm))
sm = np.abs(np.diff(tr[:, 478:], 2, axis=0)); print("jitter (2nd diff) px grid p50 %.2f p95 %.2f" % (np.median(sm), np.percentile(sm, 95)))
cap = cv2.VideoCapture(video); fps = cap.get(cv2.CAP_PROP_FPS); w = cv2.VideoWriter(outv, cv2.VideoWriter_fourcc(*"mp4v"), fps, (1024, 512))
for i in range(n):
    ok, f = cap.read()
    if not ok: break
    c = cv2.resize(f[y0:y0 + size, x0:x0 + size], (RES, RES), interpolation=cv2.INTER_AREA); o = c.copy()
    for j in range(478, tr.shape[1], 2):
        col = (0, 255, 0) if vis[i, j] > .5 else (0, 0, 255)
        cv2.circle(o, tuple(np.round(tr[i, j]).astype(int)), 1, col, -1, cv2.LINE_AA)
    for j in lips:
        col = (0, 255, 255) if vis[i, j] > .5 else (0, 0, 255)
        cv2.circle(o, tuple(np.round(tr[i, j]).astype(int)), 2, col, -1, cv2.LINE_AA)
    w.write(np.hstack([c, o]))
w.release()

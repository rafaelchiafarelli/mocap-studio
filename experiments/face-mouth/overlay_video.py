"""Draws the tracked points over a recording. Args: video, tracker CSV, pts.txt, output .mp4 (no audio)."""
import csv, subprocess, sys
import cv2
import numpy as np
video, src, pts, out = sys.argv[1:5]
R = csv.reader(open(src, newline="")); next(R); rows = [r for r in R if r]
xy = np.array([[float(v) for v in r[25:25 + 204]] for r in rows]).reshape(len(rows), 68, 3)[:, :, :2]  # by position: the header is wrong
T = np.array([float(x.split(",")[0]) for x in open(pts)])
d = lambda i, j: np.linalg.norm(xy[:, i] - xy[:, j], axis=1)
inner = d(60, 64) / d(27, 30)
def draw(img, p, x0, y0, s, r):
    def line(idx, col):
        cv2.polylines(img, [((p[idx] - [x0, y0]) * s).astype(np.int32)], True, col, 1, cv2.LINE_AA)
    line(list(range(48, 58)), (0, 200, 0)); line(list(range(58, 66)), (0, 255, 255))
    for k, pt in enumerate(p[:68]):
        col = (255, 255, 0) if k >= 66 else (0, 255, 255) if 58 <= k < 66 else (0, 255, 0)
        cv2.circle(img, tuple(((pt - [x0, y0]) * s).astype(np.int32)), r, col, -1, cv2.LINE_AA)
def crop(f, cx, cy, w, h):
    x0 = int(np.clip(cx - w / 2, 0, 1920 - w)); y0 = int(np.clip(cy - h / 2, 0, 1080 - h))
    return f[y0:y0 + h, x0:x0 + w].copy(), x0, y0
def compose(f, i):
    p = xy[i]; c = p.mean(0)
    L, a, b = crop(f, c[0], c[1], 840, 840); L = cv2.resize(L, (960, 960), interpolation=cv2.INTER_CUBIC); draw(L, p, a, b, 960 / 840, 3)
    mc = p[48:66].mean(0); M, a, b = crop(f, mc[0], mc[1], 320, 240); M = cv2.resize(M, (960, 720), interpolation=cv2.INTER_CUBIC); draw(M, p, a, b, 3, 4)
    E, a, b = crop(f, (p[36, 0] + p[45, 0]) / 2, (p[36, 1] + p[45, 1]) / 2, 320, 80); E = cv2.resize(E, (960, 240), interpolation=cv2.INTER_CUBIC); draw(E, p, a, b, 3, 4)
    C = np.zeros((1080, 1920, 3), np.uint8); C[60:1020, 0:960] = L; C[60:780, 960:1920] = M; C[780:1020, 960:1920] = E
    cv2.putText(C, f"t={T[i]:.2f}s  labios: {inner[i]:.2f}  (verde=contorno externo, amarelo=interno, ciano=pupilas)", (16, 42), cv2.FONT_HERSHEY_SIMPLEX, .9, (255, 255, 255), 2, cv2.LINE_AA)
    return C
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", "1920x1080", "-r", "30", "-i", "-", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
cap = cv2.VideoCapture(video); now = 0.0; step = 1 / 30
for i in range(len(T)):
    ok, f = cap.read()
    if not ok:
        break
    C = compose(f, i); nxt = T[i + 1] if i + 1 < len(T) else T[i] + step
    while now < nxt:  # the camera's frame rate varies; the output is fixed
        enc.stdin.write(C.tobytes()); now += step
enc.stdin.close(); enc.wait()

"""Joins two videos of the same person into one 3D capture: MediaPipe 2D in each view, synced by a clap, the cameras found
from the body itself (no board), triangulated, put upright on the floor and scaled to the person's height.

Run through two_cameras.sh, which extracts the audio with the host's ffmpeg and runs capture_pose.py on each video first:

    human-model/investigations/pose-capture/two_cameras.sh A.mp4 B.mp4 OUT_DIR [--height 1.70] [--focal-mm 26] [--offset S]

Directly, in the reference image (hm.sh --ref):

    python two_cameras.py A.npz B.npz A.wav B.wav meta.json A.mp4 B.mp4 OUT_DIR [--height M] [--focal-mm MM] [--offset S] [--fixed-focal] [--scale-shoulders] [--no-skeleton] [--from S] [--to S]

--from and --to keep only A's video time between them (both_views.py lists where the body is whole in both cameras).
meta.json: {"a": {"video_start": s, "audio_start": s}, "b": {...}} from ffprobe, since a phone's audio and video streams
don't start at the same instant.

Steps:
1. Sync: the clap is found by cross-correlating the two sound tracks' onset envelopes (2 kHz, refined to a fraction of a
   sample). --offset S skips it: S seconds is added to A's video time to get B's.
2. B's landmarks are interpolated at A's frame times (phones record at a variable frame rate).
3. Cameras: pinhole, centred, no distortion. The focal length is the lens's 35 mm-equivalent (--focal-mm, 26 for most
   phones' main camera; give the phone's own figure), applied to the frame's diagonal, then fitted together with the cameras, with the bones (see calibrate();
   --fixed-focal keeps the lens's); B's rotation and direction from A come from the essential matrix of every
   landmark both views see well, then reprojection error is minimised (Huber), each landmark triangulated anew per try,
   together with how much each limb bone's length varies over the frames: two views alone can't tell the focal length
   (a wrong one reprojects as well and stretches depth), rigid bones can.
4. Left and right: MediaPipe sometimes swaps sides in one view. Per frame and per group (face, arms, legs), B's labels are
   tried swapped; the labelling that reprojects better wins, and which camera was wrong is decided by which keeps the 3D
   left nearest to the last frame's left.
5. Skeleton (unless --no-skeleton): the landmarks from the shoulders down are fitted per frame as a body with rigid
   bones (lengths from the frames where both views see a bone's ends well), each landmark weighted by its visibility in
   each view, the pose held near the last frame's. The head stays triangulated.
6. Metric: up is the median direction from mid-ankle to mid-shoulder; the floor is the 2nd percentile of heels and toes
   along it; the scale makes the ears' height (75th percentile over frames) `EAR_RATIO` of the given height, or with
   --scale-shoulders the shoulders' `SHOULDER_RATIO` (when a view cuts the head off).
   X is the person's left, from the hips in the first second, so the person starts facing -Y, as the Blender body does.

OUT_DIR gets:
- two_cameras.npz: `points_m` (T, 33, 3) in metres, Blender axes (Z up, floor at 0); `world` (T, 33, 3) the same about the
  mid-hip in MediaPipe's axes (x, -z, y), so drive_capture.py reads it as it reads a single camera's; `found`, `times`, `fps`,
  `swapped` (T, 3, 2): per group, whether A's or B's labels were swapped;
- two_cameras.json: offset and its confidence, both cameras, reprojection error, swaps, bone-length variation;
- two_cameras_overlay.mp4 (mp4v; the .sh transcodes it): both views with MediaPipe's points (white) and the 3D
  reprojected (lines), and the 3D seen from the front and the side.
"""
from __future__ import annotations

import json
import os
import sys
import wave

import numpy as np

os.environ.setdefault("GLOG_minloglevel", "2")
import cv2  # noqa: E402
from scipy.optimize import least_squares  # noqa: E402

EAR_RATIO = 0.93  # ear (tragion) height over stature, by eye from anthropometric tables
SHOULDER_RATIO = 0.82  # shoulder (acromion) height over stature, the same way; for when one view loses the head
VIS_MIN = 0.6  # landmarks below this visibility in either view don't count for the cameras
ENV_RATE = 2000  # sound envelope samples per second for the sync
FULL_FRAME_DIAGONAL_MM = 43.27
PAIRS = [(1, 4), (2, 5), (3, 6), (7, 8), (9, 10), (11, 12), (13, 14), (15, 16), (17, 18), (19, 20), (21, 22),
         (23, 24), (25, 26), (27, 28), (29, 30), (31, 32)]
GROUPS = {"face": [p for p in PAIRS if p[0] < 11], "arms": [p for p in PAIRS if 11 <= p[0] < 23], "legs": [p for p in PAIRS if p[0] >= 23]}
SEGMENTS = {"upper_arm.L": (11, 13), "forearm.L": (13, 15), "upper_arm.R": (12, 14), "forearm.R": (14, 16),
            "thigh.L": (23, 25), "shin.L": (25, 27), "thigh.R": (24, 26), "shin.R": (26, 28),
            "hips": (23, 24), "shoulders": (11, 12)}


def swap_perm(groups):
    perm = np.arange(33)
    for g in groups:
        for a, b in GROUPS[g]:
            perm[a], perm[b] = b, a
    return perm


# ---------- sync ----------

def read_wav(path):
    with wave.open(path) as w:
        n, ch, sr, width = w.getnframes(), w.getnchannels(), w.getframerate(), w.getsampwidth()
        raw = np.frombuffer(w.readframes(n), {2: np.int16, 4: np.int32}[width]).astype(float)
    return raw.reshape(-1, ch).mean(1), sr


def envelope(x, sr):
    """Onsets: the high-passed sound's magnitude, its peak per 1/ENV_RATE s, minus a 50 ms running mean."""
    d = np.abs(np.diff(x))
    step = sr / ENV_RATE
    idx = (np.arange(int(len(d) / step)) * step).astype(int)
    env = np.maximum.reduceat(d, idx) if len(idx) else d[:0]
    k = int(0.05 * ENV_RATE)
    base = np.convolve(env, np.ones(k) / k, mode="same")
    e = np.maximum(env - base, 0)
    return e / (e.max() + 1e-12)


def audio_offset(a, sr_a, b, sr_b, max_lag_s=30.0):
    """Seconds to add to a time in A's sound to get the same instant in B's, and a confidence (peak over next peak)."""
    ea, eb = envelope(a, sr_a), envelope(b, sr_b)
    n = 1 << int(np.ceil(np.log2(len(ea) + len(eb))))
    c = np.fft.irfft(np.fft.rfft(eb, n) * np.conj(np.fft.rfft(ea, n)), n)
    lags = np.concatenate([np.arange(0, n // 2), np.arange(-n // 2, 0)])
    ok = np.abs(lags) <= max_lag_s * ENV_RATE
    c = np.where(ok, c, -np.inf)
    k = int(np.argmax(c))
    y0, y1, y2 = c[k - 1], c[k], c[(k + 1) % n]
    frac = 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2) if np.isfinite([y0, y2]).all() and (y0 - 2 * y1 + y2) != 0 else 0.0
    near = np.abs(lags - lags[k]) < 0.02 * ENV_RATE
    second = np.max(np.where(near | ~ok, -np.inf, c))
    return (lags[k] + frac) / ENV_RATE, float(y1 / second) if second > 0 else float("inf")


# ---------- cameras ----------

def focal_guess(w, h, mm_equiv):
    return float(np.hypot(w, h) * mm_equiv / FULL_FRAME_DIAGONAL_MM)


def K_of(f, w, h):
    return np.array([[f, 0, w / 2], [0, f, h / 2], [0, 0, 1.0]])


def triangulate(Pa, Pb, xa, xb):
    """Linear (DLT) triangulation of N points seen by two 3x4 cameras."""
    A = np.stack([xa[:, :1] * Pa[2] - Pa[0], xa[:, 1:2] * Pa[2] - Pa[1], xb[:, :1] * Pb[2] - Pb[0], xb[:, 1:2] * Pb[2] - Pb[1]], 1)
    A /= np.linalg.norm(A, axis=2, keepdims=True) + 1e-12
    X = np.linalg.svd(A)[2][:, -1]
    return X[:, :3] / X[:, 3:4]


def project(P, X):
    x = X @ P[:, :3].T + P[:, 3]
    return x[:, :2] / x[:, 2:3]


def unit_from(theta, phi):
    return np.array([np.sin(theta) * np.cos(phi), np.sin(theta) * np.sin(phi), np.cos(theta)])


class Cameras:
    def __init__(self, fa, fb, R, t, size_a, size_b):
        self.fa, self.fb, self.R, self.t, self.size_a, self.size_b = fa, fb, R, t, size_a, size_b

    @property
    def Pa(self):
        return K_of(self.fa, *self.size_a) @ np.hstack([np.eye(3), np.zeros((3, 1))])

    @property
    def Pb(self):
        return K_of(self.fb, *self.size_b) @ np.hstack([self.R, self.t[:, None]])

    def residuals(self, xa, xb):
        X = triangulate(self.Pa, self.Pb, xa, xb)
        return np.concatenate([(project(self.Pa, X) - xa).ravel(), (project(self.Pb, X) - xb).ravel()]), X


RIGID = [(11, 13), (13, 15), (12, 14), (14, 16), (23, 25), (25, 27), (24, 26), (26, 28)]  # arm, forearm, thigh, shin
BONE_WEIGHT = 100.0  # a bone 1% off its median length weighs like 1 px of reprojection
MAX_BONE_FRAMES = 150


def calibrate(xa, xb, size_a, size_b, mm_equiv, frames_a=None, frames_b=None, refine_focal=True, max_points=6000, seed=0):
    """B's pose relative to A (unit baseline) and both focal lengths, from matched pixel points.
    Two views of points can't tell the focal length: a wrong one reprojects as well and only stretches depth. Bones can:
    with frames_a/frames_b (F, 33, 2), whole frames seen well by both, each limb bone's length is held to its median.
    Synthetic test (test_two_cameras.py, focal guessed 8% short), median 3D error after a rigid fit, 2D noise 1.5 / 5 / 10 px:
    refined 6.2 / 20 / 43 mm, fixed 6.4 / 29 / 54 mm. With the noise the refined focal itself ends 20 to 40% long, yet the
    3D is better, since the bones also steady B's pose. refine_focal=False (--fixed-focal) keeps the lens's."""
    fa0, fb0 = focal_guess(*size_a, mm_equiv), focal_guess(*size_b, mm_equiv)
    Ka, Kb = K_of(fa0, *size_a), K_of(fb0, *size_b)
    na = cv2.undistortPoints(xa.reshape(-1, 1, 2), Ka, None).reshape(-1, 2)
    nb = cv2.undistortPoints(xb.reshape(-1, 1, 2), Kb, None).reshape(-1, 2)
    E, mask = cv2.findEssentialMat(na, nb, np.eye(3), method=cv2.RANSAC, prob=0.999, threshold=4.0 / fa0)
    if E is None:
        raise SystemExit("no essential matrix: the views share too few well-seen landmarks")
    E = E[:3]
    _, R, t, _ = cv2.recoverPose(E, na, nb, np.eye(3), mask=mask)
    t = t.ravel() / np.linalg.norm(t)
    inl = mask.ravel() > 0
    rng = np.random.default_rng(seed)
    pick = np.flatnonzero(inl)
    if len(pick) > max_points:
        pick = rng.choice(pick, max_points, replace=False)
    sa, sb = xa[pick], xb[pick]
    theta, phi = np.arccos(np.clip(t[2], -1, 1)), np.arctan2(t[1], t[0])
    p0 = np.concatenate([cv2.Rodrigues(R)[0].ravel(), [theta, phi, np.log(fa0), np.log(fb0)]])
    n_free = 7 if refine_focal else 5
    prior = np.log([fa0, fb0])
    if frames_a is not None and len(frames_a) > MAX_BONE_FRAMES:
        keep = np.linspace(0, len(frames_a) - 1, MAX_BONE_FRAMES).astype(int)
        frames_a, frames_b = frames_a[keep], frames_b[keep]
    seg = np.array(RIGID)

    def bones(cams):
        if frames_a is None or not len(frames_a):
            return np.zeros(0)
        X = triangulate(cams.Pa, cams.Pb, frames_a.reshape(-1, 2), frames_b.reshape(-1, 2)).reshape(len(frames_a), 33, 3)
        L = np.linalg.norm(X[:, seg[:, 0]] - X[:, seg[:, 1]], axis=2)
        return ((L / np.median(L, axis=0) - 1) * BONE_WEIGHT).ravel()

    def unpack(p):
        p = np.concatenate([p, p0[len(p):]])
        return Cameras(np.exp(p[5]), np.exp(p[6]), cv2.Rodrigues(p[:3])[0], unit_from(p[3], p[4]), size_a, size_b)

    def fun(p):
        c = unpack(p)
        r, _ = c.residuals(sa, sb)
        if not refine_focal:
            return r
        return np.concatenate([r, bones(c), (p[5:7] - prior) / 0.3])  # focal lengths held loosely near the lens's (one pixel per 30% off)

    sol = least_squares(fun, p0[:n_free], loss="huber", f_scale=3.0, x_scale="jac", max_nfev=200)
    cams = unpack(sol.x)
    r, _ = cams.residuals(sa, sb)
    err = np.linalg.norm(r.reshape(2, -1, 2), axis=2)
    b = bones(cams) / BONE_WEIGHT * 100
    return cams, {"focal_refined": refine_focal, "bone_frames": 0 if frames_a is None else int(len(frames_a)), "bone_variation_pct_rms": float(np.sqrt(np.mean(b ** 2))) if len(b) else None,
                  "essential_inliers": int(inl.sum()), "points_used": int(len(pick)), "focal_px_a": cams.fa, "focal_px_b": cams.fb,
                  "focal_guess_px_a": fa0, "focal_guess_px_b": fb0, "reprojection_px_median": [float(np.median(e)) for e in err],
                  "reprojection_px_p95": [float(np.percentile(e, 95)) for e in err]}


# ---------- per frame ----------

def frame_error(cams, xa, xb, idx):
    r, X = cams.residuals(xa[idx], xb[idx])
    return float(np.median(np.abs(r))) if len(idx) else np.inf, X


def solve_frames(cams, la, lb):
    """3D per frame with left/right swaps resolved. la, lb: (T, 33, 3) pixels and visibility, B already at A's times.
    Returns the points, which groups were swapped, and la, lb relabelled."""
    T = len(la)
    X = np.full((T, 33, 3), np.nan)
    LA, LB = la.copy(), lb.copy()
    swapped = np.zeros((T, len(GROUPS), 2), bool)
    prev = None
    for t in range(T):
        xa, xb = la[t, :, :2].copy(), lb[t, :, :2].copy()
        va, vb = la[t, :, 2], lb[t, :, 2]
        if not (np.isfinite(xa).all() and np.isfinite(xb).all()):
            continue
        for gi, g in enumerate(GROUPS):
            idx = np.array([i for p in GROUPS[g] for i in p])
            good = idx[(va[idx] > 0.3) & (vb[idx] > 0.3)]
            if len(good) < 2:
                continue
            perm = swap_perm([g])
            e_none, _ = frame_error(cams, xa, xb, good)
            e_swap, _ = frame_error(cams, xa, xb[perm], good)
            if e_swap < 0.7 * e_none:
                # B swapped, or A swapped: same geometry, labels mirrored; keep the one continuous with the last frame
                Xb = triangulate(cams.Pa, cams.Pb, xa[idx], xb[perm][idx])
                Xa = triangulate(cams.Pa, cams.Pb, xa[perm][idx], xb[idx])
                if prev is not None and np.isfinite(prev[idx]).all() and np.linalg.norm(Xa - prev[idx]) < np.linalg.norm(Xb - prev[idx]):
                    xa = xa[perm]
                    va = va[perm]
                    swapped[t, gi, 0] = True
                else:
                    xb = xb[perm]
                    vb = vb[perm]
                    swapped[t, gi, 1] = True
        X[t] = triangulate(cams.Pa, cams.Pb, xa, xb)
        LA[t, :, :2], LA[t, :, 2], LB[t, :, :2], LB[t, :, 2] = xa, va, xb, vb
        prev = X[t]
    return X, swapped, LA, LB


# A body with rigid bones fitted to both views: each landmark pulls by its visibility, so a view that only guesses a
# hidden limb gives way to the one that sees it; bones keep their length; the pose moves little from the last frame.
SKELETON = [(11, 12), (23, 24), (11, 23), (12, 24), (11, 24), (12, 23),  # trunk, braced so it can't shear
            (11, 13), (13, 15), (12, 14), (14, 16), (15, 17), (15, 19), (17, 19), (16, 18), (16, 20), (18, 20),
            (23, 25), (25, 27), (24, 26), (26, 28), (27, 29), (29, 31), (27, 31), (28, 30), (30, 32), (28, 32)]
FIT = np.arange(11, 33)  # the head is left to the triangulation (Rafael: ignore it for now)
FIT_REPROJ_SCALE = 5.0  # px: Huber's knee for a landmark's reprojection
FIT_BONE_WEIGHT = 300.0  # a bone 1% off its length weighs 3 px
FIT_STILL_WEIGHT = 0.3  # moving a thigh's length from the last frame weighs 30 px
VIS_FLOOR = 0.05


def bone_lengths(X, la, lb, vis=0.8):
    """Each bone's median length over the frames where both views see both its ends well."""
    out = {}
    for a, b in SKELETON:
        ok = (la[:, a, 2] > vis) & (la[:, b, 2] > vis) & (lb[:, a, 2] > vis) & (lb[:, b, 2] > vis)
        d = np.linalg.norm(X[ok, a] - X[ok, b], axis=1)
        d = d[np.isfinite(d)]
        if len(d) < 5:
            d = np.linalg.norm(X[:, a] - X[:, b], axis=1)
            d = d[np.isfinite(d)]
        out[(a, b)] = (float(np.median(d)), int(ok.sum()))
    return out


def fit_sparsity(n, ia, ib, still):
    """Which residuals each coordinate moves: its own reprojections, its bones, its own stillness. Without it the
    numerical Jacobian costs a residual evaluation per coordinate (the first full run took over 10 minutes)."""
    cols = lambda j: [3 * j, 3 * j + 1, 3 * j + 2]
    rows = 4 * n + len(ia) + (3 * n if still else 0)
    S = np.zeros((rows, 3 * n), bool)
    for j in range(n):
        S[2 * j:2 * j + 2, cols(j)] = True
        S[2 * n + 2 * j:2 * n + 2 * j + 2, cols(j)] = True
        if still:
            S[4 * n + len(ia) + 3 * j:4 * n + len(ia) + 3 * j + 3, cols(j)] = True
    for k, (a, b) in enumerate(zip(ia, ib)):
        S[4 * n + k, cols(a) + cols(b)] = True
    return S


def fit_skeleton(cams, X0, la, lb, lengths):
    """Per frame, the landmarks FIT as a body with rigid bones, from the triangulated start. Returns points and per-frame
    reprojection error (px, visibility-weighted mean over FIT, per view)."""
    T = len(X0)
    X = X0.copy()
    err = np.full((T, 2), np.nan)
    pairs = np.array(list(lengths))
    L = np.array([lengths[tuple(p)][0] for p in pairs])
    ref = lengths[(23, 25)][0]
    prev = None
    for t in range(T):
        if not np.isfinite(X0[t, FIT]).all() or not np.isfinite(la[t, FIT, :2]).all() or not np.isfinite(lb[t, FIT, :2]).all():
            continue
        wa = np.sqrt(np.clip(la[t, FIT, 2], VIS_FLOOR, 1))[:, None]
        wb = np.sqrt(np.clip(lb[t, FIT, 2], VIS_FLOOR, 1))[:, None]
        start = X0[t, FIT]  # from this frame's triangulation: starting from the last fit, the fit fell behind the motion (2026-11-14)
        idx = {j: k for k, j in enumerate(FIT)}
        ia, ib = np.array([idx[a] for a, _ in pairs]), np.array([idx[b] for _, b in pairs])

        def fun(p):
            Y = p.reshape(-1, 3)
            ra = (project(cams.Pa, Y) - la[t, FIT, :2]) * wa
            rb = (project(cams.Pb, Y) - lb[t, FIT, :2]) * wb
            rl = (np.linalg.norm(Y[ia] - Y[ib], axis=1) / L - 1) * FIT_BONE_WEIGHT
            rs = ((Y - prev) / ref * 100 * FIT_STILL_WEIGHT).ravel() if prev is not None else np.zeros(0)
            return np.concatenate([ra.ravel(), rb.ravel(), rl, rs])

        sol = least_squares(fun, start.ravel(), loss="huber", f_scale=FIT_REPROJ_SCALE, max_nfev=200, x_scale="jac",
                            jac_sparsity=fit_sparsity(len(FIT), ia, ib, prev is not None))
        Y = sol.x.reshape(-1, 3)
        X[t, FIT] = Y
        w_a, w_b = np.clip(la[t, FIT, 2], VIS_FLOOR, 1), np.clip(lb[t, FIT, 2], VIS_FLOOR, 1)
        err[t] = [np.sum(np.linalg.norm(project(cams.Pa, Y) - la[t, FIT, :2], axis=1) * w_a) / w_a.sum(),
                  np.sum(np.linalg.norm(project(cams.Pb, Y) - lb[t, FIT, :2], axis=1) * w_b) / w_b.sum()]
        prev = Y
    return X, err


def to_metric(X, height, scale_from="ears"):
    """Upright, on the floor, in metres, Blender axes; returns points and a report. scale_from: ears or shoulders."""
    mid = lambda a, b: (X[:, a] + X[:, b]) / 2
    up_dirs = mid(11, 12) - mid(27, 28)
    up_dirs = up_dirs[np.isfinite(up_dirs).all(1)]
    up = np.median(up_dirs / np.linalg.norm(up_dirs, axis=1, keepdims=True), axis=0)
    up /= np.linalg.norm(up)
    feet = X[:, [29, 30, 31, 32]].reshape(-1, 3)
    feet = feet[np.isfinite(feet).all(1)]
    floor = np.percentile(feet @ up, 2)
    ref, ratio = (mid(7, 8), EAR_RATIO) if scale_from == "ears" else (mid(11, 12), SHOULDER_RATIO)
    ref_h = np.nanpercentile(ref @ up - floor, 75)
    scale = height * ratio / ref_h
    first = X[: max(1, min(len(X), 30))]
    lr = np.nanmedian(first[:, 23] - first[:, 24], axis=0)
    x = lr - (lr @ up) * up
    x /= np.linalg.norm(x)
    y = np.cross(up, x)
    hips0 = np.nanmedian(mid(23, 24)[: len(first)], axis=0)
    origin = hips0 - (hips0 @ up - floor) * up
    M = np.stack([x, y, up])
    P = (X - origin) @ M.T * scale
    return P, {"scale_to_m": float(scale), "up_in_camera_a": up.tolist(), "scale_from": scale_from, "reference_height_m": float(height * ratio)}


def bone_variation(P):
    out = {}
    for name, (a, b) in SEGMENTS.items():
        d = np.linalg.norm(P[:, a] - P[:, b], axis=1)
        d = d[np.isfinite(d)]
        if len(d):
            out[name] = {"mean_m": round(float(d.mean()), 4), "variation_pct": round(float(d.std() / d.mean() * 100), 2)}
    return out


def resample(lm, times_src, times_dst):
    """Landmarks (T, 33, 4) at other times, linearly; NaN outside the source's span."""
    out = np.full((len(times_dst), 33, 3), np.nan)
    inside = (times_dst >= times_src[0]) & (times_dst <= times_src[-1])
    for j in range(33):
        for c, src in enumerate((0, 1, 3)):
            v = lm[:, j, src]
            ok = np.isfinite(v)
            if ok.sum() > 1:
                out[inside, j, c] = np.interp(times_dst[inside], times_src[ok], v[ok])
    return out


# ---------- video ----------

def draw(frame, mp_pts, rep, colour):
    for a, b in [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28), (27, 29), (29, 31), (28, 30), (30, 32), (7, 8)]:
        if np.isfinite(rep[[a, b]]).all():
            c = (255, 160, 40) if a % 2 == 1 and b % 2 == 1 else (40, 120, 255) if a % 2 == 0 and b % 2 == 0 else (0, 220, 0)
            cv2.line(frame, tuple(rep[a].astype(int)), tuple(rep[b].astype(int)), c, 3, cv2.LINE_AA)
    for p in mp_pts:
        if np.isfinite(p[:2]).all():
            cv2.circle(frame, tuple(p[:2].astype(int)), 5, colour, -1, cv2.LINE_AA)


def panel(P, axes, title, size=480, scale=200):
    img = np.full((size, size, 3), 30, np.uint8)
    cv2.putText(img, title, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (230, 230, 230), 2, cv2.LINE_AA)
    cv2.line(img, (0, size - 40), (size, size - 40), (90, 90, 90), 1)
    if np.isfinite(P).all():
        c = P[[23, 24]].mean(0)
        u = (P[:, axes[0]] - c[axes[0]]) * scale + size / 2
        v = size - 40 - P[:, 2] * scale
        for a, b in [(11, 12), (11, 13), (13, 15), (12, 14), (14, 16), (11, 23), (12, 24), (23, 24), (23, 25), (25, 27), (24, 26), (26, 28), (27, 29), (29, 31), (28, 30), (30, 32), (7, 8), (0, 7), (0, 8)]:
            col = (255, 160, 40) if a % 2 == 1 and b % 2 == 1 else (40, 120, 255) if a % 2 == 0 and b % 2 == 0 else (200, 200, 200)
            cv2.line(img, (int(u[a]), int(v[a])), (int(u[b]), int(v[b])), col, 3, cv2.LINE_AA)
    return img


def write_overlay(path, video_a, video_b, la_full, lb_at_a, X, P, cams, times_a, times_b_at_a, times_b, fps, first_frame=0):
    ca, cb = cv2.VideoCapture(video_a), cv2.VideoCapture(video_b)
    for c in (ca, cb):
        c.set(cv2.CAP_PROP_ORIENTATION_AUTO, 1)  # as capture_pose.py: phone videos' rotation
    for _ in range(first_frame):  # read, not seek: seeking a variable-frame-rate video can land off by a frame
        ca.read()
    H = 960
    writer = None
    bi, fb = -1, None
    for t in range(len(times_a)):
        ok, fa = ca.read()
        if not ok:
            break
        target = times_b_at_a[t]
        while bi + 1 < len(times_b) and (bi < 0 or abs(times_b[bi + 1] - target) <= abs(times_b[bi] - target)):
            ok, f = cb.read()
            if not ok:
                break
            bi, fb = bi + 1, f
        if fb is None:
            fb = np.zeros_like(fa)
        A, B = fa.copy(), fb.copy()
        if np.isfinite(X[t]).all():
            draw(A, la_full[t], project(cams.Pa, X[t]), (255, 255, 255))
            draw(B, lb_at_a[t], project(cams.Pb, X[t]), (255, 255, 255))
        A = cv2.resize(A, (A.shape[1] * H // A.shape[0], H))
        B = cv2.resize(B, (B.shape[1] * H // B.shape[0], H))
        cv2.putText(A, f"camera A  t={times_a[t]:.2f}s", (16, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.putText(B, f"camera B  t={target:.2f}s", (16, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
        side = np.vstack([panel(P[t], (0, 2), "3D frente"), panel(P[t], (1, 2), "3D lado")])
        frame = np.hstack([A, B, side])
        if writer is None:
            writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (frame.shape[1], frame.shape[0]))
        writer.write(frame)
    if writer:
        writer.release()


# ---------- main ----------

def main(argv):
    opts = {"--height": 1.70, "--focal-mm": 26.0, "--offset": None, "--from": None, "--to": None}
    scale_from = "shoulders" if "--scale-shoulders" in argv else "ears"
    argv = [a for a in argv if a != "--scale-shoulders"]
    fit = "--no-skeleton" not in argv
    argv = [a for a in argv if a != "--no-skeleton"]
    refine = "--fixed-focal" not in argv
    argv = [a for a in argv if a != "--fixed-focal"]
    rest = []
    i = 0
    while i < len(argv):
        if argv[i] in opts:
            opts[argv[i]] = float(argv[i + 1])
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    npz_a, npz_b, wav_a, wav_b, meta_path, video_a, video_b, out = rest
    os.makedirs(out, exist_ok=True)
    A, B = np.load(npz_a), np.load(npz_b)
    meta = json.load(open(meta_path))
    report = {"height_m": opts["--height"], "focal_mm_equiv": opts["--focal-mm"]}

    if opts["--offset"] is None:
        if not (os.path.exists(wav_a) and os.path.exists(wav_b)):
            raise SystemExit("Um dos vídeos não tem som: sem a palma não há como sincronizar. Use --offset SEGUNDOS.")
        a, sra = read_wav(wav_a)
        b, srb = read_wav(wav_b)
        audio_off, conf = audio_offset(a, sra, b, srb)
        report["clap_offset_s"], report["clap_confidence"] = audio_off, conf
        # a video time in A -> the same instant's video time in B
        if None in (meta["a"]["audio_start"], meta["b"]["audio_start"]):
            raise SystemExit("meta.json sem o início do som")
        d = audio_off + (meta["b"]["audio_start"] - meta["b"]["video_start"]) - (meta["a"]["audio_start"] - meta["a"]["video_start"])
        if conf < 1.5:
            print(f"ATENÇÃO: a palma não se destaca no som (confiança {conf:.2f}); confira o vídeo ou use --offset")
    else:
        d = opts["--offset"]
    report["video_offset_s"] = d
    ta, tb = A["times"], B["times"]
    image_a = A["image"]
    lo = opts["--from"] if opts["--from"] is not None else -np.inf
    hi = opts["--to"] if opts["--to"] is not None else np.inf
    sel = np.flatnonzero((ta >= lo) & (ta <= hi))
    first_frame = int(sel[0])
    ta, image_a = ta[sel], image_a[sel]
    report["from_s"], report["to_s"], report["first_frame_a"] = float(ta[0]), float(ta[-1]), first_frame
    la = image_a[:, :, [0, 1, 3]]
    lb = resample(B["image"], tb, ta + d)
    size_a, size_b = (int(A["width"]), int(A["height"])), (int(B["width"]), int(B["height"]))

    both = (la[:, :, 2] > VIS_MIN) & (lb[:, :, 2] > VIS_MIN) & np.isfinite(la[:, :, 0]) & np.isfinite(lb[:, :, 0])
    xa, xb = la[:, :, :2][both], lb[:, :, :2][both]
    whole = both[:, [i for s in RIGID for i in s]].all(1)
    cams, cal = calibrate(xa, xb, size_a, size_b, opts["--focal-mm"], la[whole, :, :2], lb[whole, :, :2], refine_focal=refine)
    report["cameras"] = cal
    report["cameras"]["R_b"] = cams.R.tolist()
    report["cameras"]["t_b_unit"] = cams.t.tolist()
    report["cameras"]["angle_between_deg"] = float(np.degrees(np.arccos(np.clip((np.trace(cams.R) - 1) / 2, -1, 1))))

    X_dlt, swapped, la_r, lb_r = solve_frames(cams, la, lb)
    if fit:
        lengths = bone_lengths(X_dlt, la_r, lb_r)
        X, fit_err = fit_skeleton(cams, X_dlt, la_r, lb_r, lengths)
        report["skeleton_fit"] = {"bone_frames_seen_well": {f"{a}-{b}": n for (a, b), (_, n) in lengths.items()},
                                  "reprojection_px_median": [float(np.nanmedian(fit_err[:, i])) for i in range(2)],
                                  "reprojection_px_p95": [float(np.nanpercentile(fit_err[:, i], 95)) for i in range(2)]}
    else:
        X = X_dlt
    P, metric = to_metric(X, opts["--height"], scale_from)
    report["metric"] = metric
    report["cameras"]["baseline_m"] = metric["scale_to_m"]
    report["frames"] = int(len(ta))
    report["frames_with_3d"] = int(np.isfinite(X).all(axis=(1, 2)).sum())
    report["swaps"] = {g: {"a": int(swapped[:, gi, 0].sum()), "b": int(swapped[:, gi, 1].sum())} for gi, g in enumerate(GROUPS)}
    report["bones"] = bone_variation(P)
    errs = []
    for t in range(len(X)):
        if np.isfinite(X[t]).all():
            errs.append(np.linalg.norm(project(cams.Pa, X[t]) - la[t, :, :2], axis=1).mean())
    report["frame_reprojection_px_a_median"] = float(np.median(errs)) if errs else None

    world_mp = P - (P[:, 23:24] + P[:, 24:25]) / 2
    world_mp = np.stack([world_mp[..., 0], -world_mp[..., 2], world_mp[..., 1]], -1)  # inverse of drive_capture's (x, z, -y)
    found = np.isfinite(P).all(axis=(1, 2))
    np.savez_compressed(os.path.join(out, "two_cameras.npz"), points_m=P, world=world_mp, found=found, times=ta, fps=float(A["fps"]),
                        swapped=swapped, image=image_a)
    json.dump(report, open(os.path.join(out, "two_cameras.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in report.items() if k not in ("bones",)}, indent=1)[:2500])
    write_overlay(os.path.join(out, "two_cameras_overlay.mp4"), video_a, video_b, image_a, lb, X, P, cams, ta, ta + d, tb, float(A["fps"]), first_frame)


if __name__ == "__main__":
    if len(sys.argv) < 9:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1:])

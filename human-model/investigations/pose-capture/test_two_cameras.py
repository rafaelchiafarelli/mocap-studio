"""Synthetic check of two_cameras.py: a known motion (clip 0100's MediaPipe world landmarks, as if true) seen by two virtual
phones, with noise, a clap at a known offset and left/right swaps; the solve must recover them.
    human-model/hm.sh --ref python human-model/investigations/pose-capture/test_two_cameras.py
NOISE_PX (default 1.5) sets the 2D noise, FIXED_FOCAL=1 keeps the guessed focal. Needs G:'s 01_mediapipe_0100.npz (step 1's output); skips without it."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import two_cameras as tc

SRC = "/mnt/g/mocap-studio-downloads/review/2026-11-14/pose_capture/01_mediapipe_0100.npz"


def look(cam_pos, target):
    f = target - cam_pos; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
    d = np.cross(f, r)  # image y down
    R = np.stack([r, d, f])
    return R, -R @ cam_pos


CHAINS = [((11, 13), [13]), ((13, 15), [15, 17, 19, 21]), ((12, 14), [14]), ((14, 16), [16, 18, 20, 22]),
          ((23, 25), [25]), ((25, 27), [27, 29, 31]), ((24, 26), [26]), ((26, 28), [28, 30, 32])]


def rigidify(X):
    """MediaPipe's own 3D bones stretch by ~10%; a real body's don't. Each limb bone is set to its median length, root to tip,
    carrying the points beyond it."""
    X = X.copy()
    for (a, b), moved in CHAINS:
        L = np.linalg.norm(X[:, b] - X[:, a], axis=1)
        d = (X[:, b] - X[:, a]) * (np.median(L) / L - 1)[:, None]
        X[:, moved] += d[:, None, :]
    return X


def test_sync():
    rng = np.random.default_rng(1)
    def track(sr, clap_s, n_s=8.0):
        x = rng.normal(0, 200, int(n_s * sr))
        i = int(clap_s * sr)
        x[i:i + int(0.004 * sr)] += rng.normal(0, 20000, int(0.004 * sr)) * np.exp(-np.arange(int(0.004 * sr)) / (0.001 * sr))
        return x
    a, b = track(48000, 2.000), track(44100, 2.4567)
    off, conf = tc.audio_offset(a, 48000, b, 44100)
    print(f"sync: offset {off:.4f} s (true 0.4567), confidence {conf:.1f}")
    assert abs(off - 0.4567) < 0.002 and conf > 1.5


def test_solve():
    d = np.load(SRC)
    w = d["world"]
    true = np.stack([w[..., 0], w[..., 2], -w[..., 1]], -1)  # Blender axes, origin at the hips
    true = rigidify(true)
    true[..., 2] += 0.95
    true *= 1.0 / 0.95 * 0.93 * 1.70 / np.nanpercentile((true[:, 7, 2] + true[:, 8, 2]) / 2 - np.percentile(true[:, 29:33, 2], 2), 75) * 0.95
    T = len(true)
    size = (1080, 1920)
    f_true = tc.focal_guess(*size, 26) * 1.08
    K = tc.K_of(f_true, *size)
    poses = [look(np.array([0.3, -3.6, 1.1]), np.array([0, 0, 0.9])), look(np.array([3.2, -1.8, 1.3]), np.array([0, 0, 0.9]))]
    rng = np.random.default_rng(2)
    views = []
    for R, t in poses:
        x = (true.reshape(-1, 3) @ R.T + t) @ K.T
        x = x[:, :2] / x[:, 2:3] + rng.normal(0, float(os.environ.get("NOISE_PX", 1.5)), (len(x), 2))
        views.append(np.concatenate([x.reshape(T, 33, 2), np.ones((T, 33, 1))], -1))
    la, lb = views
    perm = tc.swap_perm(["legs"])
    swap_frames = rng.choice(np.arange(10, T), T // 10, replace=False)
    lb[swap_frames] = lb[swap_frames][:, perm]
    both = la[:, :, 2] > 0
    ok = np.setdiff1d(np.arange(T), swap_frames)
    cams, cal = tc.calibrate(la[:, :, :2][both], lb[:, :, :2][both], size, size, 26, la[ok, :, :2], lb[ok, :, :2], refine_focal=os.environ.get("FIXED_FOCAL") != "1")
    print("cameras:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in cal.items()}, "true f", round(f_true, 1))
    X, swapped = tc.solve_frames(cams, la, lb)
    P, metric = tc.to_metric(X, 1.70)
    # rigid alignment without reflection: a mirrored result (left for right) can't fit
    A, B = P.reshape(-1, 3), true.reshape(-1, 3)
    ca, cb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    D = np.diag([1, 1, np.sign(np.linalg.det(U @ Vt))])
    Rk = (U @ D @ Vt).T
    err = np.linalg.norm((A - ca) @ Rk.T + cb - B, axis=1)
    found = int(swapped[:, 2, 1].sum() + swapped[:, 2, 0].sum())
    print(f"3D error after rigid fit: median {np.median(err)*1000:.1f} mm, p95 {np.percentile(err,95)*1000:.1f} mm; "
          f"leg swaps inserted {len(swap_frames)}, found {found}; scale {metric['scale_to_m']:.3f}")
    assert np.median(err) < 0.02 * max(1.0, float(os.environ.get("NOISE_PX", 1.5)) / 3) and abs(found - len(swap_frames)) <= 2
    if cal["focal_refined"] and float(os.environ.get("NOISE_PX", 1.5)) <= 2:
        assert abs(cal["focal_px_a"] / f_true - 1) < 0.05


if __name__ == "__main__":
    test_sync()
    if os.path.exists(SRC):
        test_solve()
    else:
        print("skip test_solve: no", SRC)
    print("ok")

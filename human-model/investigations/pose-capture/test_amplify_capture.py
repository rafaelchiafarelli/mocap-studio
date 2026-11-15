"""Checks amplify_capture.py on a synthetic body: every gain at 1 changes nothing, a gain on the pelvis's sway multiplies it,
bones keep their lengths, and slow turns and fast noise are left alone.
    human-model/hm.sh --ref python human-model/investigations/pose-capture/test_amplify_capture.py"""
import os, sys
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import amplify_capture as ac

FPS = 30.0
T = 300
ONES = {r: 1.0 for r in ac.REGIONS}
# a standing body in MediaPipe's world axes (x right of the image, y down, z away), metres, origin between the hips
REST = np.zeros((33, 3))
for i in range(11):
    REST[i] = [0.02 * (i - 5), -0.62, -0.08 if i == 0 else 0.0]
REST[7], REST[8] = [0.08, -0.6, 0.0], [-0.08, -0.6, 0.0]
for side, s in (("l", 1), ("r", -1)):
    REST[ac.L[f"sh_{side}"]] = [0.18 * s, -0.5, 0]
    REST[ac.L[f"el_{side}"]] = [0.22 * s, -0.22, 0.02]
    REST[ac.L[f"wr_{side}"]] = [0.24 * s, 0.03, -0.05]
    REST[ac.L[f"hip_{side}"]] = [0.1 * s, 0, 0]
    REST[ac.L[f"knee_{side}"]] = [0.11 * s, 0.42, -0.03]
    REST[ac.L[f"ank_{side}"]] = [0.11 * s, 0.82, 0.02]
for i, j in ((17, 15), (18, 16), (19, 15), (20, 16), (21, 15), (22, 16), (29, 27), (30, 28), (31, 27), (32, 28)):
    REST[i] = REST[j] + [0, 0.05, -0.03 if i < 29 else -0.1]


def body(sway_deg=8.0, turn_deg=0.0, noise_deg=0.0, seed=0):
    """The whole body rocked about the hips (sway at 1.5 Hz), slowly turned, and shaken."""
    t = np.arange(T) / FPS
    rng = np.random.default_rng(seed)
    X = np.empty((T, 33, 3))
    for k in range(T):
        rot = (Rotation.from_euler("y", turn_deg * t[k] / t[-1], degrees=True)
               * Rotation.from_euler("z", sway_deg * np.sin(2 * np.pi * 1.5 * t[k]), degrees=True)
               * Rotation.from_rotvec(np.radians(noise_deg) * rng.normal(size=3)))
        X[k] = rot.apply(REST)
    return X


def pelvis_roll(X):
    F = ac.world_frames(X)["pelvis"]
    return np.degrees(np.arcsin(np.clip(F[:, 1, 0], -1, 1)))  # the hip line's tilt out of horizontal


def bone_lengths(X):
    pairs = [(11, 13), (13, 15), (12, 14), (14, 16), (23, 25), (25, 27), (24, 26), (26, 28), (23, 24), (11, 12)]
    return np.stack([np.linalg.norm(X[:, a] - X[:, b], axis=1) for a, b in pairs], 1)


def test_identity():
    X = body(turn_deg=90, noise_deg=1.0)
    path = np.cumsum(np.full((T, 3), 0.002), 0)
    Y, P, _ = ac.amplify(X, ONES, fps=FPS, hips_path=path)
    assert np.abs(Y - X).max() < 1e-9, np.abs(Y - X).max()
    assert np.abs(P - path).max() < 1e-12


def test_sway_gain():
    X = body(sway_deg=8.0)
    for g in (0.5, 2.0, 3.0):
        Y, _, rep = ac.amplify(X, {**ONES, "hips": g}, fps=FPS)
        mid = slice(60, T - 60)  # away from the edges, where the base is held
        a, b = np.ptp(pelvis_roll(X)[mid]), np.ptp(pelvis_roll(Y)[mid])
        assert abs(b / a - g) < 0.06 * g, (g, a, b)
        assert np.abs(bone_lengths(Y) - bone_lengths(X)).max() < 1e-9
        assert abs(rep["pelvis"]["motion_deg_rms_after"] / rep["pelvis"]["motion_deg_rms"] - g) < 1e-9


def test_turn_and_noise_kept():
    """A slow turn is base, not motion; noise is kept at --noise 1 and removed at 0."""
    X = body(sway_deg=0.0, turn_deg=120, noise_deg=0.0)
    Y, _, _ = ac.amplify(X, {r: 3.0 for r in ac.REGIONS}, fps=FPS)
    assert np.abs(Y - X)[30:-30].max() < 0.01, np.abs(Y - X)[30:-30].max()
    Xn = body(sway_deg=0.0, noise_deg=2.0)
    Y0, _, rep = ac.amplify(Xn, ONES, noise_gain=0.0, fps=FPS)
    assert rep["pelvis"]["noise_deg_rms"] > 1.0 and rep["pelvis"]["noise_deg_rms_after"] == 0
    # per-frame noise at 30 fps spreads evenly up to 15 Hz: the part over 6 Hz goes, the part under it reads as motion
    assert np.std(pelvis_roll(Y0)) < 0.8 * np.std(pelvis_roll(Xn))


def test_cli_limits():
    for args in (["a", "b", "--hips", "3.5"], ["a", "b", "--gain", "2", "--legs", "2"], ["a", "b", "--noise", "-1"]):
        try:
            ac.parse(args)
        except SystemExit as e:
            assert "from 0 to" in str(e)
        else:
            raise AssertionError(args)
    _, g, _ = ac.parse(["a", "b", "--gain", "1.5", "--hips", "2"])
    assert g["hips"] == 3.0 and g["arms"] == 1.5


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)

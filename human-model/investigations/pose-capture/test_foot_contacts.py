"""Checks foot_contacts.py on synthetic feet: a known floor tilt is found and removed, feet held still in the air don't bend the
floor, and contacts follow the planted foot.
    human-model/hm.sh --ref python human-model/investigations/pose-capture/test_foot_contacts.py"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import foot_contacts as fc

FPS = 30.0
T = 300


def walk(tilt_x=0.03, tilt_y=-0.17, noise_mm=5.0, seed=0):
    """Two feet stepping in turn, forward and zigzagging sideways, each standing still for 1 s then swinging 0.5 s; a shoe's heel 8 mm and
    ankle 75 mm above its toe. The floor is z = tilt_x x + tilt_y y. One pause with the left foot lifted 120 mm."""
    rng = np.random.default_rng(seed)
    P = np.full((T, 33, 3), 0.0)
    P[:, :, 2] = 1.0  # the rest of the body, well above the floor
    lift = np.zeros((T, 2))
    for f, side in enumerate(("left", "right")):
        phase = 0 if f == 0 else 22
        xy = np.zeros((T, 2))
        pos = np.array([0.1 * (1 if f == 0 else -1), -0.4])
        for t in range(T):
            c = (t + phase) % 45
            if c >= 30:  # swing: move 0.12 m forward with a 60 mm arc
                pos = pos + np.array([0.06 * np.sign(np.sin(t / 60)), 0.12]) / 15  # forward, and side to side
                lift[t, f] = 0.06 * np.sin(np.pi * (c - 30) / 15)
            xy[t] = pos
        if f == 0:
            lift[200:240, 0] = 0.12  # a foot held still in the air
        for p, (i, dz, dy) in enumerate(zip(fc.FEET[side], (0.075, 0.008, 0.0), (0.0, -0.05, 0.15))):
            x, y = xy[:, 0], xy[:, 1] + dy
            P[:, i] = np.stack([x, y, tilt_x * x + tilt_y * y + dz + lift[:, f]], -1)
    P[:, :, :] += rng.normal(0, noise_mm / 1000, P.shape) * (np.arange(33) >= 27)[None, :, None]
    return P, lift


def test_floor_found_and_levelled():
    P, _ = walk()
    v = fc.speeds(P, FPS)
    (a, b), resid, _ = fc.fit_floor(P, v, 0.3)
    assert abs(a - 0.03) < 0.01 and abs(b + 0.17) < 0.01, (a, b)
    L = P @ fc.level_rotation(a, b).T
    (a2, b2), _, _ = fc.fit_floor(L, fc.speeds(L, FPS), 0.3)
    assert abs(a2) < 0.005 and abs(b2) < 0.005, (a2, b2)
    assert resid < 0.01, resid


def test_contacts_follow_the_planted_foot():
    P, lift = walk(tilt_x=0, tilt_y=0, noise_mm=2.0)
    v = fc.speeds(P, FPS)
    heights = np.tile([0.075, 0.008, 0.0], (2, 1))
    C = fc.contacts(P, v, heights, 0.04, 0.3)
    planted = lift == 0
    agree = (C[:, :, 1] == planted)[5:-5].mean()  # heel
    assert agree > 0.85, agree
    assert not C[205:235, 0].any()  # held in the air: still, but not on the floor


def test_rotation_is_proper():
    R = fc.level_rotation(0.2, -0.1)
    assert np.allclose(R @ R.T, np.eye(3)) and np.isclose(np.linalg.det(R), 1)
    n = np.array([-0.2, 0.1, 1.0]); n /= np.linalg.norm(n)
    assert np.allclose(R @ n, [0, 0, 1])


if __name__ == "__main__":
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            f()
            print("ok", name)

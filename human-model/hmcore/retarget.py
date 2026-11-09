"""Actor to character: motion is carried as bone directions, so the character keeps its own proportions and the actor's lengths don't matter."""
import numpy as np

# rig bone: (from marker, to marker, parent rig bone); chain ends are the capture's named points
BODY_CHAINS = {
    "thigh.L": ("left_hip", "left_knee"), "shin.L": ("left_knee", "left_ankle"), "foot.L": ("left_heel", "left_foot_index"),
    "thigh.R": ("right_hip", "right_knee"), "shin.R": ("right_knee", "right_ankle"), "foot.R": ("right_heel", "right_foot_index"),
    "upper_arm.L": ("left_shoulder", "left_elbow"), "forearm.L": ("left_elbow", "left_wrist"),
    "upper_arm.R": ("right_shoulder", "right_elbow"), "forearm.R": ("right_elbow", "right_wrist"),
}


def rotation_between(a, b):
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(a @ b)
    if c < -0.9999:
        axis = np.cross(a, [1.0, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1.0, 0])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def facing_frame(lh, rh, ls, rs):
    """Rotation taking capture axes to model axes for one frame's trunk: X along right-to-left hip, Z up the trunk, Y back."""
    x = (lh - rh)
    x = x / np.linalg.norm(x)
    up = (ls + rs) / 2 - (lh + rh) / 2
    up = up - (up @ x) * x
    z = up / np.linalg.norm(up)
    y = np.cross(z, x)
    return np.stack([x, y, z])


def bone_length_stats(points, a, b):
    """Mean and coefficient of variation of a capture segment's length: a rigid bone shouldn't change."""
    d = np.linalg.norm(points[:, a] - points[:, b], axis=-1)
    d = d[np.isfinite(d)]
    return float(d.mean()), float(d.std() / d.mean()) if len(d) else (0.0, 0.0)


def jitter_mm(points):
    """Median frame-to-frame jump of a point after removing slow motion: tracking noise, in the capture's units."""
    p = points[np.isfinite(points).all(axis=1)]
    if len(p) < 5:
        return float("nan")
    smooth = np.column_stack([np.convolve(p[:, k], np.ones(5) / 5, mode="same") for k in range(3)])
    return float(np.median(np.linalg.norm((p - smooth)[2:-2], axis=1)))

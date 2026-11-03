"""From shapes or landmarks to muscle activations, with non-negative least squares plus an effort penalty: many muscles can make one movement, so the solver prefers the least total activation."""
import numpy as np

# dlib-style indices of the tracker's landmarks, and the rig bone end each stands for, on the subject's own sides (image left is the subject's right).
LANDMARKS = {
    17: ("brow.T.R", "head"), 18: ("brow.T.R.001", "head"), 19: ("brow.T.R.002", "head"), 20: ("brow.T.R.003", "head"),
    23: ("brow.T.L.003", "head"), 24: ("brow.T.L.002", "head"), 25: ("brow.T.L.001", "head"), 26: ("brow.T.L", "head"),
    36: ("lid.T.R.003", "tail"), 37: ("lid.T.R.002", "head"), 38: ("lid.T.R.001", "head"), 39: ("lid.T.R", "head"), 40: ("lid.B.R.002", "head"), 41: ("lid.B.R.001", "head"),
    42: ("lid.T.L", "head"), 43: ("lid.T.L.001", "head"), 44: ("lid.T.L.002", "head"), 45: ("lid.T.L.003", "tail"), 46: ("lid.B.L.001", "head"), 47: ("lid.B.L.002", "head"),
    48: ("lip.T.R.001", "tail"), 49: ("lip.T.R.001", "head"), 51: ("lip.T.L", "head"), 53: ("lip.T.L.001", "head"), 54: ("lip.T.L.001", "tail"),
    55: ("lip.B.L.001", "head"), 57: ("lip.B.L", "head"), 59: ("lip.B.R.001", "head"), 8: ("chin", "head"),
    31: ("nose.R.001", "head"), 35: ("nose.L.001", "head"),
}
STABLE = [36, 39, 42, 45, 27, 28]  # corners of the eyes and the nose's bridge: what the head moves, and a face barely does


def effort_nnls(A, b, effort=0.0, upper=1.0, start=None, iterations=60):
    """min |Ax-b|^2 + effort*sum(x), 0 <= x <= upper, by coordinate descent."""
    n = A.shape[1]
    x = np.zeros(n) if start is None else np.clip(start, 0, upper).copy()
    AtA = A.T @ A
    Atb = A.T @ b
    diag = np.maximum(np.diag(AtA), 1e-12)
    for _ in range(iterations):
        changed = 0.0
        for j in range(n):
            g = Atb[j] - AtA[j] @ x + AtA[j, j] * x[j] - effort / 2
            new = min(max(g / diag[j], 0.0), upper)
            changed = max(changed, abs(new - x[j]))
            x[j] = new
        if changed < 1e-5:
            break
    return x


def shape_fit(fields, shape, effort=1e-5):
    """Activations reproducing one shape from fields (n_muscles, n_points, 3), and the relative residual."""
    A = fields.reshape(fields.shape[0], -1).T
    b = shape.ravel()
    x = effort_nnls(A, b, effort=effort, upper=1.5)
    res = np.linalg.norm(A @ x - b) / max(np.linalg.norm(b), 1e-12)
    return x, float(res)


def align(points, rest, stable=STABLE):
    """Removes head motion: the similarity (scale, rotation, shift) that best maps a frame's stable points onto the rest ones. points and rest are (n, 2)."""
    p, q = points[stable], rest[stable]
    pc, qc = p.mean(axis=0), q.mean(axis=0)
    a = (p - pc)
    b = (q - qc)
    H = a.T @ b
    U, S, Vt = np.linalg.svd(H)
    R = Vt.T @ np.diag([1, np.sign(np.linalg.det(Vt.T @ U.T))]) @ U.T
    s = S.sum() / max((a ** 2).sum(), 1e-12)
    return s * (points - pc) @ R.T + qc


def track_matrix(fields, vertex_of, ids):
    """Frontal-plane field at the tracked vertices: rows are x and z of each landmark."""
    pos = {v: i for i, v in enumerate(ids)}
    rows = []
    for dlib, vid in vertex_of.items():
        i = pos[vid]
        rows.append(fields[:, i, 0])
        rows.append(fields[:, i, 2])
    return np.array(rows).T.T


def solve_track(landmarks, rest_window, vertex_of, fields, ids, ipd_m, effort, jaw_open=None, jaw_lower=None, smooth_frames=2):
    """Activations per frame from tracked 2D landmarks. landmarks is (frames, n, 2) in pixels; y grows down."""
    rest = np.median(landmarks[rest_window[0]:rest_window[1]], axis=0)
    px_per_m = np.linalg.norm(rest[39] - rest[42] + (rest[36] - rest[45])) / 2 / (ipd_m * 2)
    A = track_matrix(fields, vertex_of, ids)
    frames = landmarks.shape[0]
    out = np.zeros((frames, fields.shape[0]))
    residual = np.zeros(frames)
    keys = list(vertex_of.keys())
    x = None
    for t in range(frames):
        p = align(landmarks[t], rest)
        d = (p - rest) / px_per_m
        b = np.zeros(2 * len(keys))
        for k, dlib in enumerate(keys):
            b[2 * k], b[2 * k + 1] = d[dlib, 0], -d[dlib, 1]
        if jaw_open is not None:
            b = b - jaw_open[t] * jaw_lower
        x = effort_nnls(A, b, effort=effort, start=x, iterations=25)
        out[t] = x
        residual[t] = np.linalg.norm(A @ x - b) / max(np.linalg.norm(b), 1e-9)
    if smooth_frames:
        kernel = np.exp(-0.5 * (np.arange(-3 * smooth_frames, 3 * smooth_frames + 1) / smooth_frames) ** 2)
        kernel /= kernel.sum()
        out = np.column_stack([np.convolve(np.pad(out[:, j], len(kernel) // 2, mode="edge"), kernel, mode="valid") for j in range(out.shape[1])])
    return out, residual

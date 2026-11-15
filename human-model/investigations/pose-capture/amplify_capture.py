"""Motion gain: the captured motion with more (or less) travel, before it drives a body (Rafael, 2026-11-14).

    human-model/hm.sh --ref python human-model/investigations/pose-capture/amplify_capture.py IN.npz OUT.npz \
        [--gain G] [--hips G] [--trunk G] [--head G] [--arms G] [--legs G] [--noise G] [--base-hz F] [--noise-hz F]

IN.npz is capture_pose.py's (one camera) or two_cameras.py's (two); OUT.npz has the same keys, so drive_capture.py reads it
as it is. Next to OUT.npz goes OUT.json: the gains and, per part, how much motion and noise the capture had and has now.

The body is cut into parts, each a rotation relative to its parent: pelvis (to the world), chest (to the pelvis), head (to
the chest), upper arm and forearm, thigh and shin. A part's rotation over time is split in three bands by two gaussians in
time, each set by the frequency it halves (sigma = 0.187 / F seconds):
- base (under --base-hz, default 0.3 Hz): the held pose, travel and turns; kept as captured;
- motion (between the two): what the body does on purpose, the sway of a dance; multiplied by the part's gain;
- noise (over --noise-hz, default 6 Hz): MediaPipe's tremor; multiplied by --noise (default 1, as captured).
The bands overlap a little: a 1.5 Hz sway is 96% motion and 4% noise, a 0.5 Hz one 85% motion and 15% base.
Noise slower than --noise-hz can't be told from motion and takes the part's gain.
The multiplying is on angles (the motion band's rotation from the base, scaled about its own axis), never on positions, so
bones keep their lengths. With two cameras, the hips' path on the floor (points_m) is split the same way and takes the hips
gain. Each part's gain is --gain times its own (--hips, --trunk, --head, --arms, --legs; all 1 by default) and must be from
0 to 3 (Rafael: past 3 the take is lost). Every gain at 1 returns the capture unchanged.

Planted feet (Rafael, 2026-11-15; with foot_contacts.py's `contact` in IN.npz, two cameras; --no-plant off): the hips' gain
moved every point with the hips, planted feet too (a planted foot slid 188 mm median at hips gain 3, against 24 as captured,
and drive_capture.py's IK then dropped the hips up to 174 mm). Now a foot on the floor keeps its captured place (ankle, heel,
toe; eased in and out over a few frames around each contact) and the leg reaches it: the knee by two bones of the captured
lengths, in the plane the amplified knee bends in. Where the amplified hips would put a planted foot out of the leg's reach,
the hips' path takes less gain in those frames (smoothed in time), never less than 1 (as captured). OUT.json says how often.

Gain can only scale what was captured: a part MediaPipe barely saw (the pelvis's tilt, two points under shorts) stays barely
moving, and OUT.json says so.
"""
import json, os, sys
import numpy as np
from scipy.spatial.transform import Rotation

MAX_GAIN = 3.0
HALF = np.sqrt(np.log(2) / 2) / np.pi  # a gaussian of sigma HALF / F seconds halves frequency F
L = dict(nose=0, ear_l=7, ear_r=8, sh_l=11, sh_r=12, el_l=13, el_r=14, wr_l=15, wr_r=16, hip_l=23, hip_r=24,
         knee_l=25, knee_r=26, ank_l=27, ank_r=28)
HEAD_POINTS = list(range(0, 11))
# name, parent, region, how its frame is built, origin (landmark index or "midhip"/"midsh"), landmarks it carries
PARTS = [
    ("pelvis", None, "hips", "pelvis", "midhip", [23, 24]),
    ("chest", "pelvis", "trunk", "chest", "midhip", [11, 12]),
    ("head", "chest", "head", "head", "midsh", HEAD_POINTS),
    ("upperarm_l", "chest", "arms", (11, 13), 11, [13]),
    ("forearm_l", "upperarm_l", "arms", (13, 15), 13, [15, 17, 19, 21]),
    ("upperarm_r", "chest", "arms", (12, 14), 12, [14]),
    ("forearm_r", "upperarm_r", "arms", (14, 16), 14, [16, 18, 20, 22]),
    ("thigh_l", "pelvis", "legs", (23, 25), 23, [25]),
    ("shin_l", "thigh_l", "legs", (25, 27), 25, [27, 29, 31]),
    ("thigh_r", "pelvis", "legs", (24, 26), 24, [26]),
    ("shin_r", "thigh_r", "legs", (26, 28), 26, [28, 30, 32]),
]
REGIONS = ["hips", "trunk", "head", "arms", "legs"]


def smooth(x, sigma):
    """Gaussian in time along axis 0, edges held."""
    if sigma <= 0:
        return x.copy()
    r = int(np.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.concatenate([np.repeat(x[:1], r, 0), x, np.repeat(x[-1:], r, 0)])
    return np.stack([np.tensordot(k, pad[i:i + 2 * r + 1], axes=(0, 0)) for i in range(len(x))])


def fill_gaps(x):
    """Frames with no capture take the line between their neighbours (as drive_capture.py does)."""
    x = x.copy()
    t = np.arange(len(x))
    flat = x.reshape(len(x), -1)
    for k in range(flat.shape[1]):
        ok = np.isfinite(flat[:, k])
        if ok.any() and not ok.all():
            flat[:, k] = np.interp(t, t[ok], flat[ok, k])
    return flat.reshape(x.shape)


def unit(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def frame(x, up):
    """Rotation matrices (T, 3, 3) whose columns are x, then up made square to x, then their cross."""
    x = unit(x)
    z = unit(up - np.sum(up * x, -1, keepdims=True) * x)
    return np.stack([x, np.cross(z, x), z], -1)


def swing(a, b):
    """Shortest rotations (T, 3, 3) taking unit vectors a onto b."""
    axis = np.cross(a, b)
    s = np.linalg.norm(axis, axis=-1)
    c = np.sum(a * b, -1)
    ang = np.arctan2(s, c)
    axis = np.where(s[:, None] > 1e-9, axis / np.maximum(s, 1e-12)[:, None], [1.0, 0, 0])
    return Rotation.from_rotvec(axis * ang[:, None]).as_matrix()


def origin_of(X, o):
    if o == "midhip":
        return (X[:, 23] + X[:, 24]) / 2
    if o == "midsh":
        return (X[:, 11] + X[:, 12]) / 2
    return X[:, o]


def world_frames(X):
    """Each part's frame in the world, per frame. Limbs: the parent's frame swung so the reference axis meets the bone; the
    reference is the bone's median direction in its parent, so the limb's rest is where it mostly was."""
    F, ref = {}, {}
    for name, parent, _, how, _, _ in PARTS:
        if how == "pelvis":
            F[name] = frame(X[:, 23] - X[:, 24], origin_of(X, "midsh") - origin_of(X, "midhip"))
        elif how == "chest":
            F[name] = frame(X[:, 11] - X[:, 12], origin_of(X, "midsh") - origin_of(X, "midhip"))
        elif how == "head":
            mid_ear = (X[:, 7] + X[:, 8]) / 2
            F[name] = frame(X[:, 7] - X[:, 8], np.cross(X[:, 0] - mid_ear, X[:, 7] - X[:, 8]))
        else:
            a, b = how
            d_local = unit(np.einsum("tji,tj->ti", F[parent], X[:, b] - X[:, a]))
            r = unit(np.median(d_local, 0))
            ref[name] = r
            F[name] = F[parent] @ swing(np.repeat(r[None], len(X), 0), d_local)
    return F


def split_rotations(R, base_hz, noise_hz, fps):
    """Rotations (T, 3, 3) -> base, motion (rotvec from base), noise (rotvec after motion), each per frame."""
    q = Rotation.from_matrix(R).as_quat()
    for t in range(1, len(q)):  # one hemisphere, so averaging quaternions is averaging rotations
        if np.dot(q[t], q[t - 1]) < 0:
            q[t] = -q[t]
    base = Rotation.from_quat(unit(smooth(q, HALF / base_hz * fps)))
    mid = Rotation.from_quat(unit(smooth(q, HALF / noise_hz * fps)))
    raw = Rotation.from_quat(q)
    return base, (base.inv() * mid).as_rotvec(), (mid.inv() * raw).as_rotvec()


def split_points(p, base_hz, noise_hz, fps):
    base = smooth(p, HALF / base_hz * fps)
    mid = smooth(p, HALF / noise_hz * fps)
    return base, mid - base, p - mid


def deg_rms(rv):
    return float(np.degrees(np.sqrt(np.mean(np.sum(rv ** 2, -1)))))


def amplify(X, gains, noise_gain=1.0, base_hz=0.3, noise_hz=6.0, fps=30.0, hips_path=None):
    """X: (T, 33, 3) landmarks, NaN-free. Returns the new landmarks, the new hips path (or None) and a report."""
    F = world_frames(X)
    report = {}
    newF = {}
    for name, parent, region, _, _, _ in PARTS:
        g = gains[region]
        local = F[name] if parent is None else np.einsum("tji,tjk->tik", F[parent], F[name])
        base, motion, noise = split_rotations(local, base_hz, noise_hz, fps)
        new_local = (base * Rotation.from_rotvec(g * motion) * Rotation.from_rotvec(noise_gain * noise)).as_matrix()
        newF[name] = new_local if parent is None else newF[parent] @ new_local
        report[name] = {"region": region, "gain": g, "motion_deg_rms": deg_rms(motion),
                        # about the part's own axes; for pelvis, chest and head: x tilt (forward/back), y roll (side), z turn
                        "motion_deg_rms_by_axis": [float(v) for v in np.degrees(np.sqrt(np.mean(motion ** 2, 0)))],
                        "motion_deg_rms_after": deg_rms(g * motion), "noise_deg_rms": deg_rms(noise),
                        "noise_deg_rms_after": deg_rms(noise_gain * noise)}
    Y = X.copy()
    for name, parent, _, _, o, carried in PARTS:
        # a part's own points ride on its frame about its origin, which its parent has already moved
        o_old, o_new = origin_of(X, o), origin_of(Y, o)
        local_pts = np.einsum("tji,tpj->tpi", F[name], X[:, carried] - o_old[:, None])
        Y[:, carried] = o_new[:, None] + np.einsum("tij,tpj->tpi", newF[name], local_pts)
    new_path = None
    if hips_path is not None:
        g = gains["hips"]
        base, motion, noise = split_points(hips_path, base_hz, noise_hz, fps)
        new_path = base + g * motion + noise_gain * noise
        mm = lambda v: float(1000 * np.sqrt(np.mean(np.sum(v ** 2, -1))))
        report["hips_path"] = {"region": "hips", "gain": g, "motion_mm_rms": mm(motion), "motion_mm_rms_after": mm(g * motion),
                               "noise_mm_rms": mm(noise), "noise_mm_rms_after": mm(noise_gain * noise)}
        report["_path_parts"] = (base, motion, noise_gain * noise)
    return Y, new_path, report


FEET = {0: (23, 25, 27, 29, 31), 1: (24, 26, 28, 30, 32)}  # left, right: hip, knee, ankle, heel, toe
REACH = 0.995  # a planted leg reaches at most this share of its two bones' length


def plant_feet(P_old, rel, path_parts, g, contact, fps, ease_frames=2.0):
    """P_old: (T, 33, 3) captured points; rel: the amplified body about its mid hips; path_parts: base, motion, noise of the hips'
    path (noise already scaled); g: the hips gain. Returns the points with planted feet held, the hips gain used per frame and a
    report."""
    base, motion, noise = path_parts
    T = len(P_old)
    on = contact.any(axis=2).astype(float)  # (T, 2) a foot on the floor by any of its points
    w = np.maximum(on, np.clip(smooth(on, ease_frames) * 2, 0, 1))  # 1 on the floor, eased to 0 around it
    lens = {s: (np.linalg.norm(P_old[:, k[1]] - P_old[:, k[0]], axis=1), np.linalg.norm(P_old[:, k[2]] - P_old[:, k[1]], axis=1))
            for s, k in FEET.items()}

    def points_at(k):
        return (base + k[:, None] * motion + noise)[:, None] + rel

    def reachable(P, s):
        hip, _, ank = FEET[s][:3]
        A = P[:, ank] + w[:, s, None] * (P_old[:, ank] - P[:, ank])
        return np.linalg.norm(A - P[:, hip], axis=1) <= REACH * (lens[s][0] + lens[s][1])

    lo = np.full(T, min(1.0, g))
    k = np.full(T, float(g))
    if g > 1.0:
        ok = np.ones(T, bool)
        P = points_at(k)
        for s in FEET:
            ok &= reachable(P, s) | (w[:, s] == 0)
        hi = k.copy()
        bad = ~ok
        lo_b, hi_b = lo.copy(), hi.copy()
        for _ in range(20):  # bisection, per frame, on the frames out of reach
            mid = 0.5 * (lo_b + hi_b)
            Pm = points_at(np.where(bad, mid, k))
            good = np.ones(T, bool)
            for s in FEET:
                good &= reachable(Pm, s) | (w[:, s] == 0)
            lo_b = np.where(bad & good, mid, lo_b)
            hi_b = np.where(bad & ~good, mid, hi_b)
        k = np.where(bad, lo_b, k)
        # smoothed in time without rising past what each frame allows much: eroded first, then smoothed
        r = int(np.ceil(3 * ease_frames))
        er = np.array([k[max(0, t - r): t + r + 1].min() for t in range(T)])
        k = np.minimum(smooth(er, ease_frames), float(g))
        k = np.maximum(k, lo)
    P = points_at(k)
    unreachable = 0
    for s, (hip, knee, ank, heel, toe) in FEET.items():
        sel = w[:, s] > 0
        for i in (ank, heel, toe):
            P[sel, i] = P[sel, i] + w[sel, s, None] * (P_old[sel, i] - P[sel, i])
        # the knee by two bones: hip H, ankle A, in the plane of the amplified knee
        H, A, Kn = P[sel, hip], P[sel, ank], P[sel, knee]
        l1, l2 = lens[s][0][sel], lens[s][1][sel]
        d_vec = A - H
        d = np.linalg.norm(d_vec, axis=1)
        far = d > (l1 + l2) * 0.9999
        unreachable += int(far.sum())
        d_use = np.minimum(d, (l1 + l2) * 0.9999)
        u = d_vec / np.maximum(d, 1e-9)[:, None]
        A = np.where(far[:, None], H + u * d_use[:, None], A)
        a = (l1 ** 2 - l2 ** 2 + d_use ** 2) / (2 * d_use)
        hgt = np.sqrt(np.maximum(l1 ** 2 - a ** 2, 0))
        pole = (Kn - H) - np.sum((Kn - H) * u, 1, keepdims=True) * u
        pole = pole / np.maximum(np.linalg.norm(pole, axis=1, keepdims=True), 1e-9)
        P[sel, knee] = H + a[:, None] * u + hgt[:, None] * pole
        shift = A - P[sel, ank]
        for i in (ank, heel, toe):
            P[sel, i] += shift
    slide = {}
    for s, name in ((0, "left"), (1, "right")):
        ank = FEET[s][2]
        c = on[:, s] > 0
        slide[name] = float(1000 * np.median(np.linalg.norm(P[c, ank] - P_old[c, ank], axis=1))) if c.any() else 0.0
    rep = {"frames_hips_gain_lowered": int((k < g - 1e-6).sum()), "hips_gain_min": float(k.min()),
           "frames_foot_out_of_reach_at_gain_1": unreachable,
           "planted_ankle_off_capture_mm_median": slide}
    return P, k, rep


def parse(argv):
    opts = {"--gain": 1.0, "--noise": 1.0, "--base-hz": 0.3, "--noise-hz": 6.0, **{f"--{r}": 1.0 for r in REGIONS}}
    pos, i = [], 0
    opts["--no-plant"] = False
    while i < len(argv):
        if argv[i] == "--no-plant":
            opts["--no-plant"] = True
            i += 1
        elif argv[i] in opts:
            opts[argv[i]] = float(argv[i + 1])
            i += 2
        else:
            pos.append(argv[i])
            i += 1
    if len(pos) != 2:
        sys.exit(__doc__)
    gains = {r: opts["--gain"] * opts[f"--{r}"] for r in REGIONS}
    bad = {r: g for r, g in gains.items() if not 0 <= g <= MAX_GAIN}
    if bad:
        sys.exit(f"gains must be from 0 to {MAX_GAIN} (--gain times the part's): {bad}")
    if not 0 <= opts["--noise"] <= MAX_GAIN:
        sys.exit(f"--noise must be from 0 to {MAX_GAIN}")
    if not 0 < opts["--base-hz"] < opts["--noise-hz"]:
        sys.exit("need 0 < --base-hz < --noise-hz")
    return pos, gains, opts


def main():
    (src, out), gains, opts = parse(sys.argv[1:])
    d = np.load(src)
    data = {k: d[k] for k in d.files}
    fps = float(d["fps"])
    world = d["world"].astype(float)
    missing = ~np.isfinite(world)
    X = fill_gaps(world)
    hips = None
    if "points_m" in d.files:  # two cameras: where the hips really went, metres, Blender axes
        P = fill_gaps(d["points_m"].astype(float))
        hips = (P[:, 23] + P[:, 24]) / 2
    Y, new_hips, report = amplify(X, gains, opts["--noise"], opts["--base-hz"], opts["--noise-hz"], fps, hips)
    parts = report.pop("_path_parts", None)
    Y = Y - (Y[:, 23:24] + Y[:, 24:25]) / 2  # MediaPipe's world has its origin between the hips
    if new_hips is not None:
        # world is (P - mid hips) mapped (x, y, z) -> (x, -z, y), as two_cameras.py writes it
        rel = np.stack([Y[..., 0], Y[..., 2], -Y[..., 1]], -1)
        P_new = new_hips[:, None] + rel
        if "contact" in d.files and not opts["--no-plant"]:
            P_new, k, report["planted_feet"] = plant_feet(P, rel, parts, gains["hips"], d["contact"], fps)
            report["planted_feet"]["hips_gain_per_frame"] = [round(float(v), 3) for v in k]
            mid = (P_new[:, 23] + P_new[:, 24]) / 2
            R_ = P_new - mid[:, None]
            Y = np.stack([R_[..., 0], -R_[..., 2], R_[..., 1]], -1)
        P_new[~np.isfinite(d["points_m"])] = np.nan
        data["points_m"] = P_new
    Y[missing] = np.nan
    data["world"] = Y
    np.savez_compressed(out, **data)
    summary = {"source": src, "gains": gains, "noise_gain": opts["--noise"], "base_hz": opts["--base-hz"],
               "noise_hz": opts["--noise-hz"], "fps": fps, "frames": len(X), "parts": report}
    json.dump(summary, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
    if "planted_feet" in report:
        pf = {k_: v for k_, v in report["planted_feet"].items() if k_ != "hips_gain_per_frame"}
        print("planted feet:", json.dumps(pf))
    for name, r in report.items():
        if name == "planted_feet":
            continue
        unit_ = "mm" if name == "hips_path" else "deg"
        k = f"motion_{unit_}_rms"
        print(f"{name:12s} gain {r['gain']:.2f}  motion {r[k]:6.1f} -> {r[k + '_after']:6.1f} {unit_} rms   "
              f"noise {r[f'noise_{unit_}_rms']:5.2f} {unit_} rms"
              + (f"   by axis x/y/z {'/'.join(f'{v:.1f}' for v in r['motion_deg_rms_by_axis'])}" if unit_ == "deg" else ""))


if __name__ == "__main__":
    main()

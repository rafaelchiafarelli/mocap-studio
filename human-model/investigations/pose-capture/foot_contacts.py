"""Floor and foot contacts of a two-camera capture, from one frame Rafael marks as a foot on the floor (Rafael, 2026-11-14).

    human-model/hm.sh --ref python human-model/investigations/pose-capture/foot_contacts.py IN.npz OUT.npz \
        --pe-no-chao MARK:direito|esquerdo [--videos A.mp4 B.mp4] [--contact-mm 40] [--speed 0.3]

IN.npz is two_cameras.py's (it needs points_m); its two_cameras.json, next to it, gives the offset between the videos. MARK
is a VLC snapshot (.png) of either video, found by comparing it with every frame (--videos needed), or a time in seconds of
video A. The marked foot must be flat on the floor and still at that moment; its shoe can be anything.

1. Level the floor. two_cameras.py takes "up" as the body's median ankles-to-shoulders direction, so a body leaning through the
   stretch tilts the floor. Here every frame where a heel, toe or ankle point is still is taken as standing on the floor, a
   plane is fitted through them (one height per point, since a heel sits higher than a toe in a shoe, and points that sit
   far above the plane dropped as feet held still in the air), and the whole capture is turned so the plane is level.
   Every capture measures its own floor (Rafael: each take has other conditions); the plane assumes the cameras stayed
   still and the floor is flat through the take, and the report warns when the points don't fit one plane.
2. Floor heights from the mark. Around the marked frame (+-0.1 s), each point of the marked foot gives the height it has when
   standing; the other foot takes the same, as it wears the same shoe. The marked foot's lowest point is put at z = 0.
3. Contacts. A point is on the floor in a frame when it is within --contact-mm of its standing height and slower than --speed
   m/s; runs shorter than 3 frames are dropped.

OUT.npz has IN.npz's keys with points_m levelled and world recomputed from it, plus contact (T, 2, 3) bool [left, right] x
[ankle, heel, toe], floor_heights_m (2, 3), floor_rotation (3, 3) and floor_shift_m (3). OUT.json reports the tilt found, the
mark (where it was found, how still the foot was, how far it sits from the fitted plane) and contacts per point; OUT.png
plots each point's height with its contacts, before and after levelling.
"""
import json, os, sys
import numpy as np

FEET = {"left": [27, 29, 31], "right": [28, 30, 32]}  # ankle, heel, toe (MediaPipe's foot_index)
POINTS = ["ankle", "heel", "toe"]
SIDE = {"direito": "right", "esquerdo": "left", "right": "right", "left": "left"}
MARK_WINDOW_S = 0.1
PLANE_WARN_MM = 30  # still foot points this far from one plane (std): a camera moved, or the floor isn't flat
MIN_RUN = 3


def smooth(x, sigma):
    r = int(np.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    pad = np.concatenate([np.repeat(x[:1], r, 0), x, np.repeat(x[-1:], r, 0)])
    return np.stack([np.tensordot(k, pad[i:i + 2 * r + 1], axes=(0, 0)) for i in range(len(x))])


def fill_gaps(x):
    x = x.copy()
    t = np.arange(len(x))
    flat = x.reshape(len(x), -1)
    for k in range(flat.shape[1]):
        ok = np.isfinite(flat[:, k])
        if ok.any() and not ok.all():
            flat[:, k] = np.interp(t, t[ok], flat[ok, k])
    return flat.reshape(x.shape)


def speeds(P, fps):
    """Speed of every point (T, 33), m/s, on positions smoothed by 1 frame so tremor doesn't read as motion."""
    return np.linalg.norm(np.gradient(smooth(P, 1.0), axis=0), axis=-1) * fps


def fit_floor(P, v, speed):
    """Plane z = a x + b y + c_i through still foot points, one c per point; points far above it dropped, three rounds.
    Returns (a, b), the residual std, and how many samples were kept."""
    idx = FEET["left"] + FEET["right"]
    keep = {i: v[:, i] < speed for i in idx}
    for _ in range(4):
        rows, z, which = [], [], []
        for j, i in enumerate(idx):
            t = np.where(keep[i])[0]
            for tt in t:
                rows.append([P[tt, i, 0], P[tt, i, 1]] + [1.0 if k == j else 0.0 for k in range(len(idx))])
                z.append(P[tt, i, 2])
                which.append((i, tt))
        M, z = np.array(rows), np.array(z)
        coef, *_ = np.linalg.lstsq(M, z, rcond=None)
        res = z - M @ coef
        mad = 1.4826 * np.median(np.abs(res - np.median(res)))
        for (i, tt), r in zip(which, res):
            if r > 3 * mad:  # held still above the floor (a foot lifted and paused), not standing
                keep[i][tt] = False
    return coef[:2], float(np.std(res)), len(z)


def level_rotation(a, b):
    """Rotation turning the plane z = a x + b y + c level: its normal onto +z, by the shortest turn."""
    n = np.array([-a, -b, 1.0])
    n /= np.linalg.norm(n)
    axis = np.cross(n, [0, 0, 1.0])
    s, c = np.linalg.norm(axis), n[2]
    if s < 1e-12:
        return np.eye(3)
    k = axis / s
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K


def find_snapshot(png, videos):
    """(video index, time in that video, match error, error of the best frame of the other video)."""
    import cv2
    snap = cv2.imread(png, cv2.IMREAD_GRAYSCALE)
    small = lambda g: cv2.resize(g, (96, 54), interpolation=cv2.INTER_AREA).astype(float)
    s = small(snap)
    best = []
    for vi, video in enumerate(videos):
        cap = cv2.VideoCapture(video)
        cap.set(cv2.CAP_PROP_ORIENTATION_AUTO, 0)  # VLC's snapshot is the frame as stored, before the rotation flag
        e_best, t_best = np.inf, None
        while True:
            ok, f = cap.read()
            if not ok:
                break
            g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            if (g.shape[0] > g.shape[1]) != (snap.shape[0] > snap.shape[1]):
                g = cv2.rotate(g, cv2.ROTATE_90_COUNTERCLOCKWISE)
            e = float(np.mean((small(g) - s) ** 2))
            if e < e_best:
                e_best, t_best = e, cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        best.append((e_best, t_best))
    vi = int(np.argmin([e for e, _ in best]))
    other = min(e for j, (e, _) in enumerate(best) if j != vi) if len(best) > 1 else None
    return vi, best[vi][1], best[vi][0], other


def runs_at_least(mask, n):
    out = mask.copy()
    t = 0
    while t < len(mask):
        if mask[t]:
            u = t
            while u < len(mask) and mask[u]:
                u += 1
            if u - t < n:
                out[t:u] = False
            t = u
        else:
            t += 1
    return out


def contacts(P, v, heights, contact_m, speed):
    C = np.zeros((len(P), 2, 3), bool)
    for f, side in enumerate(("left", "right")):
        for p, i in enumerate(FEET[side]):
            on = (P[:, i, 2] - heights[f, p] < contact_m) & (v[:, i] < speed)
            C[:, f, p] = runs_at_least(on, MIN_RUN)
    return C


def plot(path, t, P_before, P_after, C, heights):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(2, 3, figsize=(15, 6.5), sharex=True, sharey=True)
    colours = {"before": "#9a9a9a", "after": "#1f5fa8", "contact": "#e07b22"}
    for f, side in enumerate(("left", "right")):
        for p, i in enumerate(FEET[side]):
            ax = axes[f, p]
            ax.plot(t, 1000 * P_before[:, i, 2], color=colours["before"], lw=1, label="antes de nivelar")
            ax.plot(t, 1000 * P_after[:, i, 2], color=colours["after"], lw=1.4, label="nivelado")
            on = C[:, f, p]
            ax.scatter(t[on], 1000 * P_after[on, i, 2], s=6, color=colours["contact"], zorder=3, label="no chão")
            ax.axhline(1000 * heights[f, p], color=colours["contact"], lw=0.8, ls="--")
            ax.set_title(f"{'esquerdo' if side == 'left' else 'direito'} · "
                         f"{dict(ankle='tornozelo', heel='calcanhar', toe='ponta')[POINTS[p]]}", fontsize=10)
            ax.grid(alpha=0.25)
            if p == 0:
                ax.set_ylabel("altura (mm)")
            if f == 1:
                ax.set_xlabel("tempo no vídeo A (s)")
    axes[0, 0].legend(fontsize=8, loc="upper left", frameon=False)
    fig.suptitle("Altura de cada ponto do pé; tracejado = altura de apoio tirada do quadro marcado", fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


def parse(argv):
    opts = {"--contact-mm": 40.0, "--speed": 0.3}
    mark, videos, pos, i = None, None, [], 0
    while i < len(argv):
        a = argv[i]
        if a in opts:
            opts[a] = float(argv[i + 1]); i += 2
        elif a == "--pe-no-chao":
            mark = argv[i + 1]; i += 2
        elif a == "--videos":
            videos = argv[i + 1:i + 3]; i += 3
        else:
            pos.append(a); i += 1
    if len(pos) != 2 or not mark or ":" not in mark:
        sys.exit(__doc__)
    where, side = mark.rsplit(":", 1)
    if side not in SIDE:
        sys.exit(f"foot must be one of {sorted(SIDE)}")
    if where.lower().endswith(".png") and not videos:
        sys.exit("a snapshot needs --videos A.mp4 B.mp4")
    return pos, where, SIDE[side], videos, opts


def main():
    (src, out), where, side, videos, opts = parse(sys.argv[1:])
    d = np.load(src)
    if "points_m" not in d.files:
        sys.exit("needs a two-camera capture (points_m): with one camera the floor isn't measured")
    data = {k: d[k] for k in d.files}
    tc = json.load(open(os.path.join(os.path.dirname(src), "two_cameras.json")))
    fps, ta = float(d["fps"]), d["times"].astype(float)
    raw = d["points_m"].astype(float)
    P = fill_gaps(raw)
    report = {"source": src, "contact_mm": opts["--contact-mm"], "speed_m_s": opts["--speed"]}

    # the mark, as a time in video A (two_cameras.py: time in B = time in A + video_offset_s)
    if where.lower().endswith(".png"):
        vi, tv, err, other = find_snapshot(where, videos)
        t_mark = tv - tc["video_offset_s"] * vi
        report["mark"] = {"snapshot": where, "video": videos[vi], "time_in_video_s": tv, "match_error": err,
                          "other_video_best_error": other}
        if other is not None and err > 0.2 * other:
            sys.exit(f"snapshot not found clearly in either video: {report['mark']}")
    else:
        t_mark = float(where)
        report["mark"] = {"time_in_video_a_s": t_mark}
    if not ta[0] <= t_mark <= ta[-1]:
        sys.exit(f"the mark ({t_mark:.3f} s in A) is outside this capture ({ta[0]:.2f}-{ta[-1]:.2f} s)")
    k = int(np.argmin(np.abs(ta - t_mark)))
    report["mark"].update(foot=side, time_in_video_a_s=t_mark, frame=k)

    # 1. level
    v = speeds(P, fps)
    (a, b), resid, n = fit_floor(P, v, opts["--speed"])
    R = level_rotation(a, b)
    L = P @ R.T
    report["floor_fit"] = {"slope_mm_per_m_x": 1000 * a, "slope_mm_per_m_y": 1000 * b,
                           "tilt_deg": float(np.degrees(np.arctan(np.hypot(a, b)))), "residual_mm_std": 1000 * resid,
                           "samples": n}
    if 1000 * resid > PLANE_WARN_MM:
        report["floor_fit"]["warning"] = (f"still foot points sit {1000 * resid:.0f} mm (std) from one plane: did a camera move "
                                          "during the take, or is the floor uneven?")
        print("WARNING:", report["floor_fit"]["warning"])

    # 2. heights from the mark
    w = slice(max(0, k - int(round(MARK_WINDOW_S * fps))), k + int(round(MARK_WINDOW_S * fps)) + 1)
    f_mark = 0 if side == "left" else 1
    own = np.array([np.mean(L[w, i, 2]) for i in FEET[side]])
    shift = np.array([0.0, 0.0, -own.min()])
    L = L + shift
    heights = np.tile(own + shift[2], (2, 1))
    report["mark"]["speed_m_s"] = {POINTS[p]: float(v[k, i]) for p, i in enumerate(FEET[side])}
    report["mark"]["still"] = bool(max(v[k, i] for i in FEET[side]) < opts["--speed"])
    report["mark"]["moving_foot_speed_m_s"] = float(max(v[k, i] for i in FEET["left" if side == "right" else "right"]))
    report["floor_heights_mm"] = {POINTS[p]: 1000 * float(heights[0, p]) for p in range(3)}

    # 3. contacts, and how far points go under their standing height
    C = contacts(L, v, heights, opts["--contact-mm"] / 1000, opts["--speed"])
    per = {}
    for f, s in enumerate(("left", "right")):
        for p, i in enumerate(FEET[s]):
            below = heights[f, p] - L[:, i, 2]
            per[f"{s}_{POINTS[p]}"] = {"frames_on_floor": int(C[:, f, p].sum()), "share": float(C[:, f, p].mean()),
                                       "deepest_under_mm": float(1000 * below.max()),
                                       "frames_over_contact_mm_under": int((below > opts["--contact-mm"] / 1000).sum())}
    report["contacts"] = per
    report["frames_no_foot_on_floor"] = int((~C.any(axis=(1, 2))).sum())

    Lout = L.copy()
    Lout[~np.isfinite(raw)] = np.nan
    world = Lout - (Lout[:, 23:24] + Lout[:, 24:25]) / 2
    data["points_m"] = Lout
    data["world"] = np.stack([world[..., 0], -world[..., 2], world[..., 1]], -1)  # as two_cameras.py writes it
    data.update(contact=C, floor_heights_m=heights, floor_rotation=R, floor_shift_m=shift)
    np.savez_compressed(out, **data)
    base = os.path.splitext(out)[0]
    json.dump(report, open(base + ".json", "w"), indent=1)
    plot(base + ".png", ta, P - np.array([0, 0, own.min()]), L, C, heights)
    print(json.dumps({k: report[k] for k in ("mark", "floor_fit", "floor_heights_mm", "frames_no_foot_on_floor")}, indent=1))
    for name, r in per.items():
        print(f"{name:13s} on floor {r['frames_on_floor']:4d} ({100 * r['share']:3.0f}%)  deepest under {r['deepest_under_mm']:5.0f} mm")


if __name__ == "__main__":
    main()

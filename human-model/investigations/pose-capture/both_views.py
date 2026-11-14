"""Lists the stretches where the body, shoulders to feet, is whole in both cameras, after capture_pose.py and the sync.

    python both_views.py A.npz B.npz OFFSET_S [MIN_SECONDS] [--head]

OFFSET_S is two_cameras.json's `video_offset_s` (B's video time = A's + offset). A frame counts when, in both views,
every landmark from the shoulders down (with --head, the whole body) has visibility over `VIS` (low, so a limb
hidden behind the body still counts) and lies inside the
picture by `MARGIN` of its size. Gaps up to `GAP_S` are bridged. Prints the stretches in A's video time, longest first,
for two_cameras.py's --from and --to.
"""
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import two_cameras as tc  # noqa: E402

VIS = 0.0  # visibility not required: a limb hidden behind the body (the far arm in a side view) is still in the picture,
# and the skeleton fit already weighs it by visibility; 0.3 left 24% of frames, 0.0 left 70% (clip 2026-11-14)
MARGIN = 0.01
GAP_S = 0.25


def whole(lm, w, h, idx):
    x, y, v = lm[:, idx, 0], lm[:, idx, 1], lm[:, idx, -1]
    inside = (x > MARGIN * w) & (x < (1 - MARGIN) * w) & (y > MARGIN * h) & (y < (1 - MARGIN) * h)
    return (np.nan_to_num(v) > VIS).all(1) & inside.all(1)


def stretches(ok, times, gap_s=GAP_S):
    out, start, last = [], None, None
    for t, k in zip(times, ok):
        if k:
            if start is None or t - last > gap_s:
                if start is not None:
                    out.append((start, last))
                start = t
            last = t
    if start is not None:
        out.append((start, last))
    return out


def main(a_npz, b_npz, offset, min_s=1.0, head=False):
    A, B = np.load(a_npz), np.load(b_npz)
    idx = np.arange(0 if head else 11, 33)
    lb = B["image"]
    ok_b = whole(lb, int(B["width"]), int(B["height"]), idx).astype(float)
    ok_b_at_a = np.interp(A["times"] + offset, B["times"], ok_b, left=0, right=0) > 0.999
    ok_a = whole(A["image"], int(A["width"]), int(A["height"]), idx)
    ok = ok_a & ok_b_at_a
    found = [(s, e) for s, e in stretches(ok, A["times"]) if e - s >= min_s]
    print(f"quadros com o corpo inteiro: A {ok_a.mean()*100:.0f}%, B {ok_b.mean()*100:.0f}%, os dois {ok.mean()*100:.0f}%")
    for s, e in sorted(found, key=lambda p: p[0] - p[1]):
        print(f"  de {s:6.2f} s a {e:6.2f} s  ({e - s:4.1f} s)")
    return found


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--head"]
    if len(args) < 3:
        print(__doc__)
        sys.exit(2)
    main(args[0], args[1], float(args[2]), float(args[3]) if len(args) > 3 else 1.0, "--head" in sys.argv)

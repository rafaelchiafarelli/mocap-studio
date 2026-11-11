"""Classifies each model of a table in our own terms: silhouette, biotype, gluteus and breast, each with its confidence and the measures behind it.

    human-model/hm.sh --ref python human-model/tools/classify_body.py "G:\\...\\modelos.csv" [--sexo female|male]

The table is the one saved by tools/cut_stretches.py's page: clips named after the same model are one person, "vindo" is measured from the front,
"indo" from the back and "lado" from the side, and "descartar" and "outro" are left out. Writes classificacao.csv and classificacao.html beside the table.

Everything is measured on the body's outline as the camera sees it, clothes included, so loose clothes read as body. Widths become girths through a fit
on ANSUR II (US Army personnel). The prototypes and the confidence rules are declared by judgement and have not been checked against measured people.
"""
from __future__ import annotations

import csv
import html
import json
import math
import sys
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

import check_reference as cr
from check_reference import AN_L, AN_R, EAR_L, EAR_R, HIP_L, HIP_R, KNEE_L, KNEE_R, NOSE, SH_L, SH_R, WR_L, WR_R, cv2, mp_pose

DATA = Path(__file__).resolve().parent.parent / "data"
SAMPLE_HZ = 4.0
WORKERS = 8
EL_L, EL_R, INDEX_L, INDEX_R = 13, 14, 19, 20
VIEW_OF_DIRECTION = {"vindo": "front", "indo": "back", "lado": "side"}

# Bands along the torso, as shares of the distance from the shoulders' line to the hips' line.
SHOULDER_BAND, BUST_BAND, WAIST_BAND, HIP_BAND = (-0.05, 0.20), (0.25, 0.45), (0.55, 0.85), (0.95, 1.25)
GLUTE_TOP, GLUTE_BOTTOM = 0.90, 1.30
FRONT_MIN, SIDE_MAX = 0.50, 0.45  # shoulders' width over the torso's length that makes a frame usable as front or back, and as side
ARM_RADIUS = 0.12  # of the torso's length
JUMP = 0.05  # of the torso's length: an edge further than this from its neighbours' median is a hand, a bag or a fold of cloth
JUMP_WINDOW = 0.2  # of the torso's length: how many rows make those neighbours
STRAIGHT_LEG = 165.0  # degrees at the knee: only such frames give the body's height

# Least squares on ANSUR II, 1986 women and 4082 men (R2 in brackets): girth ratio = a + b * measured ratio.
GIRTH_FIT = {
    "female": {"waist_breadth": (0.0676, 0.9142), "waist_ellipse": (0.0232, 0.9409), "bust_ellipse": (0.1145, 0.9314)},  # R2 0.81, 0.88, 0.74; bust from breadth alone is 0.37: not used
    "male": {"waist_breadth": (0.0923, 0.8785), "waist_ellipse": (-0.0328, 1.0026), "bust_ellipse": (0.2492, 0.8636)},  # R2 0.71, 0.87, 0.57
}
# ANSUR II means: over the stature minus the ankle's height, which leaves heels out of it.
NEUTRAL = {"female": {"shoulders": 0.2878, "waist": 0.1916, "hips": 0.2261, "limb_length": 0.4997}, "male": {"shoulders": 0.3035, "waist": 0.1940, "hips": 0.2055, "limb_length": 0.4917}}
BIOTYPE_KEYS = ("shoulders", "waist", "hips", "limb_length")
BIOTYPE_NAMES = {"ectomorph": "ectomorfo", "mesomorph": "mesomorfo", "endomorph": "endomorfo"}
BIOTYPE_MAX_OTHER, BIOTYPE_MAX_OTHERS = 0.35, 0.65  # the rule of initiative body-type-selection

# The gluteus's outline, from the top of the hip bones to the top of the thigh: the width of its upper and lower quarters over the widest, where the widest falls (0 at the top, 1 at the base),
# and, seen from the side, the hip's depth over the waist's. Declared from the definitions in initiative body-type-selection; not checked against measured people.
GLUTE_PROTOTYPES = {
    "quadrado": {"upper": 0.96, "lower": 0.96, "peak": 0.5, "projection": 1.10},
    "redondo": {"upper": 0.91, "lower": 0.91, "peak": 0.5, "projection": 1.35},
    "coracao": {"upper": 0.85, "lower": 0.98, "peak": 0.8, "projection": 1.30},
    "em_v": {"upper": 0.98, "lower": 0.85, "peak": 0.2, "projection": 1.15},
}
GLUTE_SCALE = {"upper": 0.06, "lower": 0.06, "peak": 0.3, "projection": 0.15}
TORSO_CM = 48.0  # a typical torso, to read the breast's base in data/breast_shapes.json against the picture
MIN_FRAMES = 3


def ellipse(a, b):
    a, b = a / 2, b / 2
    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))


def refined(pose, bgr):
    """The person found in the whole frame, then again in a crop around them: the model's mask is 256 cells wide, so a crop gives it several times the detail across the body."""
    first = cr.find_person(pose, bgr)
    if first is None:
        return None, None
    h, w = bgr.shape[:2]
    x0, y0, x1, y1 = first.box
    mx, my = int(0.25 * (x1 - x0)) + 10, int(0.08 * (y1 - y0)) + 10
    x0, y0, x1, y1 = max(x0 - mx, 0), max(y0 - my, 0), min(x1 + mx, w), min(y1 + my, h)
    crop = bgr[y0:y1, x0:x1]
    result = pose.process(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    if result.pose_landmarks is None or result.segmentation_mask is None:
        return None, None
    ch, cw = crop.shape[:2]
    lm = np.array([[p.x * cw, p.y * ch, p.z * cw, p.visibility] for p in result.pose_landmarks.landmark])
    mask = (cv2.resize(result.segmentation_mask, (cw, ch), interpolation=cv2.INTER_LINEAR) > 0.5).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    if n < 2:
        return None, None
    return (lm, labels == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))), crop


def run_at(mask, y, x):
    """The left and right ends of the run of body through column x of row y; None if x isn't on the body or the run reaches the picture's edge."""
    if not 0 <= y < mask.shape[0] or not 0 <= x < mask.shape[1] or not mask[y, x]:
        return None
    row = mask[y]
    left, right = row[x::-1], row[x:]
    if left.all() or right.all():
        return None
    return x - int(np.argmin(left)) + 1, x + int(np.argmin(right)) - 1


def arm_points(lm, shoulder, elbow, wrist, index):
    """Shoulder, elbow, wrist and the fingertips, which lie past the index landmark, on the knuckles."""
    tip = lm[index, :2] + 0.8 * (lm[index, :2] - lm[wrist, :2])
    return [lm[shoulder, :2], lm[elbow, :2], lm[wrist, :2], tip]


def arm_x(points, y):
    """Where an arm crosses row y, or None."""
    for a, b in zip(points, points[1:]):
        if min(a[1], b[1]) <= y <= max(a[1], b[1]) and a[1] != b[1]:
            return a[0] + (y - a[1]) / (b[1] - a[1]) * (b[0] - a[0])
    return None


def angle(a, b):
    return float(np.degrees(np.arccos(np.clip(np.dot(a, b) / max(np.linalg.norm(a) * np.linalg.norm(b), 1e-6), -1, 1))))


class Frame:
    """One person's outline in one picture, and the torso's scale."""

    def __init__(self, lm, mask, crop):
        self.lm, self.mask, self.crop = lm, mask, crop
        self.sh = lm[[SH_L, SH_R], :2].mean(0)
        self.hip = lm[[HIP_L, HIP_R], :2].mean(0)
        self.torso = float(self.hip[1] - self.sh[1])
        self.ratio = float(np.linalg.norm(lm[SH_L, :2] - lm[SH_R, :2]) / self.torso) if self.torso > 0 else 0.0
        self.top = int(np.nonzero(mask.any(axis=1))[0][0])
        self.edges = None

    def y(self, share):
        return int(round(self.sh[1] + share * self.torso))

    def mid(self, y):
        t = min(max((y - self.sh[1]) / self.torso, 0.0), 1.0)
        return int(round(self.sh[0] + t * (self.hip[0] - self.sh[0])))

    def _edges(self):
        """Each row's distance from the midline to the left and to the right edge, NaN where an arm or a hand hides it or the edge jumps from its neighbours."""
        y0, y1 = self.y(-0.1), self.y(1.5)
        rows = np.arange(y0, y1 + 1)
        left, right = np.full(len(rows), np.nan), np.full(len(rows), np.nan)
        radius = ARM_RADIUS * self.torso
        arms = [arm_points(self.lm, SH_L, EL_L, WR_L, INDEX_L), arm_points(self.lm, SH_R, EL_R, WR_R, INDEX_R)]
        for n, y in enumerate(rows):
            mid = self.mid(int(y))
            run = run_at(self.mask, int(y), mid)
            if run is None:
                continue
            crossing = [a for a in (arm_x(points, y) for points in arms) if a is not None]
            if not any(run[0] - radius < a < mid for a in crossing):
                left[n] = mid - run[0]
            if not any(mid < a < run[1] + radius for a in crossing):
                right[n] = run[1] - mid
        half = max(int(JUMP_WINDOW * self.torso / 2), 2)
        for side in (left, right):
            original = side.copy()
            for n in range(len(side)):
                window = original[max(n - half, 0):n + half + 1]
                if np.isfinite(window).sum() >= 3 and np.isfinite(original[n]) and abs(original[n] - np.nanmedian(window)) > JUMP * self.torso:
                    side[n] = np.nan
        return {int(y): (l, r) for y, l, r in zip(rows, left, right)}

    def width(self, y, check_arms=True):
        if not check_arms:
            run = run_at(self.mask, y, self.mid(y))
            return None if run is None else float(run[1] - run[0] + 1)
        if self.edges is None:
            self.edges = self._edges()
        left, right = self.edges.get(y, (np.nan, np.nan))
        if np.isfinite(left) and np.isfinite(right):
            return float(left + right + 1)
        return None  # one side alone can't be mirrored: walking sways the pelvis off the midline

    def band(self, band, pick, check_arms=True):
        values = [v for y in range(self.y(band[0]), self.y(band[1]) + 1) if (v := self.width(y, check_arms)) is not None]
        return pick(values) if len(values) >= max(3, 0.3 * (self.y(band[1]) - self.y(band[0]))) else None

    def height(self):
        return float(self.lm[[AN_L, AN_R], 1].mean() - self.top)

    def leg_straight(self):
        lm = self.lm[:, :2]
        return max(angle(lm[HIP_L] - lm[KNEE_L], lm[AN_L] - lm[KNEE_L]), angle(lm[HIP_R] - lm[KNEE_R], lm[AN_R] - lm[KNEE_R])) >= STRAIGHT_LEG

    def skin_in(self, band):
        y0, y1 = self.y(band[0]), self.y(band[1])
        region = self.mask[y0:y1]
        return float(cr.skin_mask(self.crop[y0:y1])[region].mean()) if region.any() else 0.0


def measure_front(f: Frame) -> dict:
    out = {}
    shoulders, bust, waist, hip = f.band(SHOULDER_BAND, max, check_arms=False), f.band(BUST_BAND, max), f.band(WAIST_BAND, min), f.band(HIP_BAND, max)
    if waist and hip:
        out["waist_hip"] = waist / hip
    if bust and hip:
        out["bust_breadth"] = bust / hip
    if shoulders and hip:
        out["shoulder_hip"] = shoulders / hip
    if waist:
        out["waist_w"] = waist / f.torso
    if bust:
        out["bust_w"] = bust / f.torso
    if hip:
        out["hip_w"] = hip / f.torso
    if f.leg_straight():
        h = f.height()
        if h > 0:
            for name, value in (("shoulders", shoulders), ("waist", waist), ("hips", hip)):
                if value:
                    out[f"{name}_H"] = value / h
            out["limb_length_H"] = float(f.lm[[AN_L, AN_R], 1].mean() - f.hip[1]) / h
    # The gluteus's outline, on the gluteus alone: from the waist down every woman's body widens, whatever her gluteus's shape.
    rows = list(range(f.y(GLUTE_TOP), f.y(GLUTE_BOTTOM) + 1))
    widths = np.array([np.nan if (w := f.width(y)) is None else w for y in rows], float)
    n = len(rows)
    upper, lower = widths[:int(0.25 * n) + 1], widths[int(0.75 * n):]
    if n >= 8 and np.isfinite(widths).sum() >= 0.6 * n and np.isfinite(upper).any() and np.isfinite(lower).any():
        top = float(np.nanmax(widths))
        out["upper"], out["lower"] = float(np.nanmedian(upper)) / top, float(np.nanmedian(lower)) / top
        out["peak"] = float(np.nanargmax(widths)) / max(n - 1, 1)
    out["skin_torso"], out["skin_hip"] = f.skin_in((0.2, 0.9)), f.skin_in((0.9, 1.3))
    knee_y = int(f.lm[[KNEE_L, KNEE_R], 1].mean())
    run = run_at(f.mask, knee_y, int(f.lm[[KNEE_L, KNEE_R], 0].mean()))
    out["knees_joined"] = float(run is not None and run[0] <= f.lm[[KNEE_L, KNEE_R], 0].min() and run[1] >= f.lm[[KNEE_L, KNEE_R], 0].max())
    return out


def measure_side(f: Frame) -> dict:
    out = {}
    bust, waist, hip = f.band(BUST_BAND, max, check_arms=False), f.band(WAIST_BAND, min, check_arms=False), f.band(HIP_BAND, max, check_arms=False)
    if bust:
        out["bust_d"] = bust / f.torso
    if waist:
        out["waist_d"] = waist / f.torso
    if hip:
        out["hip_d"] = hip / f.torso
    if waist and hip:
        out["projection"] = hip / waist
    out["skin_bust"] = f.skin_in(BUST_BAND)
    # The breast: the outline of the front of the chest, against the straight line joining its top and its bottom.
    facing = np.sign(f.lm[NOSE, 0] - f.lm[[EAR_L, EAR_R], 0].mean()) or 1.0
    rows = list(range(f.y(0.05), f.y(0.70) + 1))
    edges = []
    for y in rows:
        run = run_at(f.mask, y, f.mid(y))
        edges.append(np.nan if run is None else (run[1] if facing > 0 else run[0]))
    edges = np.array(edges, float)
    arms_forward = any(facing * (f.lm[j, 0] - f.mid(int(f.lm[j, 1]))) > 0.6 * f.band(BUST_BAND, max, check_arms=False) for j in (WR_L, WR_R, EL_L, EL_R) if f.y(0.05) <= f.lm[j, 1] <= f.y(0.70) and f.band(BUST_BAND, max, check_arms=False))
    if len(edges) >= 10 and not np.isnan(edges).any() and not arms_forward:
        line = np.linspace(edges[0], edges[-1], len(edges))
        p = facing * (edges - line)
        p = np.convolve(p, np.ones(3) / 3, mode="same")
        apex = int(np.argmax(p))
        if p[apex] >= 0.02 * f.torso and 0 < apex < len(p) - 1:
            up = apex - int(np.argmax(p[apex::-1] < 0.1 * p[apex])) if (p[apex::-1] < 0.1 * p[apex]).any() else 0
            down = apex + int(np.argmax(p[apex:] < 0.1 * p[apex])) if (p[apex:] < 0.1 * p[apex]).any() else len(p) - 1
            upper, lower = apex - up, down - apex
            if upper > 0 and lower > 0:
                out["breast_upper_lower"] = upper / lower
                out["breast_base"] = (upper + lower) / 2 / f.torso
                out["breast_fullness"] = float(np.mean(p[up:down + 1]) / p[apex])
    return out


def clip_frames(path: Path, view: str, pose):
    """The usable pictures of one clip, a few per second."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step, index, found = max(1, int(round(fps / SAMPLE_HZ))), -1, []
    while cap.grab():
        index += 1
        if index % step:
            continue
        ok, bgr = cap.retrieve()
        if not ok:
            continue
        person, crop = refined(pose, bgr)
        if person is None:
            continue
        f = Frame(person[0], person[1], crop)
        if f.torso <= 20:
            continue
        if (view == "side" and f.ratio <= SIDE_MAX) or (view != "side" and f.ratio >= FRONT_MIN):
            found.append(measure_side(f) if view == "side" else measure_front(f))
    cap.release()
    return found


def median(frames, key, q=50):
    values = [f[key] for f in frames if key in f]
    return float(np.percentile(values, q)) if len(values) >= MIN_FRAMES else None


def level(margin, skin):
    if margin < 0.02:
        return "baixa"
    return "alta" if margin >= 0.06 and skin is not None and skin >= 0.5 else "média"


def silhouette(sex, m, ratios, has_side):
    limits = ratios[sex]
    gaps = []
    measures = {"waist_hip": m.get("waist_hip_girth"), "bust_hip": m.get("bust_hip_girth"), "shoulder_hip": m.get("shoulder_hip")}
    if measures["waist_hip"] is None or measures["shoulder_hip"] is None:
        return None
    for name, spec in limits.items():
        total, count = 0.0, 0
        for key, value in measures.items():
            rng = spec.get(key)
            if rng is None or value is None:
                continue
            lo, hi = rng
            total += max((lo - value) if lo is not None else 0.0, (value - hi) if hi is not None else 0.0, 0.0)
            count += 1
        low = spec["waist_hip"][0] if spec.get("waist_hip") and spec["waist_hip"][0] is not None else 0.0
        gaps.append((total / max(count, 1), -low, name))
    gaps.sort()
    return gaps[0][2], gaps[1][0] - gaps[0][0], gaps[1][2], measures


def biotype(sex, m, table):
    x = []
    for key in BIOTYPE_KEYS:
        value = m.get(f"{key}_H")
        if value is None:
            return None
        x.append(value / NEUTRAL[sex][key])
    x = np.array(x)
    names = list(BIOTYPE_NAMES)
    M = np.array([[table[n][k] for k in BIOTYPE_KEYS] for n in names])
    best = None
    grid = np.arange(0.0, 1.0001, 0.05)
    for a in grid:
        for b in grid:
            c = 1.0 - a - b
            if c < -1e-9:
                continue
            w = np.array([a, b, max(c, 0.0)])
            order = np.argsort(w)
            if w[order[1]] > BIOTYPE_MAX_OTHER + 1e-9 or w[order[0]] + w[order[1]] > BIOTYPE_MAX_OTHERS + 1e-9 or w[order[2]] <= w[order[1]]:
                continue
            error = float(np.sqrt(np.mean((M.T @ w - x) ** 2)))
            if best is None or error < best[0]:
                best = (error, w.copy())
    return best, x, names


def glute(m):
    needed = ("upper", "lower", "peak")
    if any(m.get(k) is None for k in needed):
        return None
    keys = list(needed) + (["projection"] if m.get("projection") is not None else [])
    scores = sorted((math.sqrt(sum(((m[k] - p[k]) / GLUTE_SCALE[k]) ** 2 for k in keys) / len(keys)), n) for n, p in GLUTE_PROTOTYPES.items())
    return scores[0][1], scores[1][0] - scores[0][0], scores[1][1]


def breast(m, shapes):
    if m.get("breast_upper_lower") is None:
        return None
    scores = []
    for name in ("redondos", "gota", "conicos", "tuberosos"):
        s = shapes[name]
        fullness = float(np.mean((1 - np.linspace(-1, 1, 201) ** 2) ** s["power"]))
        d = (math.log(m["breast_upper_lower"] / (s["upper"] / s["lower"])) / 0.4) ** 2 + ((m["breast_fullness"] - fullness) / 0.1) ** 2 + ((m["breast_base"] - s["base_cm"] / TORSO_CM) / 0.04) ** 2
        scores.append((math.sqrt(d / 3), name))
    scores.sort()
    return scores[0][1], scores[1][0] - scores[0][0], scores[1][1]


def classify(model, by_view, sex, ratios, biotypes, shapes):
    front_like = by_view["front"] + by_view["back"]
    back_first = by_view["back"] or by_view["front"]
    side = by_view["side"]
    m = {k: median(front_like, k) for k in ("waist_hip", "bust_breadth", "shoulder_hip", "waist_w", "bust_w", "hip_w", "shoulders_H", "waist_H", "hips_H", "limb_length_H", "skin_torso", "skin_hip", "knees_joined")}
    m.update({k: median(back_first, k) for k in ("upper", "lower", "peak")})
    m.update({k: median(side, k) for k in ("bust_d", "waist_d", "hip_d", "projection", "skin_bust", "breast_upper_lower", "breast_base", "breast_fullness")})
    fit = GIRTH_FIT[sex]
    if m["waist_w"] and m["hip_w"] and m["waist_d"] and m["hip_d"]:
        a, b = fit["waist_ellipse"]
        m["waist_hip_girth"] = a + b * ellipse(m["waist_w"], m["waist_d"]) / ellipse(m["hip_w"], m["hip_d"])
    elif m["waist_hip"]:
        a, b = fit["waist_breadth"]
        m["waist_hip_girth"] = a + b * m["waist_hip"]
    if m["bust_w"] and m["hip_w"] and m["bust_d"] and m["hip_d"]:
        a, b = fit["bust_ellipse"]
        m["bust_hip_girth"] = a + b * ellipse(m["bust_w"], m["bust_d"]) / ellipse(m["hip_w"], m["hip_d"])

    loose = m["knees_joined"] is not None and m["knees_joined"] > 0.7 and m["skin_hip"] is not None and m["skin_hip"] < 0.25
    row = {"modelo": model, "quadros_frente": len(by_view["front"]), "quadros_costas": len(by_view["back"]), "quadros_lado": len(side), "roupa_larga_no_quadril": "sim" if loose else "não"}

    s = silhouette(sex, m, ratios, bool(side))
    if s:
        name, margin, second, measures = s
        conf = "baixa" if loose else level(margin, m["skin_torso"])
        row.update(silhueta=name, silhueta_conf=conf, silhueta_2a=second, cintura_quadril=measures["waist_hip"], busto_quadril=measures["bust_hip"], ombro_quadril=measures["shoulder_hip"])
    else:
        row.update(silhueta="sem medida", silhueta_conf="")

    b = biotype(sex, m, biotypes)
    if b and b[0]:
        (error, w), x, names = b
        order = list(np.argsort(-w))
        row["biotipo"] = BIOTYPE_NAMES[names[order[0]]]
        row["biotipo_mistura"] = ", ".join(f"{BIOTYPE_NAMES[names[i]]} {w[i]:.0%}" for i in order if w[i] > 0)
        row["biotipo_conf"] = "baixa" if loose or error > 0.06 or w[order[0]] < 0.5 else "média"
        row.update(zip(("ombro_altura_rel", "cintura_altura_rel", "quadril_altura_rel", "perna_altura_rel"), x))
    else:
        row.update(biotipo="sem medida", biotipo_conf="")

    g = glute(m)
    if g:
        name, margin, second = g
        conf = "baixa"  # always: moving the declared prototypes a little moved most of 23 models from coração to quadrado (2026-11-10)
        row.update(gluteo=name, gluteo_conf=conf, gluteo_2a=second, gluteo_vista="costas" if by_view["back"] else "frente")
    else:
        row.update(gluteo="sem medida", gluteo_conf="")

    if not side:
        row.update(seio="sem vista de lado", seio_conf="")
    else:
        br = breast(m, shapes)
        if br:
            name, margin, second = br
            row.update(seio=name, seio_conf="baixa" if (m["skin_bust"] or 0) < 0.5 or margin < 0.15 else "média", seio_2a=second)
        else:
            row.update(seio="sem contorno claro", seio_conf="")
    return row


def worker(job):
    model, clips, sex, data = job
    ratios, biotypes, shapes = data
    by_view = {"front": [], "back": [], "side": []}
    with mp_pose.Pose(static_image_mode=True, model_complexity=1, enable_segmentation=True) as pose:
        for path, view in clips:
            by_view[view] += clip_frames(path, view, pose)
    return classify(model, by_view, sex, ratios, biotypes, shapes)


COLUMNS = ["modelo", "silhueta", "silhueta_conf", "silhueta_2a", "biotipo", "biotipo_mistura", "biotipo_conf", "gluteo", "gluteo_conf", "gluteo_2a", "gluteo_vista", "seio", "seio_conf", "seio_2a", "roupa_larga_no_quadril",
           "cintura_quadril", "busto_quadril", "ombro_quadril", "ombro_altura_rel", "cintura_altura_rel", "quadril_altura_rel", "perna_altura_rel", "quadros_frente", "quadros_costas", "quadros_lado"]


def text(value):
    return "" if value is None else f"{value:.2f}" if isinstance(value, float) else str(value)


def write_page(path: Path, rows, thumbs):
    cards = []
    for r in rows:
        images = "".join(f'<img loading="lazy" src="{html.escape(t)}" alt="">' for t in thumbs[r["modelo"]])
        line = lambda label, key, conf, second=None: f'<div class="l"><b>{label}</b> {html.escape(text(r.get(key)))}' + (f' <span class="c">{html.escape(text(r.get(conf)))}</span>' if r.get(conf) else "") + (f' <span class="s">depois: {html.escape(text(r.get(second)))}</span>' if second and r.get(second) else "") + "</div>"
        cards.append(f'<div class="card"><h2>Modelo {html.escape(r["modelo"])}</h2><div class="imgs">{images}</div>{line("Silhueta", "silhueta", "silhueta_conf", "silhueta_2a")}{line("Biotipo", "biotipo", "biotipo_conf")}'
                     f'<div class="s">{html.escape(text(r.get("biotipo_mistura")))}</div>{line("Glúteo", "gluteo", "gluteo_conf", "gluteo_2a")}{line("Seio", "seio", "seio_conf", "seio_2a")}'
                     f'<div class="s">cintura/quadril {text(r.get("cintura_quadril"))} · busto/quadril {text(r.get("busto_quadril"))} · ombro/quadril {text(r.get("ombro_quadril"))}</div></div>')
    path.write_text("""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Classificação dos corpos</title><style>
:root{--bg:#f6f6f4;--card:#fff;--text:#1c1c1a;--muted:#6b6b66;--line:#dcdcd6}@media (prefers-color-scheme:dark){:root{--bg:#191917;--card:#242421;--text:#ecece6;--muted:#a3a39b;--line:#3a3a35}}
body{margin:0;padding:16px;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,sans-serif}h1{font-size:20px;margin:0 0 4px}p{color:var(--muted);margin:0 0 12px}h2{font-size:16px;margin:0 0 6px}
#g{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px}.imgs{display:flex;gap:4px;overflow-x:auto;margin-bottom:8px}img{height:220px;border-radius:4px}
.c{font-size:12px;padding:1px 6px;border:1px solid var(--line);border-radius:10px}.s{font-size:12px;color:var(--muted)}.l{margin-top:4px}</style></head><body><h1>Classificação dos corpos</h1>
<p>Medida no contorno do corpo como a câmera vê, com a roupa. Roupa solta conta como corpo. Confira cada uma a olho.</p><div id="g">""" + "".join(cards) + "</div></body></html>", encoding="utf-8")


def model_sort(name):
    return (0, int(name)) if name.isdigit() else (1, name)


def main(args) -> int:
    sex = "female"
    if "--sexo" in args:
        at = args.index("--sexo")
        sex = args[at + 1]
        args = args[:at] + args[at + 2:]
    if len(args) != 1:
        print(__doc__)
        return 2
    table = cr.wsl_path(args[0])
    base = table.parent
    groups, thumbs = defaultdict(list), defaultdict(list)
    with open(table, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name, view = row["modelo"].strip(), VIEW_OF_DIRECTION.get(row["direcao"])
            if not name or row["descartar"] == "sim":
                continue
            if view:
                groups[name].append((base / row["clip"], view))
            thumbs[name].append(row["clip"].replace("clips/", "thumbs/").replace(".mp4", ".jpg"))
    read = lambda n: json.loads((DATA / n).read_text(encoding="utf-8"))
    data = (read("silhouette_ratios.json"), read("biotypes.json"), read("breast_shapes.json"))
    jobs = [(m, clips, sex, data) for m, clips in sorted(groups.items(), key=lambda kv: model_sort(kv[0]))]
    with Pool(WORKERS) as pool:
        rows = pool.map(worker, jobs, chunksize=1)
    with open(base / "classificacao.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows({k: text(v) for k, v in r.items()} for r in rows)
    write_page(base / "classificacao.html", rows, thumbs)
    for r in rows:
        print(f"{r['modelo']:>4}  {text(r.get('silhueta')):20} {text(r.get('silhueta_conf')):6}  {text(r.get('biotipo')):11} {text(r.get('biotipo_conf')):6}  {text(r.get('gluteo')):11} {text(r.get('gluteo_conf')):6}  {text(r.get('seio')):18} {text(r.get('seio_conf'))}")
    print(f"\n{len(rows)} modelos: {base / 'classificacao.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

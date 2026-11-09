"""Muscles as volume: each muscle's chain of points, attached to the bones (hmcore.muscle), as a voxel solid thin at its tendons and thick at its belly. So muscle follows its bones when these grow or shrink, and a joint holds tendons, not a shell of muscle (Rafael's choice, 2026-11-09)."""
import numpy as np
from hmcore.muscle import spindle_profile

GROUPS = ("leg", "trunk")  # the face's, jaw's and tongue's muscles aren't part of the body's volume


def select(muscles, replaced=()):
    """The muscles that make up the body's volume, without those replaced by fans."""
    return [m for m in muscles if m["group"] in GROUPS and m["name"].rsplit("_", 1)[0] not in replaced]


def rasterize(points, radius, origin, shape, h, mask):
    """Marks in mask the cells inside this muscle: for each cell near the chain, its distance to the chain against the spindle's radius at that place along it."""
    points = np.asarray(points, float)
    lengths = np.linalg.norm(np.diff(points, axis=0), axis=1)
    total = lengths.sum()
    if total <= 0:
        return mask
    cuts = np.concatenate([[0.0], np.cumsum(lengths)]) / total
    for i, (a, b) in enumerate(zip(points[:-1], points[1:])):
        lo = np.floor((np.minimum(a, b) - radius - origin) / h).astype(int) - 1
        hi = np.ceil((np.maximum(a, b) + radius - origin) / h).astype(int) + 2
        lo, hi = np.maximum(lo, 0), np.minimum(hi, shape)
        if (hi <= lo).any():
            continue
        idx = np.indices(hi - lo).reshape(3, -1).T + lo
        c = origin + (idx + 0.5) * h
        d = b - a
        t = np.clip((c - a) @ d / max(d @ d, 1e-12), 0.0, 1.0)
        distance = np.linalg.norm(c - (a + t[:, None] * d), axis=1)
        u = cuts[i] + t * (cuts[i + 1] - cuts[i])
        inside = distance <= radius * spindle_profile(u)
        mask[tuple(idx[inside].T)] = True
    return mask


def solids(muscles, origin, shape, h, volume_scale=1.0, by_prefix=None):
    """All these muscles as one voxel mask. volume_scale multiplies every volume (the biotype's); by_prefix {name prefix: factor} one group's (a gluteus shape's)."""
    mask = np.zeros(shape, bool)
    for m in muscles:
        factor = volume_scale * next((v for k, v in (by_prefix or {}).items() if m["name"].startswith(k)), 1.0)
        rasterize(m["points"], m["radius"] * np.sqrt(factor), origin, shape, h, mask)
    return mask

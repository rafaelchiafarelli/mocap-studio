"""Muscle and fat grown outward from the bones, and the skin as their result (initiative body-type-selection, epic volumes-outward). Numpy and scipy only; the bones reach it as a mask from whoever rasterized them.
The order of a body in this path: bones, muscle around them by zone, fat around that up to the body-fat percentage, and the 13,380 skin points moved onto what results."""
import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

DENSITY = {"bone": 1500.0, "muscle": 1060.0, "fat": 900.0, "skin": 1100.0, "cavity": 900.0}  # kg/m3, as in tools/body_report.py
REAL_SKIN_M = 0.0015  # as tools/body_report.py's REAL_SKIN_MM


def core_mask(centres, hull_points, in_bone):
    """Where the body's inside starts: the bones, and the trunk's cavity as the convex hull of its bones. Muscle grows from here."""
    hull = ConvexHull(hull_points)
    inside = np.ones(len(centres), bool)
    for s in range(0, len(centres), 200_000):
        inside[s:s + 200_000] = np.all(centres[s:s + 200_000] @ hull.equations[:, :3].T + hull.equations[:, 3] <= 1e-9, axis=1)
    return in_bone | inside


def grow(mask, thickness_m, keep, h):
    """The cells within thickness_m (one value per cell, or one for all) of mask, inside keep. Distances are the exact Euclidean transform on the grid."""
    distance = ndimage.distance_transform_edt(~mask) * h
    return (distance <= thickness_m) & keep


def muscle_layer(core, muscle_m_per_cell, scale, keep, h):
    """The muscle: everything within its zone's thickness of the core, scaled by the biotype's muscle. Cells of the core itself aren't muscle."""
    return grow(core, muscle_m_per_cell * scale, keep, h) & ~core

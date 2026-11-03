"""Anthropometric measurements: ANSUR II rows and CT labels, in metres."""
import csv, io, math
import numpy as np
from hmcore import ctbones


# Below these a "whole" label is a fragment: the field of view can also clip a bone without touching the volume's face, after resampling. Metres.
COMPLETE_MIN = {"humerus_len_left": 0.24, "humerus_len_right": 0.24, "clavicle_len": 0.11, "scapula_len": 0.12, "skull_height": 0.15, "skull_depth": 0.14, "skull_width": 0.11}


def complete_values(rows, key):
    """Values of one measurement across subjects, without fragments."""
    floor = COMPLETE_MIN.get(key, 0.0)
    return [r[key] for r in rows if r.get(key) and r[key] >= floor]


def ansur_rows(text):
    return list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))


def ansur_value(row, column):
    """ANSUR lengths are millimetres. Mass is in hectograms although the column says weightkg (per the OpenLab page)."""
    v = float(row[column])
    if column == "weightkg":
        return v / 10.0
    return v / 1000.0


def summary(values):
    a = np.asarray([v for v in values if v is not None and not math.isnan(v)], dtype=float)
    if len(a) == 0:
        return {"n": 0, "mean": None, "sd": None}
    return {"n": int(len(a)), "mean": float(a.mean()), "sd": float(a.std(ddof=1)) if len(a) > 1 else 0.0}


def z_score(value, stats):
    return (value - stats["mean"]) / stats["sd"] if stats["sd"] else None


def bbox_extent_m(mask, affine):
    """Bounding box of a label in metres, from voxel size. Axes are RAS: width, depth, height."""
    idx = np.argwhere(mask)
    spacing = np.sqrt((affine[:3, :3] ** 2).sum(axis=0))
    return (idx.max(0) - idx.min(0) + 1) * spacing / 1000.0


def label_volume_l(mask, affine):
    return float(mask.sum() * abs(np.linalg.det(affine[:3, :3])) / 1e6)


def long_bone_length_m(mask, affine):
    """Principal-axis length of a complete bone, None when the scan cuts it."""
    if not mask.any() or ctbones.touches_scan_edge(mask):
        return None
    idx = np.argwhere(mask)[::7]
    spacing = np.sqrt((affine[:3, :3] ** 2).sum(axis=0))
    p = idx * spacing / 1000.0
    p = p - p.mean(0)
    axis = np.linalg.svd(p, full_matrices=False)[2][0]
    d = p @ axis
    return float(d.max() - d.min())

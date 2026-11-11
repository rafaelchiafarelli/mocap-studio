"""Sway and travelling waves on the skin, as one offset per vertex along its rest normal (initiative animation-body).
Each vertex is a mass on a spring to its rest place, pushed by the inertia of its own motion and joined to its neighbours, so a bump travels across the skin and dies out. The offset is bounded, so the skin can't leak through the body. Plain numpy."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from hmcore import deltamush as dm


@dataclass
class Values:
    """Per vertex: how much of the inertia reaches it (0 to 1), natural frequency in Hz, damping ratio, wave speed in m/s."""
    gain: np.ndarray
    hz: np.ndarray
    damping: np.ndarray
    speed: np.ndarray


LIMIT_M = 0.04  # the most a point may leave its rest place


def laplacian_scale(rest, adjacency):
    """1 / mean edge length squared at each vertex, so the wave speed is in metres per second."""
    starts, targets = adjacency
    counts = np.diff(starts)
    index = np.repeat(np.arange(len(rest)), counts)
    total = np.zeros(len(rest))
    np.add.at(total, index, np.linalg.norm(rest[index] - rest[targets], axis=1))
    mean = total / np.maximum(counts, 1)
    return 1.0 / np.maximum(mean, 1e-4) ** 2, counts, index


def stable_substeps(rest, tris, values, fps, safety=0.4):
    """Enough steps per frame for the wave and the spring to stay stable."""
    adjacency = dm.neighbours(tris, len(rest))
    scale, _, _ = laplacian_scale(rest, adjacency)
    fastest = np.sqrt(np.maximum(4.0 * values.speed**2 * scale + (2 * np.pi * values.hz) ** 2, 1e-9))
    return max(1, int(np.ceil(float(fastest.max()) / (fps * safety * 2.0))))


def inertia(positions, normals, fps):
    """Each vertex's acceleration along its normal in each frame, in m/s2, from its motion over the frames. positions: frames x vertices x 3."""
    a = np.zeros(positions.shape)
    a[1:-1] = (positions[2:] - 2 * positions[1:-1] + positions[:-2]) * fps * fps
    return (a * normals).sum(axis=2)


def simulate(rest, tris, values: Values, drive, fps, pulses=None, substeps=None, limit=LIMIT_M):
    """Offsets per frame and vertex. drive: frames x vertices, the acceleration along the normal; pulses: the same, or None, added to it at each substep (see foot_impact)."""
    adjacency = dm.neighbours(tris, len(rest))
    scale, counts, index = laplacian_scale(rest, adjacency)
    steps = substeps or stable_substeps(rest, tris, values, fps)
    dt = 1.0 / (fps * steps)
    omega = 2.0 * np.pi * values.hz
    spring, friction = omega**2, 2.0 * values.damping * omega
    wave = 4.0 * values.speed**2 * scale
    targets = adjacency[1]
    n = len(rest)
    u, v = np.zeros(n), np.zeros(n)
    frames = drive.shape[0]
    out = np.zeros((frames, n), np.float32)
    for f in range(frames):
        for s in range(steps):
            mean = np.zeros(n)
            np.add.at(mean, index, u[targets])
            mean = mean / np.maximum(counts, 1)
            push = -values.gain * (drive[f] + (0.0 if pulses is None else pulses(f, s, steps)))
            v += dt * (push - spring * u - friction * v + wave * (mean - u))
            u = np.clip(u + dt * v, -limit, limit)
        out[f] = u
    return out, steps


def regions(rest, normals, bone_weights, marks, adjacency, smoothing=10):
    """Named masks from 0 to 1 over the skin, softened along the mesh so regions change smoothly. bone_weights: {bone: per-vertex weight}; marks: {name: height in m}. +Y is the back."""
    x, y, z = rest[:, 0], rest[:, 1], rest[:, 2]
    w = lambda *names: np.maximum.reduce([bone_weights.get(n, np.zeros(len(rest))) for n in names])
    def box(low, high, edge=0.02):
        return np.clip((z - low) / edge, 0, 1) * np.clip((high - z) / edge, 0, 1)
    glute_z = box(marks["hip_joint"] - 0.11, marks["hip_joint"] + 0.11, 0.03)
    trunk_z = box(marks["hip_joint"] + 0.04, marks["ribs"], 0.03)
    masks = {
        "breast": np.clip(w("breast.L", "breast.R") * 2.5, 0, 1),
        "glute": glute_z * np.clip((y - 0.0) / 0.04, 0, 1) * np.clip((0.24 - np.abs(x)) / 0.03, 0, 1),
        "belly": trunk_z * np.clip((-y) / 0.03, 0, 1) * np.clip((0.15 - np.abs(x)) / 0.03, 0, 1),
        "flank": trunk_z * np.clip((np.abs(x) - 0.09) / 0.03, 0, 1) * np.clip((0.26 - np.abs(x)) / 0.02, 0, 1),
        "thigh": np.clip(w("thigh.L", "thigh.R") * 1.6, 0, 1) * (1.0 - glute_z),
        "upper_arm": np.clip(w("upper_arm.L", "upper_arm.R") * 1.6, 0, 1) * np.clip((y + 0.005) / 0.02, 0, 1),
        "calf": np.clip(w("shin.L", "shin.R") * 1.6, 0, 1) * np.clip((y + 0.005) / 0.02, 0, 1),
    }
    return {name: dm.smooth(mask[:, None].astype(float), adjacency, smoothing)[:, 0] for name, mask in masks.items()}


def values_from(masks, table, n):
    """The vertex values from the masks: each mask's table row, weighted by the mask; where no mask reaches, the table's base."""
    names = ("gain", "hz", "damping", "speed")
    total = np.zeros(n)
    sums = {k: np.zeros(n) for k in names}
    for region, mask in masks.items():
        row = table[region]
        total += mask
        for k in names:
            sums[k] += mask * row[k]
    base = table["base"]
    share = np.clip(total, 0, 1)
    out = {}
    for k in names:
        mixed = sums[k] / np.maximum(total, 1e-6)
        out[k] = share * mixed + (1 - share) * base[k]
    return Values(**out)


def contact_dent(positions, hands, arm_weight, adjacency, gives=0.005, spread=3):  # 5 mm at most: Rafael, 2026-11-11
    """How far the skin sinks under the hands, per frame and vertex (positive is inward). hands: frames x points x (x, y, z, radius).
    A skin vertex inside a point's sphere sinks by how far it is inside, up to `gives`, and the dent spreads a little along the skin. The arms' own skin doesn't sink."""
    frames, n = positions.shape[0], positions.shape[1]
    out = np.zeros((frames, n), np.float32)
    free = arm_weight < 0.2
    for f in range(frames):
        depth = np.zeros(n)
        for x, y, z, r in hands[f]:
            dist = np.linalg.norm(positions[f] - (x, y, z), axis=1)
            depth = np.maximum(depth, r - dist)
        depth = np.clip(depth, 0.0, gives) * free
        if depth.any():
            spread_out = dm.smooth(depth[:, None], adjacency, spread, 0.5)[:, 0]
            out[f] = np.maximum(depth, spread_out) * free
    return out

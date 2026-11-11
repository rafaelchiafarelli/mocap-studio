"""Folds of the skin as data: distances along the mesh from a fold's line, and the dent they make. Plain numpy, for Blender's Python and the tests."""
from __future__ import annotations

import heapq

import numpy as np


def edges_of(tris):
    a = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    a = np.sort(a, axis=1)
    return np.unique(a, axis=0)


def surface_distance(verts, edges, sources, limit):
    """Shortest distance along the mesh's edges from a set of vertices, up to limit; beyond it the distance is inf."""
    adjacency: dict[int, list] = {}
    lengths = np.linalg.norm(verts[edges[:, 0]] - verts[edges[:, 1]], axis=1)
    for (a, b), d in zip(edges.tolist(), lengths.tolist()):
        adjacency.setdefault(a, []).append((b, d))
        adjacency.setdefault(b, []).append((a, d))
    best = np.full(len(verts), np.inf)
    heap = [(0.0, int(s)) for s in sources]
    for _, s in heap:
        best[s] = 0.0
    heapq.heapify(heap)
    while heap:
        distance, v = heapq.heappop(heap)
        if distance > best[v]:
            continue
        for w, d in adjacency.get(v, []):
            total = distance + d
            if total < best[w] and total <= limit:
                best[w] = total
                heapq.heappush(heap, (total, w))
    return best


def profile(distance, width, bulge=0.35):
    """A fold's shape across its line: 1 on the line, falling to 0, with the skin pushed slightly the other way on both sides, as tissue piles up next to a crease."""
    d = np.where(np.isfinite(distance), distance, 1e9)
    sigma = max(width / 2.0, 1e-6)
    return np.exp(-((d / sigma) ** 2)) - bulge * np.exp(-(((d - 1.5 * sigma) / sigma) ** 2))

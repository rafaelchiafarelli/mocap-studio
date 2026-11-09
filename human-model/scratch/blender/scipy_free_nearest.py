"""Nearest neighbour without scipy, which Blender doesn't ship."""
from mathutils import kdtree


def nearest(queries, points):
    k = kdtree.KDTree(len(points))
    for i, p in enumerate(points):
        k.insert(tuple(p), i)
    k.balance()
    return [k.find(tuple(q))[1] for q in queries]

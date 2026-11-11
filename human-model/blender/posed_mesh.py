"""The posed skin as plain arrays, and how much its triangles shrink: shared by range_of_motion.py and pose_corrections.py."""
import bpy
import numpy as np

N_BODY = 13380


def set_display(body, on):
    """Mask and Subsurf hide or add vertices: off while reading, so the vertices are MPFB's own, in order."""
    for m in body.modifiers:
        if m.type in ("MASK", "SUBSURF"):
            m.show_viewport = on


def read(body):
    """Skin positions in world space, helpers included, with the current pose and shape keys; call with display off."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = body.evaluated_get(dg)
    me = ev.to_mesh()
    c = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", c)
    ev.to_mesh_clear()
    c = c.reshape(-1, 3)
    M = np.array(body.matrix_world)
    return c @ M[:3, :3].T + M[:3, 3]


def triangles(body):
    tris = []
    for p in body.data.polygons:
        v = list(p.vertices)
        if max(v) < N_BODY:
            tris += [[v[0], v[i], v[i + 1]] for i in range(1, len(v) - 1)]
    return np.array(tris)


def areas(verts, tris):
    return 0.5 * np.linalg.norm(np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]]), axis=1)


def collapse(rest, posed, tris, center=None, radius=None):
    """Share of the triangles that keep under 40% of their rest area, and the 1st percentile of area ratio, near a point if given."""
    ratio = areas(posed, tris) / np.maximum(areas(rest, tris), 1e-9)
    if center is not None:
        mid = rest[tris].mean(axis=1)
        ratio = ratio[np.linalg.norm(mid - center, axis=1) <= radius]
    return float((ratio < 0.4).mean()), float(np.percentile(ratio, 1))

"""The skin pushed outward where a bone lies too close under it or comes through it (task muscle-physics/inside-out-skin/1).
Each round: every bone point asks for its declared least depth of tissue; the skin vertices of the triangle nearest to it move out along
their normals by what's missing; the push is spread smoothly over the skin; the ends at the neck, wrists and ankles stay put.
The mesh and its vertex order are MPFB's, so everything built on it still fits. Point queries go through the GPU mesh class passed in."""
import numpy as np
from . import body


def vertex_normals(verts, tris):
    n = np.zeros_like(verts)
    face = np.cross(verts[tris[:, 1]] - verts[tris[:, 0]], verts[tris[:, 2]] - verts[tris[:, 0]])
    for k in range(3):
        np.add.at(n, tris[:, k], face)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def least_depth(name, table):
    """The declared least tissue over a bone, in metres: the longest matching name prefix in table, else its "default"."""
    match = max((k for k in table if k != "default" and name.startswith(k)), key=len, default="default")
    return table[match] / 1000


def spread(need, tris, n_verts, fixed, iterations, falloff):
    """A smooth push at least as large as need: averaged with neighbours, shrunk by falloff, then raised back to need, over and over.
    The result falls off around each pushed spot instead of making a bump. Without the falloff it spread over the whole skin and grew
    the bust by 3.2 cm (skin_v1). Fixed vertices stay at zero."""
    edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    edges = np.concatenate([edges, edges[:, ::-1]])
    deg = np.maximum(np.bincount(edges[:, 0], minlength=n_verts), 1)
    d = need.copy()
    for _ in range(iterations):
        avg = np.bincount(edges[:, 0], weights=d[edges[:, 1]], minlength=n_verts) / deg
        d = np.maximum(need, falloff * avg)
        d[fixed] = 0.0
    return d


def bone_points(bones, rig, closed_mesh, table):
    """Every bone vertex inside the body's reach, with the depth it asks for: bones mostly beyond the cuts (head, hands, feet) are left out,
    and so are points near a cut, whose bone leaves the skin there by design."""
    pts, depth, owner = [], [], []
    for name, (v, _) in sorted(bones.items()):
        if closed_mesh.inside(v).mean() < 0.5:
            continue
        keep = ~body.near_a_cut(v, rig)
        pts.append(v[keep])
        depth.append(np.full(keep.sum(), least_depth(name, table)))
        owner += [name] * int(keep.sum())
    return np.concatenate(pts), np.concatenate(depth), np.array(owner)


def depth_under_skin(points, closed_mesh, surface_mesh):
    """Signed depth of each point under the skin: positive inside the body, negative outside. Also the nearest skin face and its (u, v)."""
    inside = closed_mesh.inside(points)
    dist, face, uv = surface_mesh.closest(points)
    return np.where(inside, dist, -dist), face, uv


def fit(skin, all_tris, patch, bones, rig, table, max_push, gpu_mesh, rounds=6, iterations=40, falloff=0.8):
    """The pushed skin. Returns the new body vertices and a record of every round.
    A bone that needs more than max_push anywhere is left alone and reported as misplaced: pushing the skin part of the way for it
    grew a hump over the right scapula (skin_v1)."""
    skin = skin.copy()
    ids = np.unique(patch)
    fixed = np.setdiff1d(np.arange(len(skin)), ids)
    fixed = np.union1d(fixed, np.concatenate([loop for loop in body.layers.boundary_loops(patch)]))
    closed = gpu_mesh(*body.layers.capped(skin, patch))
    pts, want, owner = bone_points(bones, rig, closed, table)
    depth, _, _ = depth_under_skin(pts, closed, gpu_mesh(skin, patch))
    misplaced = sorted({o for o in np.unique(owner) if (want - depth)[owner == o].max() > max_push})
    pushing = ~np.isin(owner, misplaced)
    total = np.zeros(len(skin))
    record = []
    for r in range(rounds):
        closed = gpu_mesh(*body.layers.capped(skin, patch))
        surface = gpu_mesh(skin, patch)
        depth, face, uv = depth_under_skin(pts, closed, surface)
        missing = want - depth
        short = (missing > 1e-4) & pushing
        need = np.zeros(len(skin))
        if short.any():
            w = np.column_stack([uv[short, 0], uv[short, 1], 1 - uv[short].sum(axis=1)])
            corners = patch[face[short]]
            for k in range(3):
                np.maximum.at(need, corners[:, k], missing[short] * (w[:, k] > 0.15))
        capped = need + total > max_push
        need = np.minimum(need, np.maximum(max_push - total, 0.0))
        push = spread(need, all_tris, len(skin), fixed, iterations, falloff)
        record.append({"round": r + 1, "bone_points_short": int(short.sum()), "bone_points_outside": int(((depth < 0) & pushing).sum()),
                       "worst_missing_mm": round(float(missing.max()) * 1000, 2), "vertices_at_most_push": int(capped.sum()),
                       "largest_push_this_round_mm": round(float(push.max()) * 1000, 2)})
        if not short.any() or push.max() < 1e-5:
            break
        # Along the skin's normal. Pushing away from the bone instead (skin_v3) left the sacrum 7 mm out, against 0 mm this way:
        # in the cleft between the buttocks neither direction covers it, and bug human-model/2 says the sacrum sits too far back
        skin += push[:, None] * vertex_normals(skin, all_tris)
        total += push
    closed = gpu_mesh(*body.layers.capped(skin, patch))
    surface = gpu_mesh(skin, patch)
    depth, _, _ = depth_under_skin(pts, closed, surface)
    return skin, total, {"rounds": record, "points": pts, "want": want, "owner": owner, "depth_after": depth, "misplaced": misplaced}

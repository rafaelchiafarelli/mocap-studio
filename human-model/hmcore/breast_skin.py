"""The skin grows with the breast: the mesh over each breast moves onto a smooth outline over the chest, keeping its small detail (areola, nipple) and fading out around it. Numpy only, so the Blender panel can use it live.
Model frame: the body faces -Y, its left is +X, up is +Z. The outline is a height over the chest's front: `project` at the middle, closing to zero at the edge of the base, as `power` says (2 is round)."""
import numpy as np

DETAIL_ITERATIONS = 20  # how far the mesh is smoothed to find what is detail (areola, nipple) and what is form
DETAIL_FROM, DETAIL_TO = 0.25, 0.45  # in shares of the base: the areola and nipple
FRONT_REACH = 0.09  # m behind the nipple: only the skin in front of this belongs to the breast, or the same x and z on the back would move too
FADE_FROM, FADE_TO = 0.85, 1.3  # in shares of the base: full move inside, none beyond


def params(apex, side, difference_cm, neutral_difference_cm, wish, table, factor=1.0):
    """One breast's outline. apex: the nipple's position. wish: the character's breast, whose projection_cm, base_cm, upper, lower and power override the shape's."""
    s = table[wish.get("shape") or "redondos"]
    a = table["adjustments"]
    asym = wish.get("assimetricos", 1.0)
    side_factor = asym if not isinstance(asym, dict) else asym.get("L" if side > 0 else "R", 1.0)
    project = (wish["projection_cm"] / 100 if wish.get("projection_cm") else max(difference_cm, 1.0) * a["projection_per_cm"] / 100) * side_factor * factor
    base = (wish["base_cm"] if wish.get("base_cm") else s["base_cm"]) / 100
    scale = 1.0 if wish.get("base_cm") else (max(difference_cm, 1.0) / neutral_difference_cm) ** (1 / 3)
    return {"front_y": float(apex[1]) + FRONT_REACH, "cx": float(apex[0]) + side * wish.get("espacados", 0.0) * a["espacados_m"], "cz": float(apex[2]) - wish.get("pendentes", 0.0) * a["pendentes_m"],
            "project": project, "radius": base * scale * side_factor ** (1 / 3), "upper": wish.get("upper") or s["upper"], "lower": wish.get("lower") or s["lower"], "power": wish.get("power") or s["power"]}


def rho(points, p):
    """How far out on the base each point lies, seen from the front: 0 at the middle, 1 at the edge."""
    ex = (points[:, 0] - p["cx"]) / p["radius"]
    dz = points[:, 2] - p["cz"]
    ez = dz / (p["radius"] * np.where(dz >= 0, p["upper"], p["lower"]))
    return np.sqrt(ex ** 2 + ez ** 2)


def wall_y(points, p):
    """The chest's front around this breast: the median y of the skin just beyond the base."""
    r = rho(points, p)
    return float(np.median(points[(r > 1.05) & (r < 1.4) & (points[:, 1] < p["front_y"]), 1]))


def smooth(values, tris, n, iterations):
    edges = np.concatenate([tris[:, [0, 1]], tris[:, [1, 2]], tris[:, [2, 0]]])
    edges = np.concatenate([edges, edges[:, ::-1]])
    degree = np.bincount(edges[:, 0], minlength=n)
    v = np.asarray(values, float).copy()
    for _ in range(iterations):
        s = np.bincount(edges[:, 0], weights=v[edges[:, 1]], minlength=n)
        v = np.where(degree > 0, 0.5 * v + 0.5 * s / np.maximum(degree, 1), v)
    return v


def inflate(verts, tris, outlines):
    """A copy of verts with each breast's skin on its outline. The skin keeps what it has of detail over the smooth form, so the nipple rides out with the skin; beyond the base it stays where it was. outlines: params() of each breast."""
    v = np.asarray(verts, float).copy()
    for p in outlines:
        r = rho(v, p)
        wall = wall_y(v, p)
        form = smooth(v[:, 1], tris, len(v), DETAIL_ITERATIONS)
        height = p["project"] * np.maximum(1.0 - r ** 2, 0.0) ** (1.0 / p["power"])
        t = np.clip((FADE_TO - r) / (FADE_TO - FADE_FROM), 0.0, 1.0)
        fade = t * t * (3 - 2 * t) * (v[:, 1] < p["front_y"])
        near = np.clip((DETAIL_TO - r) / (DETAIL_TO - DETAIL_FROM), 0.0, 1.0)  # detail only around the nipple: on the slopes, the difference from the smoothed form is the slope itself, and it made bands in the skin
        v[:, 1] = (1 - fade) * v[:, 1] + fade * (wall - height + (v[:, 1] - form) * near * near * (3 - 2 * near))
    return v


def footprint(points, p):
    """Which points lie over this breast's base."""
    return (rho(points, p) < 1.0) & (points[:, 1] < p["front_y"])

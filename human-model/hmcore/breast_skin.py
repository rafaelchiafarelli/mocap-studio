"""The skin grows with the breast: the mesh over each breast moves onto a smooth outline over the chest, keeping its small detail (areola, nipple) and fading out around it. Numpy only, so the Blender panel can use it live.
Model frame: the body faces -Y, its left is +X, up is +Z. The outline is a height over the chest's front: `project` at the middle, closing to zero at the edge of the base with no step; the higher `power`, the more it gathers at the middle."""
import numpy as np

DETAIL_ITERATIONS = 20  # how far the mesh is smoothed to find what is detail (areola, nipple) and what is form
PROFILE = 0.75  # the outline's exponent per unit of power: 1.5 at power 2
DETAIL_FROM, DETAIL_TO = 0.5, 0.95  # in shares of the base: the areola and nipple
FRONT_REACH = 0.09  # m behind the nipple: only the skin in front of this belongs to the breast, or the same x and z on the back would move too
FRONT_FADE = 0.07  # m over which the move fades out towards the back
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
        height = p["project"] * np.maximum(1.0 - r ** 2, 0.0) ** (PROFILE * p["power"])  # zero slope at the edge: a round curve there stood up like a wall and the breast looked square
        t = np.clip((FADE_TO - r) / (FADE_TO - FADE_FROM), 0.0, 1.0)
        behind = np.clip((p["front_y"] - v[:, 1]) / FRONT_FADE, 0.0, 1.0)  # gradually towards the back: a sudden stop left a straight edge down the side of the chest
        fade = t * t * (3 - 2 * t) * behind * behind * (3 - 2 * behind)
        near = np.clip((DETAIL_TO - r) / (DETAIL_TO - DETAIL_FROM), 0.0, 1.0)  # detail only around the nipple: on the slopes, the difference from the smoothed form is the slope itself, and it made bands in the skin
        v[:, 1] = (1 - fade) * v[:, 1] + fade * (wall - height + (v[:, 1] - form) * near * near * (3 - 2 * near))
    return v


def onto_sphere(verts, centre, radius, chest_y, pole=None):
    """A copy of verts with the skin of a flat chest stretched over a sphere in front of it: the disc of skin inside the circle where the sphere meets the chest's plane (y = chest_y) becomes the cap of the sphere in front of that plane, each point at the same fraction of the way from the pole, so the pole is the disc's middle and the rim doesn't move. What the skin stands out of the plane (areola, nipple) stands out of the sphere. pole: the (x, z) of the skin that should land on the sphere's front, when the nipple isn't over the centre; the skin slides there, less and less towards the rim."""
    v = np.asarray(verts, float).copy()
    cx, cy, cz = centre
    theta_rim = np.arccos(np.clip((cy - chest_y) / radius, -1.0, 1.0))
    rim = radius * np.sin(theta_rim)
    dx, dz = v[:, 0] - cx, v[:, 2] - cz
    s = np.hypot(dx, dz)
    m = (s < rim) & (v[:, 1] < chest_y + FRONT_REACH)
    if pole is not None:
        slide = 1.0 - (s[m] / rim) ** 2
        dx[m] -= (pole[0] - cx) * slide
        dz[m] -= (pole[1] - cz) * slide
        s = np.hypot(dx, dz)
    theta = s[m] / rim * theta_rim
    out = radius + np.maximum(chest_y - v[m, 1], 0.0)
    ux, uz = dx[m] / np.maximum(s[m], 1e-9), dz[m] / np.maximum(s[m], 1e-9)
    v[m, 0] = cx + out * np.sin(theta) * ux
    v[m, 2] = cz + out * np.sin(theta) * uz
    v[m, 1] = cy - out * np.cos(theta)
    return v


def footprint(points, p):
    """Which points lie over this breast's base."""
    return (rho(points, p) < 1.0) & (points[:, 1] < p["front_y"])

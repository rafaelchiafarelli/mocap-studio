"""Body skin shapes that muscles and breathing cause, stored as displacement of the vertices they touch."""
import numpy as np
from hmcore import softtissue


def bump(skin, normals, p0, p1, height, radius):
    """Pushes skin outward over a muscle's belly: a smooth bump along p0-p1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    axis = p1 - p0
    length = np.linalg.norm(axis)
    axis = axis / length
    rel = skin - p0
    t = rel @ axis
    d = np.linalg.norm(rel - np.outer(t, axis), axis=1)
    u = np.clip(t / length, 0, 1)
    along = np.sin(np.pi * u) ** 2
    across = np.exp(-(d / radius) ** 2)
    w = along * across
    w[(t < 0) | (t > length)] = 0.0
    return normals * (w * height)[:, None]


def muscle_of(ms, name):
    return next(m for m in ms if m["name"] == name)


def shapes(ind, bones, ms, meta):
    """{name: (vertex ids, displacement)}: breath, abdomen, and the belly of biceps, triceps and deltoid when shortened."""
    skin, tris = ind["skin"], ind["tris"]
    normals = softtissue.vertex_normals(skin, tris)
    out = {}

    def keep(name, disp):
        ids = np.flatnonzero(np.linalg.norm(disp, axis=1) > 1e-4)
        out[name] = (ids, disp[ids])

    rig = ind["rig"]
    # Breathing: the chest moves out with the ribs, the belly with the diaphragm; declared sizes that match breath_check's expansion
    top, low = np.array(rig["spine.004"]["head"]), np.array(rig["spine.002"]["head"])
    mid = (top + low) / 2
    chest = (np.abs(skin[:, 2] - mid[2]) < 0.14) & (np.abs(skin[:, 0]) < 0.20)
    w = np.exp(-((skin[:, 2] - mid[2]) / 0.09) ** 2) * chest
    breath = normals * (w * 0.007)[:, None] + np.array([0, 0, 0.004]) * w[:, None]
    belly_c = np.array(rig["spine.001"]["head"])
    wb = np.exp(-((skin[:, 2] - belly_c[2]) / 0.06) ** 2 - (skin[:, 0] / 0.11) ** 2) * (skin[:, 1] < belly_c[1])
    breath += normals * (wb * 0.008)[:, None]
    keep("breath", breath)
    for side in "LR":
        ua, fa = np.array(rig[f"upper_arm.{side}"]["head"]), np.array(rig[f"upper_arm.{side}"]["tail"])
        for name, height, m in (("biceps", 0.009, f"biceps_brachii_{side}"), ("triceps", 0.004, f"triceps_brachii_{side}")):
            mm = muscle_of(ms, m)
            front = -1.0 if name == "biceps" else 1.0
            d = bump(skin, normals, ua + (fa - ua) * 0.25, ua + (fa - ua) * 0.95, height, 0.035)
            d[(np.sign(skin[:, 1] - (ua[1] + fa[1]) / 2) != np.sign(front))] = 0.0
            keep(f"{name}_{side}", d)
        d = bump(skin, normals, ua + np.array([0, 0, 0.03]), ua + (fa - ua) * 0.42, 0.007, 0.045)
        keep(f"deltoid_{side}", d)
    return out

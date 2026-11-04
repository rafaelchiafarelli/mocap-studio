"""Muscles as spindles between attachment points. Volume is what stays constant: a segment that shortens by s widens by 1/sqrt(s)."""
import json, math
import numpy as np
from hmcore import fit, sources

TISSUE_DENSITY_N_PER_M2 = 60e4  # specific tension about 60 N/cm2, to get a cross-section from Rajagopal's max force; declared


def spindle_profile(u, tendon=0.12):
    """Radius fraction along a muscle, 0 at the tendons and 1 at the belly. u in 0..1."""
    u = np.asarray(u, float)
    x = np.clip((u - tendon) / (1 - 2 * tendon), 0, 1)
    return 0.12 + 0.88 * np.sin(np.pi * x) ** 0.9


def spindle_volume(length, radius, rings=32):
    u = np.linspace(0, 1, rings)
    r = radius * spindle_profile(u)
    return float(np.trapezoid(np.pi * r ** 2, u * length))


def radius_for_volume(length, volume):
    return math.sqrt(volume / spindle_volume(length, 1.0))


def stretched(length, radius, ratio):
    """A segment stretched by ratio, with volume preserved: the rule Blender's Stretch To applies in VOLUME_XZX."""
    return length * ratio, radius / math.sqrt(ratio)


def segment_mesh(p0, p1, r0, r1, rings=6, sides=8, u0=0.0, u1=1.0):
    """A closed frustum chain around p0-p1, with radii from the profile between chain positions u0 and u1."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    axis = p1 - p0
    length = np.linalg.norm(axis)
    if length < 1e-6:
        return None
    axis /= length
    ref = np.array([0, 0, 1.0]) if abs(axis[2]) < 0.9 else np.array([1.0, 0, 0])
    a = np.cross(axis, ref)
    a /= np.linalg.norm(a)
    b = np.cross(axis, a)
    verts, faces = [], []
    for i in range(rings):
        t = i / (rings - 1)
        u = u0 + t * (u1 - u0)
        r = (r0 * (1 - t) + r1 * t) * spindle_profile(u)
        for k in range(sides):
            ang = 2 * math.pi * k / sides
            verts.append(p0 + axis * length * t + r * (math.cos(ang) * a + math.sin(ang) * b))
    for i in range(rings - 1):
        for k in range(sides):
            n = (k + 1) % sides
            faces.append((i * sides + k, i * sides + n, (i + 1) * sides + n, (i + 1) * sides + k))
    faces.append(tuple(range(sides))[::-1])
    faces.append(tuple(range((rings - 1) * sides, rings * sides)))
    return np.array(verts), faces


def mesh_volume(verts, faces):
    verts = np.asarray(verts, float)
    total = 0.0
    for f in faces:
        a = verts[f[0]]
        for i in range(1, len(f) - 1):
            total += np.dot(a, np.cross(verts[f[i]], verts[f[i + 1]])) / 6
    return float(total)


class Resolver:
    """Turns a table landmark into a point on this individual, and says which rig bone carries it."""

    def __init__(self, ind, bones):
        self.ind, self.bones = ind, bones
        skin = ind["skin"]
        head = skin[skin[:, 2] > ind["rig"]["spine.006"]["head"][2]]
        self.scale = (head[:, 0].max() - head[:, 0].min()) / 0.16

    def _sub(self, name, side):
        return name.replace("{s}", side)

    def point(self, lm, side, scaled=True):
        bone = self.ind["rig"][self._sub(lm["rig"], side)]
        h, t = np.array(bone["head"]), np.array(bone["tail"])
        p = h + lm["t"] * (t - h)
        off = np.array(lm["off"], float) * (self.scale if scaled else 1.0)
        if side == "R":
            off[0] = -off[0]
        return p + off

    def snapped(self, lm, side):
        """(point, parent rig bone): on the named bone's surface, or free in the carrying rig bone."""
        p = self.point(lm, side)
        name = self._sub(lm["snap"], side) if lm.get("snap") else None
        if name and name in self.bones:
            v = self.bones[name]["verts"]
            return v[np.argmin(np.linalg.norm(v - p, axis=1))].astype(float), self.bones[name]["parent"]
        return p, self._sub(lm["rig"], side)

    def skin_vertex(self, lm, side):
        p = self.point(lm, side)
        i = int(np.argmin(np.linalg.norm(self.ind["skin"] - p, axis=1)))
        return i, self.ind["skin"][i]


def bilateral(side_entries):
    return [(e, s) for e in side_entries for s in ("L", "R")]


def build_table(ind, bones, table):
    """The muscle list of one individual: per muscle, its chain of points, parents and radii."""
    res = Resolver(ind, bones)
    out = []
    for e, side in bilateral(table["face"]):
        o, parent = res.snapped(e["origin"], side)
        vid, p = res.skin_vertex(e["insertion"], side)
        out.append({"name": f"{e['name']}_{side}", "group": "face", "side": side, "points": [o.tolist(), p.tolist()], "parents": [parent, f"skin:{vid}"], "radius": e["radius"] * res.scale, "contraction": e["contraction"], "patch": e["patch"] * res.scale, "facs": e["facs"], "kind": "linear"})
    for e, side in bilateral(table["sphincters"]):
        ring, _ = res.snapped(e["ring"], side)
        centre = res.point(e["centre"], side)
        vid = int(np.argmin(np.linalg.norm(ind["skin"] - ring, axis=1)))
        out.append({"name": f"{e['name']}_{side}", "group": "face", "side": side, "points": [centre.tolist(), ind["skin"][vid].tolist()], "parents": ["face", f"skin:{vid}"], "radius": 0.002 * res.scale, "contraction": e["contraction"], "patch": e["radius"] * res.scale, "facs": e["facs"], "kind": e["kind"]})
    for key in ("jaw", "tongue", "trunk"):
        for e, side in bilateral(table[key]):
            a, pa = res.snapped(e["origin"], side)
            b, pb = res.snapped(e["insertion"], side)
            out.append({"name": f"{e['name']}_{side}", "group": key, "side": side, "points": [a.tolist(), b.tolist()], "parents": [pa, pb], "radius": e["radius"] * res.scale, "kind": "bone"})
    return out


# ---- Lower limb from the Rajagopal model (MIT): its measured path points, mapped by segment.
BODY_BONE = {"pelvis": "spine", "femur": "thigh", "tibia": "shin", "patella": "shin", "talus": "foot", "calcn": "foot", "toes": "toe"}


def rajagopal_muscles(ind, bones, osim_path, sockets):
    _, muscles = sources.osim_bodies(osim_path)
    joints = sources.osim_joints(osim_path)
    out = []
    rig = ind["rig"]

    def ends(side):
        hip = np.array(sockets[side])
        knee = np.array(rig[f"thigh.{side}"]["tail"])
        ankle = np.array(rig[f"shin.{side}"]["tail"])
        toe = np.array(rig[f"toe.{side}"]["head"])
        return hip, knee, ankle, toe

    raj_hip = sources.opensim_to_model(np.array(joints["femur_r"][1])[None])[0]
    pelvis_span = abs(2 * raj_hip[0])
    my_span = abs(sockets["L"][0] - sockets["R"][0])
    for name, m in muscles.items():
        if name == "default" or not m["points"]:
            continue
        s = name.rsplit("_", 1)[1]
        side = "R" if s == "r" else "L"
        hip, knee, ankle, toe = ends(side)
        hip_key = f"femur_{s}"
        h = np.array(joints[hip_key][1])
        kn = np.array(joints[f"tibia_{s}"][1])
        an = np.array(joints[f"talus_{s}"][1])
        calcn = np.array(joints[f"calcn_{s}"][1])
        to = np.array(joints[f"toes_{s}"][1])
        pts, parents = [], []
        for p in m["points"]:
            body = p["body"].rsplit("_", 1)[0]
            loc = np.array(p["location"])
            if body == "pelvis":
                q = sources.opensim_to_model((loc - h)[None])[0] * (my_span / pelvis_span) + hip
                parent = "spine"
            elif body == "femur":
                q = fit.segment_fit(sources.opensim_to_model(loc[None]), np.zeros(3), sources.opensim_to_model(kn[None])[0], hip, knee)[0]
                parent = f"thigh.{side}"
            elif body in ("tibia", "patella"):
                q = fit.segment_fit(sources.opensim_to_model(loc[None]), np.zeros(3), sources.opensim_to_model(an[None])[0], knee, ankle)[0]
                parent = f"shin.{side}"
            else:
                base = {"talus": np.zeros(3), "calcn": calcn, "toes": calcn + to}[body]
                ref = calcn + to
                q = fit.segment_fit(sources.opensim_to_model((base + loc)[None]), np.zeros(3), sources.opensim_to_model(ref[None])[0], ankle, toe)[0]
                parent = f"toe.{side}" if body == "toes" else f"foot.{side}"
            pts.append(q.tolist())
            parents.append(parent)
        length = sum(np.linalg.norm(np.array(pts[i + 1]) - np.array(pts[i])) for i in range(len(pts) - 1))
        vol = m["max_force"] / TISSUE_DENSITY_N_PER_M2 * m["fiber_length"]
        out.append({"name": name, "group": "leg", "side": side, "points": pts, "parents": parents, "radius": radius_for_volume(length, vol), "volume": vol, "kind": "bone", "source": "rajagopal"})
    return out

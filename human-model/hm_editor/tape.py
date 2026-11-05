"""A tape measure on the skin, in pattern-making terms. No bpy, so it can be tested.
A girth is the convex hull of a section through the mesh, because a real tape bridges hollows. Lengths run between landmarks found on the mesh. Model frame: metres, the body faces -Y, its left is +X, up is +Z."""
from dataclasses import dataclass
import numpy as np

N_BODY = 13380  # MakeHuman's body vertices come first; helpers follow, as in blender/export_blend.py
SCAN_STEP_M = 0.005
NECK_BASE_RATIO = 1.25  # the trunk's girth at the base of the neck, against the neck's thinnest. Declared, checked by eye on the tape's lines
NECK_RATIO = 1.08
ACROMION_SHARE = 0.2
UNDER_BREAST_DROP = 0.025  # a share of stature
UNDER_BREAST = (8507, 1835)  # the lowest vertices the rig's breast bones mainly move, read from a built female model. The mesh's numbering is the same on every character
JOINTS = ("neck", "head", "pelvis", "l-shoulder", "r-shoulder", "l-elbow", "r-elbow", "l-hand", "r-hand", "l-upper-leg", "r-upper-leg", "l-knee", "r-knee", "l-ankle", "r-ankle")


@dataclass(frozen=True)
class Measure:
    key: str
    label: str  # Rafael's trade terms, in Portuguese
    kind: str  # "girth" or "length"
    text: str


MEASURES = (
    Measure("height", "Altura total", "length", "Do chão ao topo da cabeça"),
    Measure("bust", "Busto", "girth", "Volta na altura dos bicos, por cima de tudo"),
    Measure("underbust", "Abaixo do busto", "girth", "Volta logo abaixo do seio"),
    Measure("waist", "Cintura", "girth", "A menor volta do tronco"),
    Measure("hip", "Quadril", "girth", "A maior volta entre a cintura e o gancho"),
    Measure("neck", "Pescoço", "girth", "Volta na base do pescoço"),
    Measure("armhole_depth", "Altura da cava", "length", "Da nuca (C7) até o nível da axila, na vertical"),
    Measure("back_length", "Comprimento de costas", "length", "Da nuca (C7) até a cintura, na vertical"),
    Measure("bust_height", "Altura do busto", "length", "Do ponto do ombro no pescoço até o bico, em linha reta"),
    Measure("bust_span", "Separação do busto", "length", "De bico a bico"),
    Measure("shoulder_width", "Largura de ombros", "length", "De ponta a ponta de ombro"),
    Measure("shoulder", "Ombro", "length", "Do pescoço à ponta do ombro"),
    Measure("hip_height", "Altura do quadril", "length", "Da cintura até a linha do quadril, na vertical"),
    Measure("rise", "Altura do gancho", "length", "Da cintura até o gancho, na vertical"),
    Measure("inseam", "Entrepernas", "length", "Do gancho até o chão, na vertical"),
    Measure("knee_height", "Altura do joelho", "length", "Do joelho até o chão, na vertical"),
    Measure("arm_length", "Comprimento do braço", "length", "Da ponta do ombro ao punho, passando pelo cotovelo"),
    Measure("upper_arm", "Braço", "girth", "Volta na metade entre ombro e cotovelo"),
    Measure("wrist", "Punho", "girth", "A menor volta logo acima da mão"),
    Measure("thigh", "Coxa", "girth", "Volta logo abaixo do gancho"),
    Measure("knee", "Joelho", "girth", "Volta na altura do joelho"),
    Measure("calf", "Panturrilha", "girth", "A maior volta entre joelho e tornozelo"),
    Measure("ankle", "Tornozelo", "girth", "A menor volta logo acima do pé"),
)
MEASURE_KEYS = tuple(m.key for m in MEASURES)
# Which MPFB sliders move each measure, from data/measure_sweep.json. "height" is the height macro. No slider moves the armhole's depth or the shoulder's own length, so those are read only.
DRIVERS = {
    "bust": ("measure-bust-circ-decr-incr",), "underbust": ("measure-underbust-circ-decr-incr",), "waist": ("measure-waist-circ-decr-incr",), "hip": ("measure-hips-circ-decr-incr",), "neck": ("measure-neck-circ-decr-incr",),
    "back_length": ("measure-napetowaist-dist-decr-incr",), "bust_height": ("breast-trans-down-up",), "bust_span": ("breast-dist-decr-incr",), "shoulder_width": ("measure-shoulder-dist-decr-incr",), "hip_height": ("measure-waisttohip-dist-decr-incr",),
    "rise": ("hip-scale-vert-decr-incr",), "inseam": ("measure-upperleg-height-decr-incr",), "knee_height": ("measure-lowerleg-height-decr-incr",), "arm_length": ("measure-upperarm-length-decr-incr", "measure-lowerarm-length-decr-incr"),
    "upper_arm": ("measure-upperarm-circ-decr-incr",), "wrist": ("measure-wrist-circ-decr-incr",), "thigh": ("measure-thigh-circ-decr-incr",), "knee": ("measure-knee-circ-decr-incr",), "calf": ("measure-calf-circ-decr-incr",), "ankle": ("measure-ankle-circ-decr-incr",),
}
TOLERANCE_M = 0.002
UP = np.array((0.0, 0.0, 1.0))


class Topology:
    """What stays the same on every MPFB character: edges, faces and landmark vertices, built once per mesh."""

    def __init__(self, polygons, groups):
        """polygons: vertex lists, body and helpers. groups: {name: vertex indices}."""
        body = [p for p in polygons if max(p) < N_BODY]
        self.face_edges = np.full((len(body), 4), -1, dtype=np.int32)
        index = {}
        for i, p in enumerate(body):
            for k, a in enumerate(p[:4]):
                b = p[(k + 1) % len(p)]
                edge = (a, b) if a < b else (b, a)
                self.face_edges[i, k] = index.setdefault(edge, len(index))
        self.edges = np.array(list(index), dtype=np.int32)
        self.joints = {j: np.asarray(groups[f"joint-{j}"], dtype=np.int32) for j in JOINTS}
        self.nipple = np.asarray([v for v in groups["nippleTip"] if v < N_BODY], dtype=np.int32)


def section(topology, verts, point, normal):
    """The closed loops where a plane cuts the skin, each as an array of points."""
    v = verts[:N_BODY]
    d = (v - point) @ normal
    e0, e1 = topology.edges[:, 0], topology.edges[:, 1]
    crossed = np.flatnonzero((d[e0] > 0) != (d[e1] > 0))
    if not len(crossed):
        return []
    t = (d[e0[crossed]] / (d[e0[crossed]] - d[e1[crossed]]))[:, None]
    points = v[e0[crossed]] * (1 - t) + v[e1[crossed]] * t
    where = np.full(len(topology.edges) + 1, -1, dtype=np.int32)  # the last slot answers face_edges' -1 padding
    where[crossed] = np.arange(len(crossed))
    hits = where[topology.face_edges]
    parent = list(range(len(crossed)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for row in hits[(hits >= 0).sum(1) >= 2]:
        ids = row[row >= 0]
        for other in ids[1:]:
            parent[find(int(ids[0]))] = find(int(other))
    roots = np.array([find(i) for i in range(len(crossed))])
    return [points[roots == r] for r in np.unique(roots)]


def hull_loop(points, normal):
    """The closed path a tape pulled around these points takes, in their plane."""
    u = np.cross(normal, (1.0, 0.0, 0.0) if abs(normal[0]) < 0.9 else (0.0, 1.0, 0.0))
    u /= np.linalg.norm(u)
    w = np.cross(normal, u)
    flat = np.column_stack([points @ u, points @ w])
    order = np.lexsort((flat[:, 1], flat[:, 0]))

    def half(indices):
        out = []
        for i in indices:
            while len(out) >= 2 and (flat[out[-1], 0] - flat[out[-2], 0]) * (flat[i, 1] - flat[out[-2], 1]) - (flat[out[-1], 1] - flat[out[-2], 1]) * (flat[i, 0] - flat[out[-2], 0]) <= 0:
                out.pop()
            out.append(i)
        return out[:-1]

    return points[half(order) + half(order[::-1])]


def length_of(loop):
    return float(np.linalg.norm(loop - np.roll(loop, 1, axis=0), axis=1).sum()) if len(loop) >= 3 else 0.0


def _horizontal(topology, verts, z):
    return section(topology, verts, np.array((0.0, 0.0, z)), UP)


def _torso(loops):
    """The loop around the body's midline, not an arm or a hand."""
    return min(loops, key=lambda p: abs(p[:, 0].mean()) - len(p) * 1e-6) if loops else None


def _girth_loop(topology, verts, z):
    torso = _torso(_horizontal(topology, verts, z))
    return hull_loop(torso, UP) if torso is not None else np.empty((0, 3))


def _nearest_loop(loops, point):
    return min(loops, key=lambda p: np.linalg.norm(p.mean(0) - point)) if loops else None


def _limb_loop(topology, verts, a, b, fraction):
    """A girth across the limb from joint a to joint b, square to it, as a tape sits on an arm that isn't vertical."""
    axis = (b - a) / np.linalg.norm(b - a)
    point = a + (b - a) * fraction
    loop = _nearest_loop(section(topology, verts, point, axis), point)
    return hull_loop(loop, axis) if loop is not None else np.empty((0, 3))


def _scan(start, stop, step=SCAN_STEP_M):
    return np.arange(start, stop, step if stop > start else -step)


def _armpit(topology, verts, nipple_z, top):
    """The first level above the bust where the arms join the trunk."""
    for z in _scan(nipple_z, top):
        if len(_horizontal(topology, verts, z)) == 1:
            return float(z)
    return float(top)


def _crotch(topology, verts, hip_joint_z, height):
    """The level where the two legs become one trunk, going down from the hip joints."""
    for z in _scan(hip_joint_z + 0.05 * height, hip_joint_z - 0.15 * height):
        loops = [p for p in _horizontal(topology, verts, z) if abs(p[:, 0].mean()) < 0.5 * height * 0.2]
        if len(loops) >= 2:
            return float(z)
    return float(hip_joint_z - 0.05 * height)


def _underbust(verts, height):
    """Under the breast, from fixed vertices of the mesh. They follow the shape smoothly, where looking for a crease jumps between levels when the crease is shallow. The drop keeps the tape off the breast: at the vertices' own level, 85% of a bust change still reached it."""
    return float(verts[list(UNDER_BREAST), 2].mean()) - UNDER_BREAST_DROP * height


def _neck_levels(topology, verts, joint):
    """Where the trunk ends and the neck begins, going up from the shoulders: the first level whose girth is near the neck's thinnest, for the base and for the neck itself."""
    levels = _scan(float(joint["l-shoulder"][2]), float(joint["head"][2]))
    girths = np.array([length_of(_girth_loop(topology, verts, z)) for z in levels])
    thinnest = girths[girths > 0].min()
    base = next(i for i, g in enumerate(girths) if 0 < g <= thinnest * NECK_BASE_RATIO)
    neck = next(i for i, g in enumerate(girths) if i >= base and 0 < g <= thinnest * NECK_RATIO)
    return float(levels[base]), float(levels[neck])


def _c7(v, base_z):
    """The nape: the back of the midline at the base of the neck."""
    near = v[(np.abs(v[:, 0]) < 0.015) & (np.abs(v[:, 2] - base_z) < 0.012)]
    return near[np.argmax(near[:, 1])]


def _acromion(v, shoulder, elbow):
    """The shoulder's tip: the top of the skin a set share along the arm from the shoulder joint, which sits inside the tip on MPFB's rig.
    ACROMION_SHARE gives the neutral bodies ANSUR II's breadth for their height. Looking for a change of slope instead wasn't stable on thick arms."""
    x = shoulder[0] + ACROMION_SHARE * (elbow[0] - shoulder[0])
    near = v[(np.abs(v[:, 0] - x) < 0.01) & (np.abs(v[:, 1] - shoulder[1]) < 0.03)]
    return near[np.argmax(near[:, 2])]


def landmarks(topology, verts):
    """The levels and points everything is measured from."""
    v = verts[:N_BODY]
    floor = float(v[:, 2].min())
    height = float(v[:, 2].max()) - floor
    joint = {name: verts[idx].mean(0) for name, idx in topology.joints.items()}
    nipples = v[topology.nipple]
    nipple_l, nipple_r = nipples[nipples[:, 0] > 0].mean(0), nipples[nipples[:, 0] < 0].mean(0)
    nipple_z = float((nipple_l[2] + nipple_r[2]) / 2)
    armpit = _armpit(topology, verts, nipple_z, float(joint["l-shoulder"][2]) + 0.02)
    base_z, neck_z = _neck_levels(topology, verts, joint)
    c7 = _c7(v, base_z)
    neck_loop = _girth_loop(topology, verts, neck_z)
    base_loop = _girth_loop(topology, verts, base_z)
    neck_point_l = base_loop[np.argmax(base_loop[:, 0])]
    hip_joint_z = float((joint["l-upper-leg"][2] + joint["r-upper-leg"][2]) / 2)
    crotch = _crotch(topology, verts, hip_joint_z, height)
    underbust = _underbust(verts, height)
    levels = _scan(crotch + 0.02 * height, nipple_z - 0.02 * height)
    girths = np.array([length_of(_girth_loop(topology, verts, z)) for z in levels])
    upper = levels > hip_joint_z + 0.04 * height
    waist = float(levels[upper][np.argmin(girths[upper])])
    # The fullest seat, where a tape goes. The biggest girth would be lower, because legs spread in the rest pose stretch the tape.
    lower = levels[(levels < waist) & (levels > crotch + 0.02 * height)]
    hip = float(lower[np.argmax([_girth_loop(topology, verts, z)[:, 1].max() for z in lower])])
    return {"floor": floor, "height": height, "joint": joint, "nipple_l": nipple_l, "nipple_r": nipple_r, "nipple_z": nipple_z, "c7": c7, "neck_point_l": neck_point_l, "neck_loop": neck_loop,
            "acromion_l": _acromion(v, joint["l-shoulder"], joint["l-elbow"]), "acromion_r": _acromion(v, joint["r-shoulder"], joint["r-elbow"]), "armpit": armpit, "crotch": crotch, "underbust": underbust, "waist": waist, "hip": hip}


def _pick_limb(topology, verts, a, b, fractions, pick):
    loops = [_limb_loop(topology, verts, a, b, f) for f in fractions]
    return pick(loops, key=length_of)


def _vertical(point, z):
    return np.array((point, (point[0], point[1], z)))


def _lines(topology, verts):
    """Each measure as the path the tape takes: a closed loop for a girth, an open line for a length. One side stands for both, as a pattern is drafted from one side. Left is +X."""
    m = landmarks(topology, verts)
    j = m["joint"]
    c7, floor = m["c7"], m["floor"]
    side = (0.30 * m["height"], float(j["l-upper-leg"][1]))  # a line beside the body, so the height can be seen
    thigh_loops = [p for p in _horizontal(topology, verts, m["crotch"] - 0.02 * m["height"]) if p[:, 0].mean() > 0]
    thigh = _nearest_loop(thigh_loops, j["l-upper-leg"])
    wrist_at, calf_at, ankle_at = np.linspace(0.70, 0.98, 8), np.linspace(0.20, 0.55, 8), np.linspace(0.75, 0.95, 5)
    girths = {
        "bust": _girth_loop(topology, verts, m["nipple_z"]),
        "underbust": _girth_loop(topology, verts, m["underbust"]),
        "waist": _girth_loop(topology, verts, m["waist"]),
        "hip": _girth_loop(topology, verts, m["hip"]),
        "neck": m["neck_loop"],
        "upper_arm": _limb_loop(topology, verts, j["l-shoulder"], j["l-elbow"], 0.5),
        "wrist": _pick_limb(topology, verts, j["l-elbow"], j["l-hand"], wrist_at, min),
        "thigh": hull_loop(thigh, UP) if thigh is not None else np.empty((0, 3)),
        "knee": _limb_loop(topology, verts, j["l-upper-leg"], j["l-knee"], 1.0),
        "calf": _pick_limb(topology, verts, j["l-knee"], j["l-ankle"], calf_at, max),
        "ankle": _pick_limb(topology, verts, j["l-knee"], j["l-ankle"], ankle_at, min),
    }
    lengths = {
        "height": _vertical((side[0], side[1], floor), floor + m["height"]),
        "armhole_depth": _vertical(c7, m["armpit"]),
        "back_length": _vertical((c7[0] + 0.012, c7[1], c7[2]), m["waist"]),
        "bust_height": np.array((m["neck_point_l"], m["nipple_l"])),
        "bust_span": np.array((m["nipple_l"], m["nipple_r"])),
        "shoulder_width": np.array((m["acromion_l"], m["acromion_r"])),
        "shoulder": np.array((m["neck_point_l"], m["acromion_l"])),
        "hip_height": _vertical((c7[0] - 0.012, c7[1], m["waist"]), m["hip"]),
        "rise": _vertical((0.0, float(j["l-upper-leg"][1]), m["waist"]), m["crotch"]),
        "inseam": _vertical((j["l-knee"][0] * 0.3, j["l-knee"][1], m["crotch"]), floor),
        "knee_height": _vertical((j["l-knee"][0], j["l-knee"][1] - 0.12, float(j["l-knee"][2])), floor),
        "arm_length": np.array((m["acromion_l"], j["l-elbow"], j["l-hand"])),
    }
    return girths, lengths, m


def measure(topology, verts):
    """Every measure in metres, the path of each, and the landmarks they came from."""
    girths, lengths, m = _lines(topology, verts)
    values = {k: length_of(loop) for k, loop in girths.items()}
    values.update({k: float(np.linalg.norm(np.diff(line, axis=0), axis=1).sum()) for k, line in lengths.items()})
    return values, {**girths, **lengths}, m


def solve(read, write, start, target, lo, hi, tolerance=TOLERANCE_M, steps=8):
    """Moves one control until read() gives target. Returns (reached, at_limit). Sliders aren't linear, so each step uses the slope just measured."""
    x, value = start, read()
    if abs(value - target) <= tolerance:
        return value, False
    x_new = x + (0.1 if x + 0.1 <= hi else -0.1)
    for _ in range(steps):
        write(x_new)
        new = read()
        if abs(new - target) <= tolerance:
            return new, False
        slope = (new - value) / (x_new - x) if x_new != x else 0.0
        x, value = x_new, new
        if abs(slope) < 1e-5:
            break  # this control doesn't move this measure
        x_new = min(max(x + (target - value) / slope, lo), hi)
        if x_new == x:
            return value, True
    return value, x in (lo, hi) or abs(value - target) > tolerance

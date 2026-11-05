"""A liquid-filled sphere that lifts a 1 kg box, in Blender's Cloth physics. Args: out.blend out.json [NAME=value overrides the constants below]. Saves the file with the simulation baked."""
import json, math, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

RADIUS = 0.05  # m
LIQUID = 1.0  # kg/L
LOAD = 1.0  # kg
BOX = 0.05  # m, side
CAP = 0.02  # m, radius of the patch glued to each box
SHORTEN = 0.6  # distance between the poles at full contraction, share of the diameter
SUBDIV = 3  # icosphere
LATTICE = 11  # points per side of the block that carries the load's mass
TENSION, BENDING, DAMPING, AIR, PRESSURE, GRAVITY = 200.0, 0.5, 5.0, 0.1, 50.0, 9.81
PULL, HOLD, RELEASE, END = (40, 80), (80, 130), (130, 134), 230  # frames, 24 fps


def icosphere(n):
    t = (1 + 5 ** 0.5) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    v = [np.array(p, float) / np.linalg.norm(p) for p in v]
    for _ in range(n):
        mid, out = {}, []
        def m(a, b):
            k = (min(a, b), max(a, b))
            if k not in mid:
                p = v[a] + v[b]
                v.append(p / np.linalg.norm(p))
                mid[k] = len(v) - 1
            return mid[k]
        for a, b, c in f:
            ab, bc, ca = m(a, b), m(b, c), m(c, a)
            out += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        f = out
    v = np.array(v)
    # a pole on Z: turn the vertex (0, 1, t) onto +Z
    a = v[5]
    s = np.cross(a, [0, 0, 1])
    c = a[2]
    K = np.array([[0, -s[2], s[1]], [s[2], 0, -s[0]], [-s[1], s[0], 0]])
    return v @ (np.eye(3) + K + K @ K / (1 + c)).T, np.array(f)


def enclosed(v, f):
    return abs(np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum()) / 6


def contracted(rest):
    """The rest shape at full activation: a flattened sphere of the same volume, with both caps kept as they were and the top one in place."""
    s = SHORTEN
    wide = 1 / math.sqrt(s)
    r = np.linalg.norm(rest[:, :2], axis=1)
    near = np.clip((r - CAP) / CAP, 0, 1)
    near = near * near * (3 - 2 * near)  # 0 on the caps, 1 away from them
    centre = np.array([0, 0, -RADIUS * s])  # keeps the top pole at z=0
    shape = rest + np.array([0, 0, RADIUS])
    shape = shape * np.array([wide, wide, s]) + centre
    top_cap = rest
    bottom_cap = rest + np.array([0, 0, 2 * RADIUS * (1 - s)])
    cap = np.where(rest[:, [2]] > -RADIUS, top_cap, bottom_cap)
    return cap + (shape - cap) * near[:, None]


def build():
    hb.clear_scene()
    col = hb.collection("muscle")
    unit, faces = icosphere(SUBDIV)
    sphere = unit * RADIUS - np.array([0, 0, RADIUS])  # top pole at z=0, centre below it
    n_s = len(sphere)
    # the load: a stiff block of points, because Cloth has one mass per vertex, so mass goes by count
    volume0 = enclosed(sphere, faces)
    vertex_mass = LOAD / LATTICE ** 3  # the box is exact; the liquid gets what the vertex count gives
    grid = np.linspace(-BOX / 2, BOX / 2, LATTICE)
    gx, gy, gz = np.meshgrid(grid, grid, grid, indexing="ij")
    bottom = -2 * RADIUS - BOX / 2
    block = np.c_[gx.ravel(), gy.ravel(), gz.ravel() + bottom]
    ids = np.arange(LATTICE ** 3).reshape(LATTICE, LATTICE, LATTICE) + n_s
    edges = []
    for d in [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1), (1, -1, 0), (1, 0, -1), (0, 1, -1)]:
        for i in range(LATTICE):
            for j in range(LATTICE):
                for k in range(LATTICE):
                    a, b, c = i + d[0], j + d[1], k + d[2]
                    if 0 <= a < LATTICE and 0 <= b < LATTICE and 0 <= c < LATTICE:
                        edges.append((ids[i, j, k], ids[a, b, c]))
    # glue the bottom cap to the block's top layer
    cap_bottom = np.flatnonzero((np.linalg.norm(sphere[:, :2], axis=1) < CAP) & (sphere[:, 2] < -RADIUS))
    layer = ids[:, :, -1].ravel()
    for c in cap_bottom:
        d = np.linalg.norm(block[layer - n_s][:, :2] - sphere[c, :2], axis=1)
        for t in layer[np.argsort(d)[:4]]:
            edges.append((int(c), int(t)))
    verts = np.r_[sphere, block]
    me = bpy.data.meshes.new("muscle")
    me.from_pydata(verts.tolist(), [tuple(map(int, e)) for e in edges], faces.tolist())
    me.update()
    ob = bpy.data.objects.new("muscle", me)
    col.objects.link(ob)
    # the shape the muscle wants when active
    ob.shape_key_add(name="rest")
    key = ob.shape_key_add(name="contracted")
    shape = contracted(sphere)
    lift = 2 * RADIUS * (1 - SHORTEN)
    co = np.r_[shape, block + [0, 0, lift]]
    key.data.foreach_set("co", co.ravel())
    key.value = 0
    for frame, value in [(1, 0), (PULL[0], 0), (PULL[1], 1), (HOLD[1], 1), (RELEASE[0], 1), (RELEASE[1], 0)]:
        key.value = value
        key.keyframe_insert("value", frame=frame)
    # groups
    pin = ob.vertex_groups.new(name="pin")
    top_cap = np.flatnonzero((np.linalg.norm(sphere[:, :2], axis=1) < CAP) & (sphere[:, 2] > -RADIUS))
    pin.add(top_cap.tolist(), 1.0, "REPLACE")
    press = ob.vertex_groups.new(name="liquid")
    press.add(list(range(n_s)), 1.0, "REPLACE")
    # physics
    mod = ob.modifiers.new("cloth", "CLOTH")
    s = mod.settings
    s.quality = 20
    s.mass = vertex_mass
    s.time_scale = 1.0
    s.tension_stiffness = TENSION
    s.compression_stiffness = TENSION
    s.shear_stiffness = TENSION / 4
    s.bending_stiffness = BENDING
    s.tension_damping = DAMPING
    s.compression_damping = DAMPING
    s.shear_damping = DAMPING
    s.air_damping = AIR
    s.vertex_group_mass = "pin"
    s.pin_stiffness = 1.0
    s.use_dynamic_mesh = True
    s.use_pressure = True
    s.uniform_pressure_force = 0.0
    s.use_pressure_volume = True
    s.target_volume = volume0
    s.pressure_factor = PRESSURE
    s.fluid_density = LIQUID
    s.vertex_group_pressure = "liquid"
    ob.modifiers["cloth"].collision_settings.use_collision = False
    pc = ob.modifiers["cloth"].point_cache
    pc.frame_start, pc.frame_end = 1, END
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, END
    scene.render.fps = 24
    scene.gravity = (0, 0, -GRAVITY)
    return ob, faces, n_s, volume0, top_cap, ids


def run(ob, faces, n_s, volume0, ids):
    scene = bpy.context.scene
    table = []
    centre = ids[LATTICE // 2, LATTICE // 2, LATTICE // 2]
    for f in range(1, END + 1):
        scene.frame_set(f)
        v = hb.evaluated_verts(ob)
        s = v[:n_s]
        table.append(dict(frame=f, volume=enclosed(s, faces) / volume0, box_z=float(v[centre, 2]), height=float(s[:, 2].max() - s[:, 2].min()), width=float(s[:, 0].max() - s[:, 0].min()), key=ob.data.shape_keys.key_blocks["contracted"].value))
    return table


if __name__ == "__main__":
    a = hb.args()
    for kv in a[2:]:
        k, x = kv.split("=")
        globals()[k] = float(x)
    ob, faces, n_s, volume0, top_cap, ids = build()
    m = ob.modifiers["cloth"].settings.mass
    print("load kg %.3f, sphere kg %.3f (a full liquid would be %.3f)" % (m * LATTICE ** 3, m * n_s, volume0 * 1000 * LIQUID))
    table = run(ob, faces, n_s, volume0, ids)
    json.dump(table, open(a[1], "w"))
    z = np.array([t["box_z"] for t in table])
    vol = np.array([t["volume"] for t in table])
    print("box_z start %.4f settled %.4f top %.4f lowest_after %.4f released %.4f" % (z[0], z[PULL[0] - 1], z[:HOLD[1]].max(), z[RELEASE[0]:].min(), z[-1]))
    print("volume min %.3f max %.3f" % (vol.min(), vol.max()))
    bpy.ops.wm.save_as_mainfile(filepath=a[0])

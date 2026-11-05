"""A liquid-filled sphere that lifts a 1 kg box: our own solver, run in Blender's Python and stored in the file as shape keys. Args: out.blend out.json [NAME=value overrides the constants below]. Blender's Cloth couldn't do this: muscle_sphere_cloth.py."""
import json, math, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
from muscle_sphere_cloth import icosphere, enclosed

RADIUS = 0.05  # m
LIQUID = 1000.0  # kg/m3
LOAD = 1.0  # kg
GRAVITY = 9.81  # m/s2
BOX = 0.05  # m, side
CAP = 0.02  # m, radius of the flat patch glued to each box
SUBDIV = 3.0  # icosphere
FIBRE = 8000.0  # N/m, membrane stiffness along the fibres (top to bottom)
HOOP = 150.0  # N/m, membrane stiffness across them
SHORTEN = 0.4  # how much the fibres' rest length shrinks at full activation
SLACK = 0.1  # share of the stiffness left when an edge is compressed: a membrane buckles
VISCOSITY = 0.12  # N s/m between neighbouring points: the liquid's and the membrane's internal friction
DAMPER = 20.0  # N s/m on the box: the tissue's internal friction, top to bottom. Without it the box bounces for seconds at about 6 Hz; viscosity above barely reaches that motion
CONTACT = 4000.0  # N/m, the sphere can't enter a box
DT = 1e-4  # s
SETTLE = 1.0  # s, off camera, with the load hanging, before frame 1
FPS = 24.0
PULL, RELEASE, END = (40.0, 80.0), (130.0, 134.0), 288.0  # frames


def activation(frame):
    def smooth(t):
        t = min(max(t, 0.0), 1.0)
        return t * t * (3 - 2 * t)
    return smooth((frame - PULL[0]) / (PULL[1] - PULL[0])) * (1 - smooth((frame - RELEASE[0]) / (RELEASE[1] - RELEASE[0])))


def volume_gradient(x, f):
    """Each point's share of the outward area vector / 3: moving a point by d changes the volume by g.d."""
    c = np.cross(x[f[:, 1]], x[f[:, 2]]) / 6
    a, b, d = f[:, 0], f[:, 1], f[:, 2]
    return gather(np.r_[a, b, d], np.r_[c, np.cross(x[d], x[a]) / 6, np.cross(x[a], x[b]) / 6], len(x))


def gather(index, values, n):
    """Sums vectors per point. np.add.at took most of the running time."""
    return np.stack([np.bincount(index, values[:, k], n) for k in range(3)], 1)


def simulate():
    unit, faces = icosphere(int(SUBDIV))
    x = unit * RADIUS - np.array([0, 0, RADIUS])  # top pole at z=0
    if enclosed(x, faces) and np.einsum("ij,ij->i", x[faces[:, 0]] + [0, 0, RADIUS], np.cross(x[faces[:, 1]] - x[faces[:, 0]], x[faces[:, 2]] - x[faces[:, 0]])).sum() < 0:
        faces = faces[:, ::-1]
    r = np.linalg.norm(x[:, :2], axis=1)
    top = (r < CAP) & (x[:, 2] > -RADIUS)
    bot = (r < CAP) & (x[:, 2] < -RADIUS)
    x[top, 2] = 0.0
    x[bot, 2] = -2 * RADIUS
    free = ~(top | bot)
    n = len(x)
    volume0 = enclosed(x, faces)
    mass = volume0 * LIQUID / free.sum()  # the liquid's inertia, on the free points
    edges = np.unique(np.sort(np.r_[faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]], axis=1), axis=0)
    i, j = edges[:, 0], edges[:, 1]
    rest = np.linalg.norm(x[i] - x[j], axis=1)
    # how much each edge runs along a fibre: fibres are the sphere's meridians
    centre = np.array([0, 0, -RADIUS])
    mid = (x[i] + x[j]) / 2 - centre
    east = np.cross([0, 0, 1.0], mid)
    meridian = np.cross(mid, east)
    meridian /= np.linalg.norm(meridian, axis=1, keepdims=True) + 1e-12
    along = (((x[i] - x[j]) * meridian).sum(1) / rest) ** 2
    stiff = HOOP + (FIBRE - HOOP) * along
    shrink = SHORTEN * along

    v = np.zeros_like(x)
    box0 = np.array([0, 0, -2 * RADIUS - BOX / 2])
    box, box_v = box0.copy(), np.zeros(3)
    bot0 = x[bot].copy()
    footprint = BOX / 2
    weight = np.array([0, 0, -LOAD * GRAVITY])
    both = np.r_[i, j]
    pressure = 0.0

    def step(a, drag):
        nonlocal x, v, box, box_v, pressure
        d = x[j] - x[i]
        length = np.sqrt((d * d).sum(1)) + 1e-12
        u = d / length[:, None]
        stretch = length - rest * (1 - a * shrink)
        force = stiff * np.where(stretch > 0, stretch, SLACK * stretch)
        fv = force[:, None] * u + VISCOSITY * (v[j] - v[i])
        F = gather(both, np.r_[fv, -fv], n)
        g = volume_gradient(x, faces)
        F += (LIQUID * GRAVITY * -x[:, [2]]) * g  # the liquid's weight, as hydrostatic pressure on the wall
        # the boxes' faces
        inside = free & (np.abs(x[:, 0]) < footprint) & (np.abs(x[:, 1]) < footprint)
        over = inside & (x[:, 2] > 0)
        F[over, 2] -= CONTACT * x[over, 2]
        plane = box[2] + BOX / 2
        under = inside & (x[:, 2] < plane)
        push = CONTACT * (plane - x[under, 2])
        F[under, 2] += push
        box_F = weight + F[bot].sum(0) - np.array([0, 0, push.sum()]) - DAMPER * box_v
        v[free] += DT * (F[free] / mass - drag * v[free])
        box_v = box_v + DT * (box_F / LOAD - drag * box_v)
        # the liquid can't compress: one pressure, whatever it takes, on velocities and then positions
        for _ in (0, 1):
            g = volume_gradient(x, faces)
            Gb = g[bot].sum(0)
            den = (g[free] * g[free]).sum() / mass + Gb @ Gb / LOAD
            if _ == 0:
                lam = -((v[free] * g[free]).sum() + box_v @ Gb) / den
                v[free] += lam * g[free] / mass
                box_v = box_v + lam * Gb / LOAD
                pressure = lam / DT
                x[free] += DT * v[free]
                box = box + DT * box_v
                x[bot] = bot0 + (box - box0)
            else:
                lam = (volume0 - signed(x)) / den
                x[free] += lam * g[free] / mass
                box = box + lam * Gb / LOAD
                x[bot] = bot0 + (box - box0)

    def signed(p):
        return np.einsum("ij,ij->i", p[faces[:, 0]], np.cross(p[faces[:, 1]], p[faces[:, 2]])).sum() / 6

    for _ in range(int(SETTLE / DT)):
        step(0.0, 25.0)  # off camera, heavily damped, to the resting shape under the load
    v[:] = 0
    box_v = np.zeros(3)
    per_frame = int(round(1 / FPS / DT))
    positions, boxes, table = [], [], []
    start_z = box[2]
    for frame in range(1, int(END) + 1):
        for s in range(per_frame):
            step(activation(frame + s / per_frame), 0.0)
        assert np.isfinite(x).all(), f"blew up at frame {frame}"
        positions.append(x.copy())
        boxes.append(box.copy())
        table.append(dict(frame=frame, activation=activation(frame), volume=signed(x) / volume0, box_z=float(box[2]), lift=float(box[2] - start_z), pressure_pa=float(pressure), height=float(x[:, 2].max() - x[:, 2].min()), width=float(x[:, 0].max() - x[:, 0].min())))
    return positions, boxes, faces, table


def key_shapes(ob, positions):
    ob.shape_key_add(name="basis")
    ob.data.shape_keys.use_relative = False
    for k, p in enumerate(positions):
        key = ob.shape_key_add(name=f"f{k + 1:04d}")
        key.interpolation = "KEY_LINEAR"
        key.data.foreach_set("co", p.ravel())
    keys = ob.data.shape_keys
    blocks = keys.key_blocks
    for k in range(len(positions)):
        keys.eval_time = blocks[k + 1].frame
        keys.keyframe_insert("eval_time", frame=k + 1)


def build(positions, boxes, faces):
    hb.clear_scene()
    col = hb.collection("muscle")
    ob = hb.mesh_object("muscle", positions[0], faces, col, material=hb.material("muscle_red", (0.62, 0.11, 0.09), roughness=0.35))
    for p in ob.data.polygons:
        p.use_smooth = True
    key_shapes(ob, positions)
    ob.modifiers.new("smooth", "SUBSURF").levels = 1  # looks only: the simulation is on the coarse mesh
    ob.modifiers["smooth"].render_levels = 2
    b = BOX / 2
    cube_v = [(x, y, z) for x in (-b, b) for y in (-b, b) for z in (-b, b)]
    cube_f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    steel = hb.material("box_steel", (0.32, 0.34, 0.37), roughness=0.4)
    top = hb.mesh_object("box_top_fixed", cube_v, cube_f, col, material=steel)
    top.location = (0, 0, b)
    low = hb.mesh_object("box_bottom_1kg", cube_v, cube_f, col, material=steel)
    for k, p in enumerate(boxes):
        low.location = p
        low.keyframe_insert("location", frame=k + 1)
    # marks the bottom box's top face at frame 1, to read the lift against
    z = boxes[0][2] + b
    mark = hb.mesh_object("mark_start_height", [(0.075, -0.0015, z - 0.0005), (0.11, -0.0015, z - 0.0005), (0.11, 0.0015, z - 0.0005), (0.075, 0.0015, z - 0.0005), (0.075, -0.0015, z + 0.0005), (0.11, -0.0015, z + 0.0005), (0.11, 0.0015, z + 0.0005), (0.075, 0.0015, z + 0.0005)], [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)], col, material=hb.material("mark", (0.05, 0.05, 0.05)))
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, int(END)
    scene.render.fps = int(FPS)
    scene.gravity = (0, 0, -GRAVITY)
    hb.setup_render((800, 800), 16)
    scene.camera = hb.camera_look("camera", (0, -0.62, -0.06), (0, 0, -0.06), 50)
    return ob


if __name__ == "__main__":
    a = hb.args()
    for kv in a[2:]:
        k, x = kv.split("=")
        globals()[k] = float(x)
    positions, boxes, faces, table = simulate()
    json.dump(table, open(a[1], "w"))
    build(positions, boxes, faces)
    bpy.ops.wm.save_as_mainfile(filepath=a[0])
    z = np.array([t["lift"] for t in table])
    vol = np.array([t["volume"] for t in table])
    p = np.array([t["pressure_pa"] for t in table])
    print("start height %.1f mm width %.1f mm" % (table[0]["height"] * 1000, table[0]["width"] * 1000))
    print("lift max %.1f mm, when held %.1f mm, lowest after release %.1f mm, at end %.1f mm" % (z.max() * 1000, z[int(RELEASE[0]) - 2] * 1000, z[int(RELEASE[0]):].min() * 1000, z[-1] * 1000))
    print("held height %.1f mm width %.1f mm" % (table[int(RELEASE[0]) - 2]["height"] * 1000, table[int(RELEASE[0]) - 2]["width"] * 1000))
    print("volume min %.6f max %.6f" % (vol.min(), vol.max()))
    print("pressure start %.0f held %.0f max %.0f Pa" % (p[0], p[int(RELEASE[0]) - 2], p.max()))

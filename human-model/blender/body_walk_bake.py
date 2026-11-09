"""The walking body (lower or whole) of tools/body_walk.py as a .blend that plays without simulating, and frames for two videos.
Args: WALK.npz LAYERS.npz BONES.npz WALK_DUMP.npz OUT.blend FRAMES_DIR [NICKNAME]
In the file: the simulated skin and, 80 cm behind it, the current model's skin on the same step (collection walk_compare);
the back half in section with the bones (collection walk_inside). Every frame is a shape key, keyed on at its own frame, as thigh_bake.py does.
Renders FRAMES_DIR/compare/####.png (from the side, both skins) and FRAMES_DIR/inside/####.png (the section from the front). FRAMES_DIR - makes the file only.
With NICKNAME, a text above each of the two models (in their own collections, so it switches off with them) follows the pelvis through the walk."""
import math, os, sys
import bpy
import numpy as np
from mathutils import Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

COLORS = {"bone": (0.9, 0.86, 0.75), "muscle": (0.6, 0.12, 0.1), "fat": (0.95, 0.8, 0.35), "skin": (0.85, 0.65, 0.55),
          "cavity": (0.45, 0.55, 0.8), "fat_deep": (0.85, 0.65, 0.25), "current": (0.55, 0.65, 0.85)}
BESIDE = np.array([0.0, 0.8, 0.0])  # m: the current model's skin, 80 cm behind ours along the walk, so the side view shows both (beside, it hid ours: leg_walk v2)
N_BODY = 13380  # as in export_blend.py
FOOT_BONES = ("talus", "calcaneus", "navicular", "cuboid", "cuneiform", "metatarsal", "phalanx")
FOOT_TOP = 0.25  # m: skin below this that isn't simulated is the feet's
LABEL_ABOVE = 0.18  # m over the head's top
LABEL_SIZE = 0.14  # m, the letters' height


def animated(name, frames, faces, collection, material, smooth=False):
    """A mesh whose vertices take frames[i] at frame i + 1, one shape key per frame, as thigh_bake.py's (which can't be imported: it runs on import)."""
    ob = hb.mesh_object(name, frames[0], faces, collection, material=material)
    ob.shape_key_add(name="Basis")
    for i, co in enumerate(frames):
        k = ob.shape_key_add(name=f"f{i + 1:04d}")
        k.data.foreach_set("co", np.asarray(co, np.float32).ravel())
        for f, v in ((i, 0.0), (i + 1, 1.0), (i + 2, 0.0)):
            k.value = v
            k.keyframe_insert("value", frame=f)
    if smooth:
        for p in ob.data.polygons:
            p.use_smooth = True
        ob.modifiers.new("smooth", "SUBSURF").levels = 2
    return ob


def nickname_label(text, collection, track, z, n):
    """A text facing the viewer, over the model, its X and Y following the pelvis (track) at every frame."""
    font = bpy.data.curves.new(f"apelido_{collection.name}", "FONT")
    font.body, font.size, font.align_x = text, LABEL_SIZE, "CENTER"
    ob = bpy.data.objects.new(font.name, font)
    collection.objects.link(ob)
    ob.rotation_euler = (math.pi / 2, 0.0, 0.0)  # the body faces -Y, so a text read from the front stands in XZ
    for f in range(n):
        ob.location = (float(track[f][0]), float(track[f][1]), z)
        ob.keyframe_insert("location", frame=f + 1)
    return ob


def outward(v, f):
    t = v[f]
    return f if np.einsum("ij,ij->i", t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() >= 0 else f[:, [0, 2, 1]]


def main(walk_npz, layers_npz, bones_npz, dump_npz, out_blend, frames_dir, nickname=None):
    W, L, B, D = np.load(walk_npz), np.load(layers_npz), np.load(bones_npz), np.load(dump_npz)
    T, skins, names = W["transforms"], W["skins"], [str(n) for n in W["bone_names"]]
    n, n_walk = len(T), int(W["frames_walking"])
    hb.clear_scene()
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, n
    scene.render.fps = int(W["fps"])
    compare, inside = hb.collection("walk_compare"), hb.collection("walk_inside")

    skin_ids, patch = W["skin_ids"], W["patch"]
    local = np.full(N_BODY, -1)
    local[skin_ids] = np.arange(len(skin_ids))
    faces = local[patch]
    animated("skin_simulated", skins, faces, compare, hb.material("skin", COLORS["skin"]), smooth=True)
    current = [D["skins"][min(f, n_walk - 1)][skin_ids] + BESIDE for f in range(n)]
    animated("skin_current_model", current, faces, compare, hb.material("current", COLORS["current"]), smooth=True)

    cut = W["cut_frames"]
    for label in ("muscle", "fat", "fat_deep", "skin", "cavity"):
        if f"cut_{label}" not in W.files:
            continue
        used, f = np.unique(W[f"cut_{label}"], return_inverse=True)
        animated(f"cutaway_{label}", cut[:, used], f.reshape(-1, 3), inside, hb.material(label, COLORS[label]))
    bone_mat = hb.material("bone", COLORS["bone"])
    shown = W["shown_bones"] if "shown_bones" in W.files else np.ones(len(names), bool)  # runs before bug human-model/16 have no such list
    # The feet aren't simulated but stay in the videos: every foot bone follows the rig, the foot's skin too, joined to the simulated skin at the ankle
    held = lambda M: np.concatenate([M, np.repeat(M[-1:], n - len(M), axis=0)])
    bones_shown = [(name, T[:, i]) for i, name in enumerate(names) if shown[i]]
    bones_shown += [(k[:-3], held(D[f"T_{k[:-3]}"])) for k in B.files if k.endswith("__v") and k[:-3] not in names and f"T_{k[:-3]}" in D.files and any(p in k for p in FOOT_BONES)]
    E = np.load(bones_npz[:-len(".bones.npz")] + ".export.npz")
    starts, sizes, loops = E["starts"], E["sizes"], E["loops"]
    body_tris = np.array([(loops[s], loops[s + i], loops[s + i + 1]) for s, c in zip(starts, sizes) for i in range(1, c - 1)])
    body_tris = body_tris[(body_tris < N_BODY).all(axis=1)]
    simulated = np.zeros(N_BODY, bool)
    simulated[skin_ids] = True
    low = D["skin_rest"][:, 2] < FOOT_TOP
    foot_tris = body_tris[low[body_tris].all(axis=1) & ~simulated[body_tris].all(axis=1)]
    used, foot_f = np.unique(foot_tris, return_inverse=True)
    foot_f = foot_f.reshape(-1, 3)
    ours_feet = []
    for f in range(n):
        p = D["skins"][min(f, n_walk - 1)].astype(float)
        p[skin_ids] = skins[f]
        ours_feet.append(p[used])
    animated("skin_feet", ours_feet, foot_f, compare, hb.material("skin", COLORS["skin"]), smooth=True)
    animated("skin_current_feet", [D["skins"][min(f, n_walk - 1)][used] + BESIDE for f in range(n)], foot_f, compare, hb.material("current", COLORS["current"]), smooth=True)
    for name, Tb in bones_shown:
        v = B[f"{name}__v"].astype(float)
        ob = hb.mesh_object(name, v, outward(v, B[f"{name}__f"]), inside, material=bone_mat)
        for f in range(n):
            ob.matrix_world = Matrix(Tb[f].tolist())
            ob.keyframe_insert("location", frame=f + 1)
            ob.keyframe_insert("rotation_euler", frame=f + 1)

    hb.setup_render((960, 960), 16)
    scene.render.image_settings.file_format = "PNG"
    pelvis = names.index("sacrum") if "sacrum" in names else 0
    centre = B[f"{names[pelvis]}__v"].astype(float).mean(axis=0)
    track = np.array([M[:3, :3] @ centre + M[:3, 3] for M in T[:, pelvis]])
    track[:, 2] = track[:, 2].mean()  # a steady camera height, so the body's own bounce shows
    # Framed on the region: its middle height against the pelvis, and a distance that fits its height
    first = skins[0]
    lift = (first[:, 2].min() + first[:, 2].max()) / 2 - track[0, 2]
    far = max(np.ptp(first[:, 2]) / 0.9, 1.0)
    views = {"compare": (np.array([3.0 * far, 0.4, lift]), np.array([0.0, 0.4, lift]), [compare]),
             "inside": (np.array([0.0, -2.0 * far, lift]), np.array([0.0, 0.0, lift]), [inside])}
    if nickname:
        top = float(D["skin_rest"][:, 2].max()) + LABEL_ABOVE
        for c in (compare, inside):
            nickname_label(nickname, c, track, top, n)
    cam = hb.camera_look("HM_cam", (0, 0, 0), (0, 1, 0), lens=50)
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    if frames_dir == "-":  # the file only, no frames
        return
    for view, (eye, look, shown) in views.items():
        for c in (compare, inside):
            for ob in c.objects:
                ob.hide_render = c not in shown
        os.makedirs(os.path.join(frames_dir, view), exist_ok=True)
        for f in range(n):
            scene.frame_set(f + 1)
            hb.camera_look("HM_cam", tuple(track[f] + eye), tuple(track[f] + look), lens=50)
            hb.render(os.path.join(frames_dir, view, f"{f + 1:04d}.png"), cam)


main(*hb.args())

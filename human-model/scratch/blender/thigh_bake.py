"""The walking thigh of tools/thigh_walk.py as a .blend that plays without simulating, and its frames for two videos.
Args: WALK.npz LAYERS.npz WALK_DUMP.npz OUT.blend FRAMES_DIR
Every frame is a shape key, keyed on at its own frame, as muscle_sphere.py does. In the file: the simulated skin and, 30 cm to its right,
the current model's skin on the same step (collection thigh_compare); the back half in section with the femur (collection thigh_inside).
Renders FRAMES_DIR/compare/####.png (front view, both skins) and FRAMES_DIR/inside/####.png (the section from the front)."""
import os, sys
import bpy
import numpy as np
from mathutils import Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

COLORS = {"bone": (0.9, 0.86, 0.75), "muscle": (0.6, 0.12, 0.1), "fat": (0.95, 0.8, 0.35), "skin": (0.85, 0.65, 0.55), "current": (0.55, 0.65, 0.85)}
BESIDE = np.array([0.3, 0.0, 0.0])  # m: the current model's skin, to the right of ours


def compact(verts, faces):
    used, inv = np.unique(faces, return_inverse=True)
    return used, inv.reshape(-1, 3)


def animated(name, frames, faces, collection, material, smooth=False):
    """A mesh whose vertices take frames[i] at frame i + 1, one shape key per frame."""
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


def main(walk_npz, layers_npz, dump_npz, out_blend, frames_dir):
    W, L, D = np.load(walk_npz), np.load(layers_npz), np.load(dump_npz)
    T, nodes_f, skins = W["transforms"], W["nodes"], W["skins"]
    n, n_walk = len(T), int(W["frames_walking"])
    hb.clear_scene()
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, n
    scene.render.fps = int(W["fps"])
    compare, inside = hb.collection("thigh_compare"), hb.collection("thigh_inside")

    skin_ids, patch = L["skin_ids"], L["patch"]
    local = {v: i for i, v in enumerate(skin_ids)}
    faces = np.vectorize(local.get)(patch)
    animated("skin_simulated", skins, faces, compare, hb.material("skin", COLORS["skin"]), smooth=True)
    current = [D["skins"][min(f, n_walk - 1)][skin_ids] + BESIDE for f in range(n)]
    animated("skin_current_model", current, faces, compare, hb.material("current", COLORS["current"]), smooth=True)

    for label in ("bone", "muscle", "fat"):
        used, f = compact(None, L[f"surface_cutaway_{label}"])
        animated(f"cutaway_{label}", nodes_f[:, used], f, inside, hb.material(label, COLORS[label]))
    femur = hb.mesh_object("femur", L["femur_v"], L["femur_f"], inside, material=hb.material("bone", COLORS["bone"]))
    for f in range(n):
        femur.matrix_world = Matrix(T[f].tolist())
        femur.keyframe_insert("location", frame=f + 1)
        femur.keyframe_insert("rotation_euler", frame=f + 1)

    hb.setup_render((960, 720), 16)
    scene.render.image_settings.file_format = "PNG"
    cam = hb.camera_look("HM_cam", (0, 0, 0), (0, 1, 0), lens=50)
    centre = L["nodes"].mean(axis=0)
    track = np.array([M[:3, :3] @ centre + M[:3, 3] for M in T])
    views = {"compare": (np.array([0.15, -1.3, 0.0]), np.array([0.15, 0.0, 0.0]), [compare]),
             "inside": (np.array([0.0, -0.8, 0.0]), np.array([0.0, 0.0, 0.0]), [inside])}
    bpy.ops.wm.save_as_mainfile(filepath=out_blend)
    for view, (eye, look, shown) in views.items():
        for c in (compare, inside):
            for ob in c.objects:
                ob.hide_render = c not in shown
        os.makedirs(os.path.join(frames_dir, view), exist_ok=True)
        for f in range(n):
            scene.frame_set(f + 1)
            target = track[f] + look
            hb.camera_look("HM_cam", tuple(track[f] + eye), tuple(target), lens=50)
            hb.render(os.path.join(frames_dir, view, f"{f + 1:04d}.png"), cam)


main(*hb.args())

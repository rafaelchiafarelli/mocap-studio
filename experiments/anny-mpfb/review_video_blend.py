"""A video fit in Blender: the fitted body as an MPFB human (live sliders), and per frame a camera with the frame behind and the posed body
in front, as wire. Runs in Blender.
    python3 human-model/blender_run.py experiments/anny-mpfb/review_video_blend.py OUT.blend FRAMES_DIR FIT_DIR
Checks that the MPFB human built from the recipe is the fitted rest body (printed, and in OUT.blend's text 'verificacao')."""
import json, math, os, sys
import bpy
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
out_blend, frames_dir, fit_dir = a
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.locationservice import LocationService

fit = json.load(open(os.path.join(fit_dir, "fit.json")))
meta = json.load(open(os.path.join(frames_dir, "frames.json")))["kept"]
z = np.load(os.path.join(fit_dir, "posed.npz"))
faces = [f for f in z["faces"].tolist() if max(f) < 13380]
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)

# The MPFB human from the recipe
tj = json.load(open(os.path.join(LocationService.get_mpfb_data("targets"), "target.json")))
opposite = {}
for section in tj.values():
    for cat in section["categories"]:
        if "opposites" in cat:
            for side in ("left", "right", "unsided"):
                p, n = cat["opposites"].get(f"positive-{side}"), cat["opposites"].get(f"negative-{side}")
                if p and n:
                    opposite[p], opposite[n] = n, p
recipe = fit["recipe"]
body = HumanService.create_human(macro_detail_dict=recipe["macros"])
for t, v in recipe["targets"].items():
    if v < 0 and t in opposite:
        t, v = opposite[t], -v
    TargetService.load_target(body, TargetService.target_full_path(t), weight=v, name=t)
body.name = "modelo10 ajustada (MPFB)"
keys = body.data.shape_keys.key_blocks
base = np.array([v.co[:] for v in keys[0].data])
co = base.copy()
for k in keys[1:]:
    co += k.value * (np.array([v.co[:] for v in k.data]) - base)
co = (np.array(body.matrix_world)[:3, :3] @ co.T).T[:13380]
rest = z["rest"]
d = (co - co.mean(0)) - (rest - rest.mean(0))
check = f"MPFB da receita contra o corpo ajustado: media {np.linalg.norm(d, axis=1).mean() * 1000:.2f} mm, max {np.linalg.norm(d, axis=1).max() * 1000:.2f} mm; altura {np.ptp(co[:, 2]):.3f} m"
print(check)
txt = bpy.data.texts.new("verificacao")
txt.write(check + "\n")
body.location = (0, 0, 0)

# One camera per frame, the frame behind, the posed body as wire
W, H = meta[0]["size"]
scene = bpy.context.scene
scene.render.resolution_x, scene.render.resolution_y = W, H
lens = fit["focal_px"] * 36.0 / W
root = bpy.data.collections.new("quadros do video")
scene.collection.children.link(root)
for b, k in enumerate(meta):
    col = bpy.data.collections.new(f"quadro {k['stem']} ({'frente' if k['view'] == 'front' else 'costas'})")
    root.children.link(col)
    me = bpy.data.meshes.new("corpo " + k["stem"])
    me.from_pydata(z["cam_verts"][b][:13380].tolist(), [], faces)
    ob = bpy.data.objects.new("corpo " + k["stem"], me)
    ob.display_type = "WIRE"
    ob.color = (0.2, 0.6, 1.0, 1.0)
    col.objects.link(ob)
    cd = bpy.data.cameras.new("camera " + k["stem"])
    cd.lens, cd.sensor_fit, cd.sensor_width = lens, "HORIZONTAL", 36.0
    cd.clip_end = 200.0
    cd.show_background_images = True
    bg = cd.background_images.new()
    bg.image = bpy.data.images.load(os.path.join(frames_dir, "frames", k["stem"] + ".jpg"))
    bg.alpha, bg.display_depth, bg.frame_method = 1.0, "BACK", "FIT"
    cam = bpy.data.objects.new("camera " + k["stem"], cd)
    cam.rotation_euler = (math.pi / 2, 0, 0)
    col.objects.link(cam)
    if b == 0:
        scene.camera = cam
    # Frame b of the timeline shows this frame's camera
    m = scene.timeline_markers.new(k["stem"], frame=b + 1)
    m.camera = cam
scene.frame_start, scene.frame_end, scene.frame_current = 1, len(meta), 1
bpy.ops.wm.save_as_mainfile(filepath=out_blend)

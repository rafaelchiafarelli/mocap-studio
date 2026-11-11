"""Frames of a body for a plain viewport-style video, to watch away from Blender. Run with --blend. Args: out_dir view [folds_off] [wave=NAME]
view: frente, costas or lado. The camera follows the hips. folds_off turns every fold fader and the fine creases off, for a before and after. Encode with ffmpeg."""
import os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

a = hb.args()
out, view = a[0], a[1]
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "MATERIAL"
scene.render.resolution_x, scene.render.resolution_y = 540, 960
if "folds_off" in a[2:]:
    ctrl = bpy.data.objects.get("HM_controls")
    for k in list(ctrl.keys()) if ctrl else []:
        if k.startswith("fold_") and k != "fold_fat":
            ctrl[k] = 0.0
    if "HM_fine_folds" in body.modifiers:
        body.modifiers["HM_fine_folds"].show_render = False
OFFSET = {"frente": np.array([0.0, -3.6, 0.0]), "costas": np.array([0.0, 3.6, 0.0]), "lado": np.array([3.6, 0.0, 0.0])}[view]
os.makedirs(out, exist_ok=True)
for f in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)
    hips = np.array(rig.matrix_world @ rig.pose.bones["spine"].head)
    target = np.array([hips[0], hips[1], 0.9])
    scene.camera = hb.camera_look("HM_video", tuple(target + OFFSET), tuple(target), lens=55)
    scene.render.filepath = os.path.join(out, f"{f:04d}.png")
    bpy.ops.render.render(write_still=True)
print("frames", scene.frame_end - scene.frame_start + 1)

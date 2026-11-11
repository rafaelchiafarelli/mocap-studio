"""Plain viewport-style images of a body from the front, the back and the side. Run with --blend. Args: out_prefix frame[,frame...] (0 for the rest pose as the file holds it)
The camera follows the body. Workbench only, no lights or materials: these are for judging shape against the reference clips."""
import math, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

a = hb.args()
prefix, frames = a[0], [int(x) for x in a[1].split(",")]
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "MATERIAL"
scene.render.resolution_x, scene.render.resolution_y = 560, 1000
VIEWS = {"frente": np.array([0.0, -3.4, 0.0]), "costas": np.array([0.0, 3.4, 0.0]), "lado": np.array([3.4, 0.0, 0.0])}
for frame in frames:
    if frame:
        scene.frame_set(frame)
    bpy.context.view_layer.update()
    hips = np.array(rig.matrix_world @ rig.pose.bones["spine"].head)
    target = np.array([hips[0], hips[1], 0.88])
    for name, offset in VIEWS.items():
        cam = hb.camera_look("HM_still", tuple(target + offset), tuple(target), lens=62)
        scene.camera = cam
        scene.render.filepath = f"{prefix}_{name}_q{frame:04d}.png"
        bpy.ops.render.render(write_still=True)
print("stills", len(frames) * 3)

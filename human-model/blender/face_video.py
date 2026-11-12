"""Frames of the face, close up and plain (viewport-style), for a video with the recording's sound (initiative animation-face). Run with --blend. Args: out_dir [view]
view: frente (default) or tres_quartos. Frames follow the scene's range; the camera follows the head."""
import math, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

a = hb.args()
out, view = a[0], (a[1] if len(a) > 1 else "frente")
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.display.shading.light, scene.display.shading.color_type = "STUDIO", "TEXTURE"  # texture shows the irises; the rest takes its display colour
scene.render.resolution_x, scene.render.resolution_y = 720, 720
# plain display colours, since the viewport shows each material's display colour, not its shader (the eyes came out red)
COLOURS = {"eye": (0.92, 0.91, 0.88, 1.0), "teeth": (0.86, 0.82, 0.72, 1.0), "tongue": (0.72, 0.38, 0.38, 1.0), "lash": (0.12, 0.10, 0.09, 1.0)}
for o in bpy.data.objects:
    if o.type == "MESH":
        for key, colour in COLOURS.items():
            if key in o.name.lower():
                for m in o.data.materials:
                    if m:
                        m.diffuse_color = colour
os.makedirs(out, exist_ok=True)
FRAMES = [int(x) for x in a[2].split(",")] if len(a) > 2 else None
offset = {"frente": np.array([0.0, -0.55, 0.0]), "tres_quartos": np.array([0.36, -0.42, 0.0])}[view]
for f in FRAMES or range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)
    head = rig.pose.bones["spine.006"]
    c = np.array(rig.matrix_world @ (head.head + 0.45 * (head.tail - head.head)))
    cam = hb.camera_look("HM_face_cam", tuple(c + offset), tuple(c), lens=60)
    cam.data.clip_start = 0.01
    scene.camera = cam
    scene.render.filepath = os.path.join(out, f"{f:04d}.png")
    bpy.ops.render.render(write_still=True)
print("RESULT frames", scene.frame_end - scene.frame_start + 1, "fps", scene.render.fps)

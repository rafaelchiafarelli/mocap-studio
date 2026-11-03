"""Renders a frame range to PNGs from a named view. Args: out_dir view start end [skin=0|1] [res=WxH]. Run with --blend."""
import os, sys
import bpy
from mathutils import Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
a = hb.args()
out, view, start, end = a[0], a[1], int(a[2]), int(a[3])
props = dict(p.split("=") for p in a[4:])
w, h = (int(x) for x in props.get("res", "640x720").split("x"))
hb.setup_render((w, h), 8)
scene = bpy.context.scene
rig = bpy.data.objects["HM_rig"]
for o in bpy.data.objects:
    if o.name.endswith(".skin"):
        o.hide_render = props.get("skin", "1") == "0"
if view == "walkside":
    cam = hb.camera_look("cam", (4.6, -1.6, 1.0), (0, -1.6, 0.9), 70)
elif view == "head":
    cam = hb.camera_look("cam", (0.28, -0.75, 1.62), (0, -0.05, 1.59), 50)
scene.camera = cam
if view == "walkside":
    # follow the body
    for f in range(start, end + 1):
        scene.frame_set(f)
        cam.location = (4.6, rig.location.y, 1.0)
        cam.keyframe_insert("location", frame=f)
os.makedirs(out, exist_ok=True)
for f in range(start, end + 1):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(out, f"f{f:04d}.png")
    bpy.ops.render.render(write_still=True)
print("done", start, end)

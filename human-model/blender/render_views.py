"""Renders review stills of a model file. Args: out_prefix view[,view]; views: body, head. Run with --blend."""
import os, sys
import bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
a = hb.args()
prefix, views = a[0], a[1].split(",")
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
props = dict(p.split("=") for p in a[2:])
hb.setup_render((900, 1400), 16)
m = skin.data.materials[0] if skin.data.materials else None
show_skin = props.get("skin", "1") != "0"
for o in bpy.data.objects:
    if o.name.endswith(".skin"):
        o.hide_render = not show_skin
    # with skin on, the viewer sees only skin; the inner layers still drive it
    elif o.name == "HM_muscles" or (o.parent_type == "BONE" and o.type == "MESH"):
        o.hide_render = show_skin or (o.name == "HM_muscles" and props.get("muscles", "1") == "0")
ctrl = bpy.data.objects.get("HM_controls")
for k, v in props.items():
    if ctrl is not None and k in ctrl:
        ctrl[k] = float(v)
if ctrl is not None:
    ctrl.update_tag()
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
for view in views:
    if view == "body":
        cam = hb.camera_look("cam_body", (1.4, -4.2, 1.1), (0, 0, 0.9), 50)
    elif view == "side":
        cam = hb.camera_look("cam_side", (4.5, -0.1, 1.0), (0, 0, 0.9), 50)
    elif view == "head":
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 1000
        cam = hb.camera_look("cam_head", (0.28, -0.75, 1.62), (0, -0.05, 1.59), 50)
    elif view == "headside":
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 1000
        cam = hb.camera_look("cam_hs", (0.8, -0.1, 1.6), (0, -0.05, 1.59), 50)
    hb.render(f"{prefix}_{view}.png", cam)
print("rendered")

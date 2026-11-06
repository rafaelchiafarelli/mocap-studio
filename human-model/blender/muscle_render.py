"""Renders a muscle sphere file to PNGs. Args: out_dir. Run with --blend. A Cloth file gets its boxes and camera here, since Cloth's load is a block of points."""
import os, sys
import bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
out = hb.args()[0]
os.makedirs(out, exist_ok=True)
scene = bpy.context.scene
ob = bpy.data.objects["muscle"]
cloth = "cloth" in ob.modifiers
low = None
if cloth:
    col = hb.collection("muscle")
    ob.data.materials.append(hb.material("muscle_red", (0.62, 0.11, 0.09), roughness=0.35))
    for p in ob.data.polygons:
        p.use_smooth = True
    b = 0.025
    v = [(x, y, z) for x in (-b, b) for y in (-b, b) for z in (-b, b)]
    f = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    steel = hb.material("box_steel", (0.32, 0.34, 0.37), roughness=0.4)
    hb.mesh_object("box_top_fixed", v, f, col, material=steel).location = (0, 0, b)
    low = hb.mesh_object("box_bottom_1kg", v, f, col, material=steel)
    n = len(ob.data.vertices)
    centre = 642 + 665  # middle of the 11x11x11 block, after the 642 sphere points
hb.setup_render((800, 800), 32)
scene.camera = hb.camera_look("camera", (0.1, -0.36, -0.03), (0, 0, -0.065), 50)
scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.75, 0.77, 0.8, 1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.35
scene.render.image_settings.file_format = "PNG"
for frame in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(frame)
    if low:
        low.location = hb.evaluated_verts(ob)[centre]
    scene.render.filepath = os.path.join(out, f"f{frame:04d}.png")
    bpy.ops.render.render(write_still=True)
print("done")

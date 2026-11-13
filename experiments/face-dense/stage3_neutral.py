"""Opened on the clean character .blend. Saves neutral vertices, edges and skin flags, and renders a neutral front view. Arg: output dir."""
import json, sys
import bpy, numpy as np
from mathutils import Vector
out = sys.argv[sys.argv.index("--") + 1]
s = bpy.context.scene; body = bpy.data.objects["HM_body"]
for m in body.modifiers: m.show_viewport = False
bpy.context.view_layer.update()
me = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
n = len(me.vertices); co = np.zeros(n * 3, dtype=np.float64); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
ed = np.zeros(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get("vertices", ed)
vg = body.vertex_groups["body"].index
skin = np.array([any(g.group == vg and g.weight > 0 for g in v.groups) for v in body.data.vertices])
np.savez(f"{out}/neutral.npz", co=co, edges=ed.reshape(-1, 2), skin=skin, world=np.array(body.matrix_world))
print("RESULT verts", n, "edges", len(ed) // 2, "skin", int(skin.sum()), "z", round(float(co[:, 2].max()), 3))
for m in body.modifiers: m.show_viewport = True
for o in bpy.data.objects:
    if o.type == "CURVES": o.hide_render = True
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
s.render.engine = "CYCLES"; s.cycles.device = "GPU"; s.cycles.samples = 32; s.cycles.use_denoising = True; s.cycles.denoiser = "OPTIX"; s.view_settings.view_transform = "AgX"
s.render.resolution_x = s.render.resolution_y = 1024
w = s.world or bpy.data.worlds.new("W"); s.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (.3, .3, .31, 1)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
hc = (rig.matrix_world @ rig.data.bones["spine.006"].head_local + rig.matrix_world @ rig.data.bones["spine.006"].tail_local) / 2 + Vector((0, 0, -0.03))
def aim(o, t): o.rotation_euler = (Vector(t) - o.location).to_track_quat("-Z", "Y").to_euler()
l = bpy.data.lights.new("K", "AREA"); l.energy = 50; l.size = 1.2; lo = bpy.data.objects.new("K", l); s.collection.objects.link(lo); lo.location = hc + Vector((-.5, -1.1, .5)); aim(lo, hc)
c = bpy.data.objects.new("C", bpy.data.cameras.new("C")); s.collection.objects.link(c); s.camera = c; c.data.lens = 85; c.location = hc + Vector((0, -.62, 0)); aim(c, hc)
bpy.context.view_layer.update()
f = c.data.lens / c.data.sensor_width * 1024
R = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], float) @ np.array(c.matrix_world.inverted())[:3, :4]
json.dump({"K": [[f, 0, 512], [0, f, 512], [0, 0, 1]], "Rt": R.tolist()}, open(f"{out}/camera.json", "w"))
s.render.filepath = f"{out}/neutral_front.png"; bpy.ops.render.render(write_still=True); print("RESULT rendered", flush=True)

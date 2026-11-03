"""Stage 2 data: render the animated face from three virtual cameras and save true vertex positions and cameras.
Opened on a keyed character .blend. Args: output dir, first frame, last frame."""
import json, math, sys
import bpy
import numpy as np
from mathutils import Vector
out, f0, f1 = sys.argv[sys.argv.index("--") + 1:]; f0, f1 = int(f0), int(f1)
s = bpy.context.scene
prefs = bpy.context.preferences.addons["cycles"].preferences; prefs.compute_device_type = "OPTIX"; prefs.get_devices()
for d in prefs.devices: d.use = d.type == "OPTIX"
s.cycles.device = "GPU"; s.cycles.samples = 32; s.cycles.use_denoising = True; s.cycles.denoiser = "OPTIX"
s.render.use_sequencer = False; s.render.resolution_x = s.render.resolution_y = 1024; s.render.film_transparent = False
s.world.node_tree.nodes["Background"].inputs[1].default_value = 1.0
for o in bpy.data.objects:
    if o.type == "CURVES": o.hide_render = True; o.hide_viewport = True
body = bpy.data.objects["character.body"]
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
hc = (rig.matrix_world @ rig.data.bones["spine.006"].head_local + rig.matrix_world @ rig.data.bones["spine.006"].tail_local) / 2 + Vector((0, 0, -0.03))
cams = {}
for name, az in (("front", 0), ("left", -35), ("right", 35)):
    c = bpy.data.objects.new(name, bpy.data.cameras.new(name)); s.collection.objects.link(c); c.data.lens = 85
    a = math.radians(az); c.location = hc + Vector((math.sin(a) * 0.62, -math.cos(a) * 0.62, 0.0))
    c.rotation_euler = (Vector(hc) - c.location).to_track_quat("-Z", "Y").to_euler(); cams[name] = c
bpy.context.view_layer.update()
info = {}
for n, c in cams.items():
    W = 1024; f_px = c.data.lens / c.data.sensor_width * W
    K = [[f_px, 0, W / 2], [0, f_px, W / 2], [0, 0, 1]]
    w2c = c.matrix_world.inverted()
    # Blender camera looks down -Z with +Y up; image y points down.
    R = np.array([[1, 0, 0], [0, -1, 0], [0, 0, -1]], float) @ np.array(w2c)[:3, :4]
    info[n] = {"K": K, "Rt": R.tolist()}
json.dump(info, open(f"{out}/cameras.json", "w"))
slot = [i for i, m in enumerate(body.data.materials) if m and "lips" in m.name][0]
positions = []
for f in range(f0, f1 + 1):
    s.frame_set(f)
    me = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    p = np.zeros(len(me.vertices) * 3, dtype=np.float32); me.vertices.foreach_get("co", p); positions.append(p.reshape(-1, 3))
    if f == f0:
        lips = sorted({v for q in me.polygons if q.material_index == slot for v in q.vertices}); np.save(f"{out}/lip_verts.npy", np.array(lips))
    for n, c in cams.items():
        s.camera = c; s.render.filepath = f"{out}/{n}_{f:04d}.png"; bpy.ops.render.render(write_still=True)
    print("RESULT frame", f, flush=True)
np.save(f"{out}/truth.npy", np.stack(positions))
print("RESULT done", len(positions), flush=True)

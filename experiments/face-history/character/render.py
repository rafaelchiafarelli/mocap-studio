"""Opened on the character .blend. Args: output prefix, samples, view names. Neutral photographic portrait setup."""
import math, sys
import bpy
from mathutils import Vector
args = sys.argv[sys.argv.index("--") + 1:]
prefix, samples, views = args[0], int(args[1]), args[2:]
s = bpy.context.scene
s.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type == "OPTIX"
s.cycles.device = "GPU"
s.cycles.samples, s.cycles.use_denoising = samples, True
s.cycles.denoiser = "OPTIX"
s.view_settings.view_transform, s.view_settings.look = "AgX", "None"
s.render.film_transparent = False
w = s.world or bpy.data.worlds.new("W"); s.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.20, 0.20, 0.21, 1)
w.node_tree.nodes["Background"].inputs[1].default_value = 0.35
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
head = rig.matrix_world @ rig.data.bones["spine.006"].head_local
tail = rig.matrix_world @ rig.data.bones["spine.006"].tail_local
hc = (head + tail) / 2
hip = rig.matrix_world @ rig.data.bones["spine"].head_local
def aim(o, t):
    o.rotation_euler = (Vector(t) - o.location).to_track_quat("-Z", "Y").to_euler()
def light(name, loc, target, power, size, rgb=(1, 1, 1)):
    d = bpy.data.lights.new(name, "AREA"); d.energy, d.size, d.color = power, size, rgb
    o = bpy.data.objects.new(name, d); s.collection.objects.link(o); o.location = loc; aim(o, target)
light("Key", hc + Vector((-0.9, -1.1, 0.7)), hc, 60, 0.9, (1, 0.96, 0.9))
light("Fill", hc + Vector((1.2, -0.9, 0.0)), hc, 12, 1.4, (0.9, 0.95, 1))
light("Rim", hc + Vector((0.5, 1.2, 0.5)), hc, 35, 0.6)
floor = bpy.data.meshes.new("Floor"); floor.from_pydata([(-20,-20,0),(20,-20,0),(20,20,0),(-20,20,0)],[],[(0,1,2,3)])
fo = bpy.data.objects.new("Floor", floor); s.collection.objects.link(fo)
fm = bpy.data.materials.new("Floor"); fm.use_nodes = True; fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2,0.2,0.21,1); floor.materials.append(fm)
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); s.collection.objects.link(cam); s.camera = cam
VIEWS = {
 "face_front": (85, 0, 0.88, hc + Vector((0,0,-0.005)), 1024, 1024), "face_34": (85, -35, 0.88, hc + Vector((0,0,-0.005)), 1024, 1024), "face_side": (85, -90, 0.88, hc + Vector((0,0,-0.005)), 1024, 1024),
 "body_front": (50, 0, 5.2, hip + Vector((0,0,-0.08)), 768, 1280), "body_34": (50, -35, 5.2, hip + Vector((0,0,-0.08)), 768, 1280),
}
for v in views:
    lens, az, dist, t, rx, ry = VIEWS[v]
    a = math.radians(az)
    cam.data.lens = lens
    cam.location = t + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.02))
    aim(cam, t)
    s.render.resolution_x, s.render.resolution_y = rx, ry
    s.render.filepath = f"{prefix}{v}.png"
    bpy.ops.render.render(write_still=True)
    print("RESULT rendered", v)

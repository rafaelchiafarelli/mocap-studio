"""Opened on the clean character .blend. Args: PC2 cache, channels JSON, audio file, output .blend. Skin from the cache; never renders."""
import json, sys
import bpy
from mathutils import Vector
pc2, chj, wav, out = sys.argv[sys.argv.index("--") + 1:]
t = json.load(open(chj)); ch = t["channels"]; n = t["frames"]
s = bpy.context.scene; s.render.fps, s.render.fps_base = 24, 1.001; s.frame_start, s.frame_end = 1, n; s.sync_mode = "AUDIO_SYNC"
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
body = bpy.data.objects["character.body"]
mc = body.modifiers.new("FaceCache", "MESH_CACHE"); mc.cache_format = "PC2"; mc.filepath = pc2; mc.deform_mode = "OVERWRITE"; mc.interpolation = "LINEAR"; mc.play_mode = "SCENE"; mc.frame_start = 1
mc.forward_axis = "POS_Y"; mc.up_axis = "POS_Z"
bpy.context.view_layer.objects.active = body
while body.modifiers[0] != mc:
    bpy.ops.object.modifier_move_up(modifier=mc.name)
keys = 0
for o in bpy.data.objects:
    if o.type != "MESH" or o is body or not o.data.shape_keys: continue
    kbs = o.data.shape_keys.key_blocks
    for name, vals in ch.items():
        kb = kbs.get(name)
        if kb is None or max(vals) < 0.01: continue
        for f, v in enumerate(vals, start=1):
            kb.value = v; kb.keyframe_insert("value", frame=f); keys += 1
print("RESULT keys", keys, "modifier stack", [m.name for m in body.modifiers])
for o in bpy.data.objects:
    if o.type == "CURVES": o.hide_viewport = False
sed = s.sequence_editor_create(); sed.strips.new_sound("source_audio", wav, 1, 1)
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
hc = (rig.matrix_world @ rig.data.bones["spine.006"].head_local + rig.matrix_world @ rig.data.bones["spine.006"].tail_local) / 2
def aim(o, tgt): o.rotation_euler = (Vector(tgt) - o.location).to_track_quat("-Z", "Y").to_euler()
for name, off, power, size in (("Key", (-0.9, -1.1, 0.7), 60, 0.9), ("Fill", (1.2, -0.9, 0.0), 12, 1.4), ("Rim", (0.5, 1.2, 0.5), 35, 0.6)):
    l = bpy.data.lights.new(name, "AREA"); l.energy, l.size = power, size
    ob = bpy.data.objects.new(name, l); s.collection.objects.link(ob); ob.location = hc + Vector(off); aim(ob, hc)
cam = bpy.data.objects.new("FaceCam", bpy.data.cameras.new("FaceCam")); s.collection.objects.link(cam); cam.data.lens = 85
cam.location = hc + Vector((0, -0.62, -0.02)); aim(cam, hc + Vector((0, 0, -0.03))); s.camera = cam
w = s.world or bpy.data.worlds.new("W"); s.world = w; w.use_nodes = True; w.node_tree.nodes["Background"].inputs[0].default_value = (.22, .22, .23, 1); w.node_tree.nodes["Background"].inputs[1].default_value = 1.0
teeth = next(o for o in bpy.data.objects if "teeth" in o.name and o.type == "MESH").data.materials[0]
b = next(x for x in teeth.node_tree.nodes if x.bl_idname == "ShaderNodeBsdfPrincipled")
for link in list(b.inputs["Base Color"].links): teeth.node_tree.links.remove(link)
b.inputs["Base Color"].default_value = (0.78, 0.72, 0.6, 1); b.inputs["Roughness"].default_value = 0.25
s.render.engine = "CYCLES"; s.render.resolution_x = s.render.resolution_y = 640; s.render.use_sequencer = False
bpy.ops.wm.save_mainfile(filepath=out); print("RESULT saved", out)

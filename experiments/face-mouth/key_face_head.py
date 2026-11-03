"""Opened on the character .blend. Args: channels JSON, marked-up video, recording, output .blend. Keys face and head; never renders."""
import json, sys
import bpy
from bpy_extras import anim_utils
from mathutils import Matrix, Quaternion, Vector
data_path, marked, recording, out = sys.argv[sys.argv.index("--") + 1:][:4]
take = json.load(open(data_path))
ch, n, fps = take["channels"], take["frames"], take["fps"]
s = bpy.context.scene
s.render.fps, s.render.fps_base = fps, 1.0
s.frame_start, s.frame_end = 1, n
s.sync_mode = "AUDIO_SYNC"  # a slow viewport drops frames instead of falling behind the sound


def bake(owner, data_path, index, values):
    """One curve, one key per frame: much faster than keyframe_insert on every frame."""
    owner.keyframe_insert(data_path, index=index, frame=1) if index >= 0 else owner.keyframe_insert(data_path, frame=1)
    ad = owner.id_data.animation_data
    bag = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    full = (owner.path_from_id(data_path) if owner is not owner.id_data else data_path)
    fc = bag.fcurves.find(full, index=max(index, 0))
    fc.keyframe_points.add(len(values) - 1)
    co = [c for f, v in enumerate(values, start=1) for c in (f, v)]
    fc.keyframe_points.foreach_set("co", co)
    fc.keyframe_points.foreach_set("interpolation", [bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items["LINEAR"].value] * len(values))
    fc.update()


targets = [o for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys and any(k in o.data.shape_keys.key_blocks for k in ch)]
count = 0
for o in targets:
    kbs = o.data.shape_keys.key_blocks
    for name, vals in ch.items():
        kb = kbs.get(name)
        if kb is None or max(vals) < 0.01:
            continue
        bake(kb, "value", -1, vals)
        count += 1
print("RESULT curves", count, [o.name for o in targets])

rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
head = rig.pose.bones["spine.006"]
head.rotation_mode = "QUATERNION"
M = rig.data.bones["spine.006"].matrix_local.to_quaternion()
qs = []
for rv in take["head_rotvec_world"]:
    v = Vector(rv)
    qs.append(M.inverted() @ Quaternion(v.normalized(), v.length) @ M if v.length > 1e-6 else Quaternion())
for i in range(4):
    bake(head, "rotation_quaternion", i, [q[i] for q in qs])

# The stock teeth material renders dark grey in Cycles.
teeth_mat = next(o for o in bpy.data.objects if "teeth" in o.name and o.type == "MESH").data.materials[0]
teeth_bsdf = next(nd for nd in teeth_mat.node_tree.nodes if nd.bl_idname == "ShaderNodeBsdfPrincipled")
for link in list(teeth_bsdf.inputs["Base Color"].links):
    teeth_mat.node_tree.links.remove(link)
teeth_bsdf.inputs["Base Color"].default_value = (0.78, 0.72, 0.6, 1)
teeth_bsdf.inputs["Roughness"].default_value = 0.25

sed = s.sequence_editor_create()
sed.strips.new_sound("recording_audio", recording, 1, 1)
for t, name in take.get("markers", []):
    s.timeline_markers.new(name, frame=int(round(t * fps)) + 1)

# The marked-up tracking video on a card beside him, on the same clock.
img = bpy.data.images.load(marked)
mat = bpy.data.materials.new("tracking_video"); mat.use_nodes = True
nt = mat.node_tree; nt.nodes.clear()
tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img
tex.image_user.frame_duration = n; tex.image_user.frame_start = 1; tex.image_user.use_auto_refresh = True
em = nt.nodes.new("ShaderNodeEmission"); o_ = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(tex.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs[0], o_.inputs["Surface"])
nt.nodes.active = tex
hc = (rig.matrix_world @ rig.data.bones["spine.006"].head_local + rig.matrix_world @ rig.data.bones["spine.006"].tail_local) / 2
bpy.ops.mesh.primitive_plane_add(size=1, location=hc + Vector((0.44, 0.0, 0.0)), rotation=(1.5708, 0, 0))
card = bpy.context.active_object; card.name = "tracking_video_card"; card.scale = (0.44, 0.2475, 1); card.data.materials.append(mat)
def aim(o, t): o.rotation_euler = (Vector(t) - o.location).to_track_quat("-Z", "Y").to_euler()
for name, off, power, size in (("Key", (-0.9, -1.1, 0.7), 60, 0.9), ("Fill", (1.2, -0.9, 0.0), 12, 1.4), ("Rim", (0.5, 1.2, 0.5), 35, 0.6)):
    l = bpy.data.lights.new(name, "AREA"); l.energy, l.size = power, size
    ob = bpy.data.objects.new(name, l); s.collection.objects.link(ob); ob.location = hc + Vector(off); aim(ob, hc)
cam = bpy.data.objects.new("FaceCam", bpy.data.cameras.new("FaceCam")); s.collection.objects.link(cam)
cam.data.lens = 50; cam.location = hc + Vector((0.0, -1.2, 0.0)); cam.rotation_euler = (1.5708, 0, 0); s.camera = cam
cam.data.shift_x = 0.23  # keeps him frontal: moving the camera sideways reads as a turned head
s.render.engine = "CYCLES"; s.render.resolution_x, s.render.resolution_y = 1920, 1080
# Scalp and fine hair stay in renders but are hidden in the viewport: they made playback lag in the earlier test.
for o in bpy.data.objects:
    if o.type == "CURVES" and "eyebrows" not in o.name:
        o.hide_set(True)
for scr in bpy.data.screens:
    for area in scr.areas:
        if area.type == "VIEW_3D":
            sp = area.spaces.active
            sp.shading.type = "SOLID"; sp.shading.color_type = "TEXTURE"; sp.shading.light = "STUDIO"
            sp.overlay.show_overlays = False
            sp.region_3d.view_perspective = "CAMERA"
s.frame_set(1)
bpy.ops.wm.save_mainfile(filepath=out)
print("RESULT saved", out)

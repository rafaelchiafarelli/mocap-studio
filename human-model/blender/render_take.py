"""Renders a keyed take through its own camera, in a fast engine. Args: out_dir [start end width height]. Run with --blend."""
import os, sys
import bpy
a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]
scene = bpy.context.scene
start = int(a[1]) if len(a) > 1 else scene.frame_start
end = int(a[2]) if len(a) > 2 else scene.frame_end
scene.render.engine = "BLENDER_EEVEE"
scene.eevee.taa_render_samples = 8
scene.render.resolution_x, scene.render.resolution_y = int(a[3]) if len(a) > 3 else 640, int(a[4]) if len(a) > 4 else 720
scene.render.image_settings.file_format = "JPEG"
for o in bpy.data.objects:
    if "video_card" in o.name:
        o.hide_render = True
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o.name.endswith("metarig"))
from mathutils import Vector
nose = rig.matrix_world @ rig.data.bones["nose.001"].head_local
cam = bpy.data.objects.new("cmp", bpy.data.cameras.new("cmp"))
scene.collection.objects.link(cam)
cam.location = (nose.x + 0.14, nose.y - 0.70, nose.z)
cam.data.lens = 85
cam.rotation_euler = (Vector((nose.x, nose.y, nose.z - 0.012)) - cam.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam
os.makedirs(out, exist_ok=True)
for f in range(start, end + 1):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(out, f"f{f:04d}.jpg")
    bpy.ops.render.render(write_still=True)
print("rendered", start, end)

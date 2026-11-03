"""Opened on character_v2.blend. Args: cleaned JSON, source clip, output .blend. Keys face shapes only; never renders."""
import json, sys
import bpy
import numpy as np
from mathutils import Vector, Euler
from mathutils.bvhtree import BVHTree
data_path, clip, out = sys.argv[sys.argv.index("--") + 1:][:3]
take = json.load(open(data_path))
ch = take["channels"]; n = take["frames"]
s = bpy.context.scene
s.render.fps, s.render.fps_base = take["fps_num"], take["fps_den"] / 1.0
if take["fps_num"] == 24000:
    s.render.fps, s.render.fps_base = 24, 1.001
s.frame_start, s.frame_end = 1, n
bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
targets = [o for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys and any(k in o.data.shape_keys.key_blocks for k in ch)]
count = 0
for o in targets:
    kbs = o.data.shape_keys.key_blocks
    for name, vals in ch.items():
        kb = kbs.get(name)
        if kb is None or max(vals) < 0.01:
            continue
        for f, v in enumerate(vals, start=1):
            kb.value = v
            kb.keyframe_insert("value", frame=f)
            count += 1
print("RESULT keyed_objects", [o.name for o in targets], "keys", count)


def skin_bvh():
    body = bpy.data.objects["character.body"]
    dg = bpy.context.evaluated_depsgraph_get()
    m = body.evaluated_get(dg).to_mesh()
    return BVHTree.FromPolygons([v.co.copy() for v in m.vertices], [tuple(p.vertices) for p in m.polygons]), dg


def check(label):
    bvh, dg = skin_bvh()
    for o in [c for c in bpy.data.objects if c.type == "CURVES"]:
        e = o.evaluated_get(dg).data
        p = np.zeros(len(e.attributes["position"].data) * 3, dtype=np.float32)
        e.attributes["position"].data.foreach_get("vector", p)
        roots = p.reshape(-1, len(p) // 3 // len(e.curves), 3)[:, 0]
        idx = np.random.default_rng(1).choice(len(roots), min(4000, len(roots)), replace=False)
        d = np.array([bvh.find_nearest(Vector(r))[3] for r in roots[idx]]) * 1000
        print(f"RESULT gap {label} {o.name} p50 {np.median(d):.2f} p99 {np.percentile(d,99):.2f} max {d.max():.2f} mm")


def brow_roots():
    o = bpy.data.objects["character.eyebrows"]
    e = o.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    p = np.zeros(len(e.attributes["position"].data) * 3, dtype=np.float32)
    e.attributes["position"].data.foreach_get("vector", p)
    return p.reshape(-1, len(p) // 3 // len(e.curves), 3)[:, 0].copy()


low = int(np.argmin(np.array(ch["browOuterUpRight"]) + np.array(ch["browInnerUp"]))) + 1
high = int(np.argmax(np.array(ch["browOuterUpRight"]) + np.array(ch["browInnerUp"]))) + 1
s.frame_set(low); a = brow_roots()
s.frame_set(high); b = brow_roots()
mv = np.linalg.norm(b - a, axis=1) * 1000
print(f"RESULT brow_motion f{low}->f{high} p50 {np.median(mv):.2f} p95 {np.percentile(mv,95):.2f} max {mv.max():.2f} mm")
check_frames = {"start": 1, "jaw_peak": int(np.argmax(ch["jawOpen"])) + 1, "smile_peak": int(np.argmax(ch["mouthSmileLeft"])) + 1, "blink_peak": int(np.argmax(ch["eyeBlinkLeft"])) + 1}
for label, f in check_frames.items():
    s.frame_set(f)
    check(f"{label}(f{f})")
# head turn in memory only, to prove the strands follow the skeleton too
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
head = rig.pose.bones["spine.006"]; head.rotation_mode = "XYZ"; head.rotation_euler = Euler((0.25, 0.0, 0.5), "XYZ")
bpy.context.view_layer.update()
check("head_turned")
head.rotation_euler = Euler((0, 0, 0), "XYZ")
s.frame_set(1)

# The stock teeth material renders dark grey in Cycles.
teeth_mat = next(o for o in bpy.data.objects if "teeth" in o.name and o.type == "MESH").data.materials[0]
teeth_bsdf = next(n for n in teeth_mat.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
for link in list(teeth_bsdf.inputs["Base Color"].links):
    teeth_mat.node_tree.links.remove(link)
teeth_bsdf.inputs["Base Color"].default_value = (0.78, 0.72, 0.6, 1)
teeth_bsdf.inputs["Roughness"].default_value = 0.25

# Reference: the clip and its sound in the sequencer, a face camera and plain lights for viewing. Nothing is rendered.
sed = s.sequence_editor_create()
if not clip.lower().endswith(".wav"):
    sed.strips.new_movie("source_clip", clip, 2, 1)
sed.strips.new_sound("source_audio", clip, 1, 1)
hc = (rig.matrix_world @ rig.data.bones["spine.006"].head_local + rig.matrix_world @ rig.data.bones["spine.006"].tail_local) / 2
def aim(o, t): o.rotation_euler = (Vector(t) - o.location).to_track_quat("-Z", "Y").to_euler()
for name, off, power, size in (("Key", (-0.9, -1.1, 0.7), 60, 0.9), ("Fill", (1.2, -0.9, 0.0), 12, 1.4), ("Rim", (0.5, 1.2, 0.5), 35, 0.6)):
    l = bpy.data.lights.new(name, "AREA"); l.energy, l.size = power, size
    ob = bpy.data.objects.new(name, l); s.collection.objects.link(ob); ob.location = hc + Vector(off); aim(ob, hc)
cam = bpy.data.objects.new("FaceCam", bpy.data.cameras.new("FaceCam")); s.collection.objects.link(cam)
cam.data.lens = 85; cam.location = hc + Vector((-0.45, -0.75, 0.02)); aim(cam, hc); s.camera = cam
s.render.engine = "CYCLES"; s.render.resolution_x, s.render.resolution_y = 1080, 1080
bpy.ops.wm.save_mainfile(filepath=out)
print("RESULT saved", out)

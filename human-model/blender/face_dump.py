"""The face's skin motion, frame by frame, for tools/face_tissue.py (initiative animation-face, epic face-soft-tissue). Run with --blend on a face file. Args: out.npz
Positions of the body's own vertices each frame (pose and shape keys, display modifiers off), the rest skin, its triangles, and the face bones' weights as w_<bone>."""
import os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posed_mesh as pm

FACE_PREFIXES = ("cheek.", "jaw", "chin", "lip.", "nose", "brow.", "lid.", "forehead.", "temple.")

a = hb.args()
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
scene = bpy.context.scene
pm.set_display(body, False)
names = {g.index: g.name for g in body.vertex_groups if g.name.startswith(FACE_PREFIXES)}
weights = {name: np.zeros(pm.N_BODY, np.float32) for name in names.values()}
for v in body.data.vertices[: pm.N_BODY]:
    for g in v.groups:
        if g.group in names:
            weights[names[g.group]][v.index] = g.weight
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
rest = pm.read(body)[: pm.N_BODY].astype(np.float32)
rig.data.pose_position = "POSE"
bpy.context.view_layer.update()
first, last = scene.frame_start, scene.frame_end
frames = []
for f in range(first, last + 1):
    scene.frame_set(f)
    frames.append(pm.read(body)[: pm.N_BODY].astype(np.float32))
pm.set_display(body, True)
np.savez_compressed(a[0], positions=np.array(frames), rest=rest, tris=pm.triangles(body), fps=scene.render.fps / scene.render.fps_base, first=first, **{f"w_{k}": v for k, v in weights.items()})
print("frames", len(frames), first, last, "fps", scene.render.fps, "face bones", len(weights))

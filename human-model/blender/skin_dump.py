"""The skin's motion, frame by frame, for tools/skin_waves.py. Run with --blend on a walking body. Args: out.npz"""
import os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
import posed_mesh as pm

a = hb.args()
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
scene = bpy.context.scene
pm.set_display(body, False)
BONES = ["breast.L", "breast.R", "thigh.L", "thigh.R", "upper_arm.L", "upper_arm.R", "shin.L", "shin.R"]
weights = {}
for name in BONES:
    group = body.vertex_groups[name]
    w = np.zeros(pm.N_BODY, np.float32)
    for v in body.data.vertices[: pm.N_BODY]:
        for g in v.groups:
            if g.group == group.index:
                w[v.index] = g.weight
    weights[f"w_{name}"] = w
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
rest = pm.read(body)[: pm.N_BODY].astype(np.float32)
rig.data.pose_position = "POSE"
bpy.context.view_layer.update()
M = np.array(rig.matrix_world)
head = lambda n: (np.array(rig.data.bones[n].head_local) @ M[:3, :3].T + M[:3, 3])
marks = np.array([head("thigh.L")[2], head("spine.003")[2]])
foot_rest = np.array([head("foot.L"), head("foot.R")], np.float32)
first, last = scene.frame_start, scene.frame_end
frames = []
feet = []
for f in range(first, last + 1):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    frames.append(pm.read(body)[: pm.N_BODY].astype(np.float32))
    W = rig.matrix_world
    feet.append([[*(W @ rig.pose.bones[f"foot.{s}"].head), *(W @ rig.pose.bones[f"toe.{s}"].head)] for s in "LR"])
pm.set_display(body, True)
np.savez_compressed(a[0], positions=np.array(frames), rest=rest, tris=pm.triangles(body), fps=scene.render.fps / scene.render.fps_base, first=first, marks=marks, feet=np.array(feet, np.float32), foot_rest=foot_rest, **weights)
print("frames", len(frames), first, last, "fps", scene.render.fps)

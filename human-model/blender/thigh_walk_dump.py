"""The left femur's motion and the current skin, every frame of a file from walk.py, for tools/thigh_walk.py. Args: OUT.npz
Writes: femur_rest (the femur_L mesh in world space at the rest pose), skin_rest (body vertices at rest), and per frame the femur's
world transform relative to rest (frames x 4 x 4) and the skin's body vertices as the current model moves them (frames x 13380 x 3)."""
import sys
import bpy
import numpy as np

N_BODY = 13380  # MakeHuman's body vertices come first; helpers follow, as in export_blend.py
out = sys.argv[sys.argv.index("--") + 1:][0]
scene = bpy.context.scene
rig = bpy.data.objects["HM_rig"]
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
femur = bpy.data.objects["femur_L"]


def skin_world():
    dg = bpy.context.evaluated_depsgraph_get()
    ev = skin.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    ev.to_mesh_clear()
    M = np.array(skin.matrix_world)
    return (co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])[:N_BODY]


rig.data.pose_position = "REST"
scene.frame_set(scene.frame_start)
bpy.context.view_layer.update()
rest_matrix = np.array(femur.matrix_world)
c = np.empty(len(femur.data.vertices) * 3)
femur.data.vertices.foreach_get("co", c)
femur_rest = c.reshape(-1, 3) @ rest_matrix[:3, :3].T + rest_matrix[:3, 3]
skin_rest = skin_world()
rig.data.pose_position = "POSE"

transforms, skins = [], []
for f in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    transforms.append(np.array(femur.matrix_world) @ np.linalg.inv(rest_matrix))
    skins.append(skin_world())
np.savez_compressed(out, femur_rest=femur_rest.astype(np.float32), skin_rest=skin_rest.astype(np.float32), transforms=np.array(transforms),
                    skins=np.array(skins, np.float32), frame_start=scene.frame_start, fps=scene.render.fps / scene.render.fps_base)
print("frames", len(transforms))

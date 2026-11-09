"""Every bone mesh's motion and the current skin, every frame of a file from walk.py, for tools/body_walk.py. Args: OUT.npz
Like thigh_walk_dump.py for all bones: per bone, its world transform relative to rest (frames x 4 x 4), as T_<bone>;
skin_rest and skins (frames x 13380 x 3) as there; bone_names lists them."""
import sys
import bpy
import numpy as np

N_BODY = 13380  # as in export_blend.py
out = sys.argv[sys.argv.index("--") + 1:][0]
scene = bpy.context.scene
rig = bpy.data.objects["HM_rig"]
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
bones = sorted((o for o in bpy.data.objects if o.type == "MESH" and o.parent == rig and o.parent_type == "BONE"), key=lambda o: o.name)


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
rest = {o.name: np.linalg.inv(np.array(o.matrix_world)) for o in bones}
skin_rest = skin_world()
rig.data.pose_position = "POSE"
T = {o.name: [] for o in bones}
skins = []
for f in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)
    bpy.context.view_layer.update()
    for o in bones:
        T[o.name].append(np.array(o.matrix_world) @ rest[o.name])
    skins.append(skin_world())
np.savez_compressed(out, bone_names=np.array([o.name for o in bones]), skin_rest=skin_rest.astype(np.float32), skins=np.array(skins, np.float32),
                    fps=scene.render.fps / scene.render.fps_base, **{f"T_{k}": np.array(v) for k, v in T.items()})
print("bones", len(bones), "frames", len(skins))

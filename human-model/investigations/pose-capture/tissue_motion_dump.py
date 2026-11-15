"""Step 11c: every deform bone's motion from rest, every frame, for tissue_sim.py.

    python3 human-model/blender_run.py --blend 07_movimento_duas_cameras_31-43s.blend human-model/investigations/pose-capture/tissue_motion_dump.py OUT.npz

OUT.npz: `T` (frames x bones x 4 x 4), world transform from the rest pose (the rest file 02 has its rig at the origin, so rest is
armature space): rig.matrix_world @ pose matrix @ rest matrix^-1; `bone_names` in tissue_export.py's order (deform bones);
`fps`; `first`, `last`.
"""
import sys
import bpy
import numpy as np

out = sys.argv[sys.argv.index("--") + 1:][0]
scene = bpy.context.scene
rig = bpy.data.objects["HM_rig"]
names = [b.name for b in rig.data.bones if b.use_deform]
rest_inv = [np.linalg.inv(np.array(rig.data.bones[n].matrix_local)) for n in names]
T = []
for f in range(scene.frame_start, scene.frame_end + 1):
    scene.frame_set(f)
    M = np.array(rig.matrix_world)
    T.append([M @ np.array(rig.pose.bones[n].matrix) @ rest_inv[i] for i, n in enumerate(names)])
np.savez_compressed(out, T=np.array(T, np.float32), bone_names=np.array(names), fps=scene.render.fps / scene.render.fps_base,
                    first=scene.frame_start, last=scene.frame_end)
print("frames", len(T), "bones", len(names), "fps", scene.render.fps / scene.render.fps_base)

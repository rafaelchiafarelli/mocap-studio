"""Keys capture onto the rig by bone direction, so the character keeps its proportions. Args: motion.json out.blend. Run with --blend. motion.json holds per-frame targets in the model's frame, from tools/body_motion.py."""
import json, os, sys
import bpy
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
a = hb.args()
motion = json.load(open(a[0]))
rig = bpy.data.objects["HM_rig"]
scene = bpy.context.scene
scene.render.fps = int(motion["fps"])
ORDER = ["spine", "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R", "upper_arm.L", "forearm.L", "upper_arm.R", "forearm.R"]
for pb in rig.pose.bones:
    pb.rotation_mode = "QUATERNION"
n = len(motion["frames"])
for f, frame in enumerate(motion["frames"]):
    for name in ORDER:
        pb = rig.pose.bones[name]
        pb.rotation_quaternion = (1, 0, 0, 0)
    bpy.context.view_layer.update()
    trunk = Matrix(frame["trunk"])
    pb = rig.pose.bones["spine"]
    B = rig.data.bones["spine"].matrix_local.to_3x3()
    pb.rotation_quaternion = (B.inverted() @ trunk @ B).to_quaternion()
    bpy.context.view_layer.update()
    for name in ORDER[1:]:
        if name not in frame["dirs"]:
            continue
        pb = rig.pose.bones[name]
        current = (pb.tail - pb.head).normalized()
        target = Vector(frame["dirs"][name]).normalized()
        rot = current.rotation_difference(target).to_matrix()
        head = pb.head.copy()
        new = rot @ pb.matrix.to_3x3()
        pb.matrix = Matrix.Translation(head) @ new.to_4x4()
        bpy.context.view_layer.update()
    for name in ORDER:
        rig.pose.bones[name].keyframe_insert("rotation_quaternion", frame=f + 1)
    rig.location = frame["root"]
    rig.keyframe_insert("location", frame=f + 1)
scene.frame_start, scene.frame_end = 1, n
bpy.ops.wm.save_as_mainfile(filepath=a[1], compress=True)
print("keyed", n)

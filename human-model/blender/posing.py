"""Joint rotations in the rest pose's axes (+X the body's left, +Y back, +Z up), whatever each bone's own axes are."""
import math
from mathutils import Euler, Matrix, Quaternion, Vector


def rest_rotation(rig, bone):
    return rig.data.bones[bone].matrix_local.to_3x3()


def to_basis(rig, bone, world_rot):
    """A rotation in armature axes as the bone's pose rotation."""
    B = rest_rotation(rig, bone)
    return (B.inverted() @ world_rot.to_3x3() @ B).to_quaternion()


def set_rotation(rig, bone, rot, frame=None):
    pb = rig.pose.bones[bone]
    pb.rotation_mode = "QUATERNION"
    pb.rotation_quaternion = to_basis(rig, bone, rot)
    if frame is not None:
        pb.keyframe_insert("rotation_quaternion", frame=frame)


def rx(d):
    return Matrix.Rotation(math.radians(d), 3, "X")


def ry(d):
    return Matrix.Rotation(math.radians(d), 3, "Y")


def rz(d):
    return Matrix.Rotation(math.radians(d), 3, "Z")


def direction(rig, bone):
    b = rig.data.bones[bone]
    return (b.tail_local - b.head_local).normalized()


def hang_angle(rig, bone, target_deg=0.0):
    """How far about Y a limb must turn so it points down, target_deg away from vertical. Positive for a left limb."""
    d = direction(rig, bone)
    return math.degrees(math.atan2(abs(d.x), -d.z)) - target_deg


def reset(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)

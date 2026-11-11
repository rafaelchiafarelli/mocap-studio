"""Points along the forearms, hands and fingers, each with a radius, for the contact between hands and body (arm_clearance.py, skin_dump.py)."""
import numpy as np

POINTS = [("forearm", 0.5, 0.040), ("forearm", 1.0, 0.032), ("hand", 0.5, 0.025), ("hand", 1.0, 0.020), ("f_middle.03", 1.0, 0.010), ("f_index.03", 1.0, 0.010), ("f_pinky.03", 1.0, 0.010)]
ARM_BONES = ("upper_arm", "forearm", "hand", "palm", "f_", "thumb", "shoulder")


def points(rig, side):
    out = []
    for bone, along, radius in POINTS:
        name = f"{bone}.{side}"
        if name in rig.pose.bones:
            pb = rig.pose.bones[name]
            out.append((rig.matrix_world @ (pb.head + along * (pb.tail - pb.head)), radius))
    return out


def arm_weight(body, n):
    """How much each skin vertex belongs to the arms, so contact never tests the arm against itself."""
    w = np.zeros(n)
    names = {g.index: g.name for g in body.vertex_groups}
    for v in body.data.vertices[:n]:
        for g in v.groups:
            if names[g.group].startswith(ARM_BONES):
                w[v.index] += g.weight
    return w

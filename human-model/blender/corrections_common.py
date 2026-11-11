"""Shared by pose_corrections.py and apply_corrections.py: the corrections as shape keys, each driven by the angle between two bones."""
import bpy
import numpy as np

PAIRS = {"elbow": ("upper_arm.{s}", "forearm.{s}"), "knee": ("thigh.{s}", "shin.{s}"), "hip": ("spine", "thigh.{s}"), "shoulder": ("spine.003", "upper_arm.{s}")}


PV_GROUP = "mhmask-preserve-volume"  # MPFB's own: its second armature modifier preserves volume where this group has weight
ELBOW_RADIUS = 0.09  # measured: volume preservation worsens the elbow (3.8% to 4.7% of its triangles collapsed) and helps everywhere else


def preserve_volume(body, rig):
    """Volume-preserving skinning over the whole body, fading to plain skinning at the elbows."""
    group = body.vertex_groups.get(PV_GROUP) or body.vertex_groups.new(name=PV_GROUP)
    M = np.array(rig.matrix_world)
    elbows = [np.array(rig.data.bones[f"forearm.{s}"].head_local) @ M[:3, :3].T + M[:3, 3] for s in "LR"]
    co = np.empty(len(body.data.vertices) * 3)
    body.data.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3) @ np.array(body.matrix_world)[:3, :3].T + np.array(body.matrix_world)[:3, 3]
    distance = np.min([np.linalg.norm(co - e, axis=1) for e in elbows], axis=0)
    u = np.clip((distance - ELBOW_RADIUS) / ELBOW_RADIUS, 0.0, 1.0)
    for i, w in enumerate(u * u * (3 - 2 * u)):
        group.add([i], float(w), "REPLACE")


def bone_angle(rig, a, b):
    return rig.pose.bones[a].matrix.to_quaternion().rotation_difference(rig.pose.bones[b].matrix.to_quaternion()).angle


def drivers_for(rig, keep, poses, joints, scene):
    """Per kept joint and side: the two bones, and their angle at rest and in the test's pose."""
    out = {}
    for joint in keep:
        for s in "LR":
            a, b = (x.format(s=s) for x in PAIRS[joint])
            scene.frame_set(1)
            bpy.context.view_layer.update()
            rest = bone_angle(rig, a, b)
            scene.frame_set(poses[joints[joint]]["frame"])
            bpy.context.view_layer.update()
            out[f"{joint}.{s}"] = {"a": a, "b": b, "rest": rest, "pose": bone_angle(rig, a, b)}
    scene.frame_set(1)
    return out


def apply(body, rig, deltas, definitions, rest_x):
    """One shape key per joint and side, holding the correction only on that side of the body, driven from 0 at rest to 1 at the test's pose."""
    if body.data.shape_keys is None:
        body.shape_key_add(name="Basis", from_mix=False)
    basis = np.empty(len(body.data.vertices) * 3)
    body.data.shape_keys.key_blocks[0].data.foreach_get("co", basis)
    basis = basis.reshape(-1, 3)
    M = np.array(body.matrix_world)[:3, :3]
    for joint, delta in deltas.items():
        for s in "LR":
            kb = body.data.shape_keys.key_blocks.get(f"fix.{joint}.{s}") or body.shape_key_add(name=f"fix.{joint}.{s}", from_mix=False)
            side = rest_x > 0 if s == "L" else rest_x <= 0
            local = (delta * side[:, None]) @ M  # world to object axes
            co = basis.copy()
            co[: len(delta)] += local
            kb.data.foreach_set("co", co.ravel())
            kb.slider_min, kb.slider_max = 0.0, 1.0
            kb.driver_remove("value")
            d = kb.driver_add("value").driver
            d.type = "SCRIPTED"
            v = d.variables.new()
            v.name, v.type = "x", "ROTATION_DIFF"
            info = definitions[f"{joint}.{s}"]
            for target, bone in zip(v.targets, (info["a"], info["b"])):
                target.id, target.bone_target = rig, bone
            span = info["pose"] - info["rest"]
            d.expression = f"min(1,max(0,(x-({info['rest']:.5f}))/({span:.5f})))"

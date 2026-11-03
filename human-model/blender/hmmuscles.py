"""Muscle bodies on their own armature, and the fields as shape keys driven by activation.
The muscle armature follows the main rig and the skin, and nothing depends on it, so it can't make a dependency cycle."""
import math
import bpy
import numpy as np
from mathutils import Vector
import hmblender as hb

RINGS, SIDES = 6, 8
GROUP_COLOR = {"face": (0.62, 0.16, 0.14), "jaw": (0.55, 0.13, 0.13), "tongue": (0.72, 0.32, 0.36), "trunk": (0.60, 0.14, 0.14), "leg": (0.60, 0.15, 0.13)}


def profile(u):
    x = max(0.0, min(1.0, (u - 0.12) / 0.76))
    return 0.12 + 0.88 * math.sin(math.pi * x) ** 0.9


def add_fields(body, ctrl, muscles, fields, rig):
    """One shape key per muscle and per body shape, each driven by a control of the same name."""
    if not body.data.shape_keys:
        body.shape_key_add(name="Basis")
    ids = fields["ids"]
    basis = np.empty(len(body.data.vertices) * 3)
    body.data.shape_keys.reference_key.data.foreach_get("co", basis)
    basis = basis.reshape(-1, 3)
    M = np.array(body.matrix_world)[:3, :3]
    Minv = np.linalg.inv(M)

    def add(name, idx, disp, prop, lo=0.0, hi=1.0):
        key = body.shape_key_add(name=name, from_mix=False)
        co = basis.copy()
        co[idx] += disp @ Minv.T
        key.data.foreach_set("co", co.ravel())
        key.slider_min, key.slider_max = lo, hi
        if prop not in ctrl:
            hb.add_prop(ctrl, prop)
        hb.drive(key, "value", None, ctrl, prop, "x")

    for k in fields.files:
        if k.startswith("F_"):
            add(k, ids, fields[k], f"m_{k[2:]}")
    for k in fields.files:
        if k.startswith("B_") and k.endswith("__ids"):
            name = k[2:-5]
            if name == "breath":
                add("B_breath", fields[k], fields[f"B_{name}__d"], "breath")
            else:
                add(f"B_{name}", fields[k], fields[f"B_{name}__d"], f"b_{name}")
    # body shapes follow the joints: elbow bend for biceps and triceps, arm raised for the deltoid
    for side in "LR":
        for name, ref, lo, span in (("biceps", (f"upper_arm.{side}", f"forearm.{side}"), 0.8, 1.4), ("triceps", (f"upper_arm.{side}", f"forearm.{side}"), 0.8, 1.4)):
            drive_angle(body.data.shape_keys.key_blocks[f"B_{name}_{side}"], rig, ref, lo, span)
        drive_angle(body.data.shape_keys.key_blocks[f"B_deltoid_{side}"], rig, (f"upper_arm.{side}", "spine.003"), 0.6, 1.2)


def drive_angle(key, rig, bones, start, span):
    key.driver_remove("value")
    d = key.driver_add("value")
    d.driver.type = "SCRIPTED"
    v = d.driver.variables.new()
    v.name = "a"
    v.type = "ROTATION_DIFF"
    v.targets[0].id = rig
    v.targets[0].bone_target = bones[0]
    v.targets[1].id = rig
    v.targets[1].bone_target = bones[1]
    d.driver.expression = f"max(min((a-{start})/{span},1),0)"


def add_muscle_bodies(rig, skin, ctrl, muscles):
    col = hb.collection("HM_muscles")
    arm = bpy.data.armatures.new("HM_muscle_rig")
    mrig = bpy.data.objects.new("HM_muscle_rig", arm)
    col.objects.link(mrig)
    bpy.context.view_layer.objects.active = mrig
    mrig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    segments = []
    for m in muscles:
        pts = m["points"]
        lengths = [0.0]
        for i in range(len(pts) - 1):
            lengths.append(lengths[-1] + (Vector(pts[i + 1]) - Vector(pts[i])).length)
        total = lengths[-1] or 1.0
        for i in range(len(pts) - 1):
            p0, p1 = Vector(pts[i]), Vector(pts[i + 1])
            if (p1 - p0).length < 0.002:
                continue
            bname = f"{m['name']}.{i}"
            eb = arm.edit_bones.new(bname)
            eb.head, eb.tail = p0, p1
            segments.append((m, i, bname, lengths[i] / total, lengths[i + 1] / total))
    bpy.ops.object.mode_set(mode="OBJECT")

    empties = {}
    ecol = hb.collection("HM_muscle_targets")

    def target(point, parent):
        key = (round(point[0], 4), round(point[1], 4), round(point[2], 4), parent)
        if key in empties:
            return empties[key]
        e = bpy.data.objects.new(f"t{len(empties)}", None)
        e.empty_display_size = 0.003
        ecol.objects.link(e)
        e.location = point
        if parent.startswith("skin:"):
            e.parent = skin
            e.parent_type = "VERTEX"
            e.parent_vertices = (int(parent.split(":")[1]), 0, 0)
            bpy.context.view_layer.update()
            e.matrix_parent_inverse.identity()
            # vertex-parented locations are relative to the vertex
            e.location = (0, 0, 0)
        else:
            bone = rig.data.bones[parent]
            e.parent = rig
            e.parent_type = "BONE"
            e.parent_bone = parent
            bpy.context.view_layer.update()
            e.matrix_world = Matrix_translation(point)
        empties[key] = e
        return e

    verts, faces, groups = [], [], []
    for m, i, bname, u0, u1 in segments:
        pb = mrig.pose.bones[bname]
        start = target(m["points"][i], m["parents"][i])
        end = target(m["points"][i + 1], m["parents"][i + 1])
        c = pb.constraints.new("COPY_LOCATION")
        c.target = start
        s = pb.constraints.new("STRETCH_TO")
        s.target = end
        s.volume = "VOLUME_XZX"
        s.bulge = 1.0
        s.rest_length = (Vector(m["points"][i + 1]) - Vector(m["points"][i])).length
        p0, p1 = Vector(m["points"][i]), Vector(m["points"][i + 1])
        axis = (p1 - p0).normalized()
        ref = Vector((0, 0, 1)) if abs(axis.z) < 0.9 else Vector((1, 0, 0))
        ax = axis.cross(ref).normalized()
        ay = axis.cross(ax)
        base = len(verts)
        for k in range(RINGS):
            t = k / (RINGS - 1)
            r = m["radius"] * profile(u0 + (u1 - u0) * t)
            for q in range(SIDES):
                ang = 2 * math.pi * q / SIDES
                verts.append(tuple(p0 + (p1 - p0) * t + (ax * math.cos(ang) + ay * math.sin(ang)) * r))
        for k in range(RINGS - 1):
            for q in range(SIDES):
                n = (q + 1) % SIDES
                faces.append((base + k * SIDES + q, base + k * SIDES + n, base + (k + 1) * SIDES + n, base + (k + 1) * SIDES + q))
        faces.append(tuple(base + q for q in range(SIDES))[::-1])
        faces.append(tuple(base + (RINGS - 1) * SIDES + q for q in range(SIDES)))
        groups.append((bname, base, base + RINGS * SIDES))
    me = bpy.data.meshes.new("HM_muscles")
    me.from_pydata(verts, [], faces)
    me.update()
    ob = bpy.data.objects.new("HM_muscles", me)
    col.objects.link(ob)
    me.materials.append(hb.material("muscle", GROUP_COLOR["trunk"], roughness=0.5))
    for p in me.polygons:
        p.use_smooth = True
    for bname, a, b in groups:
        vg = ob.vertex_groups.new(name=bname)
        vg.add(list(range(a, b)), 1.0, "REPLACE")
    mod = ob.modifiers.new("arm", "ARMATURE")
    mod.object = mrig
    ob.parent = mrig
    mrig.hide_render = True
    print("muscle bodies", len(muscles), "segments", len(segments), "verts", len(verts))


def Matrix_translation(p):
    from mathutils import Matrix
    return Matrix.Translation(p)

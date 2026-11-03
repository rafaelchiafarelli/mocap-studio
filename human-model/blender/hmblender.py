"""Shared helpers for scripts that run inside Blender."""
import json
import bpy
import numpy as np


def args():
    import sys
    return sys.argv[sys.argv.index("--") + 1:]


def clear_scene():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)


def mesh_object(name, verts, faces, collection, color=None, material=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.asarray(verts, float).tolist(), [], np.asarray(faces).tolist())
    me.update()
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    if material:
        me.materials.append(material)
    return ob


def collection(name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(c)
    return c


def material(name, color, alpha=1.0, roughness=0.6):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = roughness
    if alpha < 1.0:
        b.inputs["Alpha"].default_value = alpha
    return m


def decimate(ob, max_faces):
    n = len(ob.data.polygons)
    if n <= max_faces:
        return
    mod = ob.modifiers.new("d", "DECIMATE")
    mod.ratio = max_faces / n
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    ob.modifiers.remove(mod)
    old = ob.data
    ob.data = new
    bpy.data.meshes.remove(old)


def parent_to_bone(ob, rig, bone):
    """Keeps the object where it is in the world."""
    world = ob.matrix_world.copy()
    ob.parent = rig
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = world


def controls_object(name="HM_controls"):
    c = bpy.data.objects.get(name)
    if c is None:
        c = bpy.data.objects.new(name, None)
        bpy.context.scene.collection.objects.link(c)
    return c


def add_prop(ctrl, name, default=0.0, lo=0.0, hi=1.0):
    ctrl[name] = default
    ui = ctrl.id_properties_ui(name)
    ui.update(min=lo, max=hi, soft_min=lo, soft_max=hi)


def drive(target, path, index, ctrl, prop, expression):
    """A simple-expression driver from a control property (no scripts run, so auto-run can stay off)."""
    d = target.driver_add(path, index) if index is not None else target.driver_add(path)
    d.driver.type = "SCRIPTED"
    v = d.driver.variables.new()
    v.name = "x"
    v.targets[0].id = ctrl
    v.targets[0].data_path = f'["{prop}"]'
    d.driver.expression = expression
    return d


def world_verts(ob):
    n = len(ob.data.vertices)
    c = np.empty(n * 3)
    ob.data.vertices.foreach_get("co", c)
    c = c.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    return c @ M[:3, :3].T + M[:3, 3]


def evaluated_verts(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = ob.evaluated_get(dg).to_mesh()
    n = len(me.vertices)
    c = np.empty(n * 3)
    me.vertices.foreach_get("co", c)
    ob.evaluated_get(dg).to_mesh_clear()
    c = c.reshape(-1, 3)
    M = np.array(ob.matrix_world)
    return c @ M[:3, :3].T + M[:3, 3]


def camera_look(name, location, target, lens=50):
    from mathutils import Vector
    cam = bpy.data.objects.get(name) or bpy.data.objects.new(name, bpy.data.cameras.new(name))
    if cam.name not in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.link(cam)
    cam.location = location
    cam.data.lens = lens
    cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()
    return cam


def setup_render(res=(1000, 1400), samples=32, engine="BLENDER_EEVEE"):
    s = bpy.context.scene
    s.render.engine = engine
    s.render.resolution_x, s.render.resolution_y = res
    s.render.film_transparent = False
    if engine.startswith("BLENDER_EEVEE"):
        s.eevee.taa_render_samples = samples
    s.world = s.world or bpy.data.worlds.new("w")
    s.world.use_nodes = True
    s.world.node_tree.nodes["Background"].inputs[0].default_value = (0.9, 0.9, 0.9, 1)
    s.world.node_tree.nodes["Background"].inputs[1].default_value = 0.8
    if "HM_sun" not in bpy.data.objects:
        sun = bpy.data.objects.new("HM_sun", bpy.data.lights.new("HM_sun", "SUN"))
        sun.data.energy = 3.0
        sun.rotation_euler = (0.9, 0.2, -0.5)
        s.collection.objects.link(sun)


def render(path, cam=None):
    if cam:
        bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)

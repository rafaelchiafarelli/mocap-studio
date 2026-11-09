"""Compares ways of binding skin to what moves it, on one smile, against the direct field. Args: out.json. Run with --blend a built model.
Direct field: the shape key. Surface Deform and Mesh Deform carry the same motion through a coarse shell."""
import json, os, sys, time
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
out = hb.args()[0]
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
keys = skin.data.shape_keys.key_blocks
names = [f"F_zygomaticus_major_{s}" for s in "LR"]
basis = hb.world_verts(skin)
n = len(skin.data.vertices)


def key_co(k):
    a = np.empty(n * 3)
    keys[k].data.foreach_get("co", a)
    return a.reshape(-1, 3)


b = key_co("Basis")
field = sum(key_co(k) - b for k in names)
head = np.flatnonzero(b[:, 2] > 1.45)[:]
head = head[head < 13380]
index = {v: i for i, v in enumerate(head)}
faces = [[index[v] for v in p.vertices] for p in skin.data.polygons if all(v in index for v in p.vertices)]
col = hb.collection("HM_binding_test")


def new_copy(name, co):
    return hb.mesh_object(name, co, faces, col)


results = {}
target = b[head] + field[head]


def shell(name, target_faces, inflate=0.0):
    o = new_copy(name, b[head])
    m = o.modifiers.new("d", "DECIMATE")
    m.ratio = target_faces / len(o.data.polygons)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), depsgraph=dg)
    o.modifiers.remove(m)
    o.data = me
    co = np.array([v.co[:] for v in me.vertices])
    if inflate:
        nrm = np.array([v.normal[:] for v in me.vertices])
        co += nrm * inflate
    me.vertices.foreach_set("co", co.ravel())
    me.update()
    from scipy_free_nearest import nearest
    return o, co, nearest(co, b[head])


def activate(o):
    bpy.context.view_layer.objects.active = o
    for x in bpy.context.selected_objects:
        x.select_set(False)
    o.select_set(True)


def run(label, mod_type, shell_faces, inflate, bind):
    res = {}
    t0 = time.perf_counter()
    sh, sh_co, near = shell(f"shell_{label}", shell_faces, inflate)
    probe = new_copy(f"probe_{label}", b[head])
    mod = probe.modifiers.new("bind", mod_type)
    if mod_type == "SURFACE_DEFORM":
        mod.target = sh
    else:
        mod.object = sh
        mod.precision = 4
    activate(probe)
    t1 = time.perf_counter()
    bind(mod)
    t2 = time.perf_counter()
    bpy.context.view_layer.update()
    sh_new = sh_co + field[head][near]
    sh.data.vertices.foreach_set("co", sh_new.ravel())
    sh.data.update()
    bpy.context.view_layer.update()
    t3 = time.perf_counter()
    got = hb.evaluated_verts(probe)
    t4 = time.perf_counter()
    err = np.linalg.norm(got - target, axis=1)
    res = {"shell_faces": len(sh.data.polygons), "bound": bool(getattr(mod, "is_bound", True)), "bind_s": t2 - t1, "eval_s": t4 - t3, "rms_mm": float(np.sqrt((err ** 2).mean()) * 1000), "max_mm": float(err.max() * 1000)}
    results[label] = res
    print(label, res)


def bind_surface(mod):
    bpy.ops.object.surfacedeform_bind(modifier=mod.name)


def bind_mesh(mod):
    bpy.ops.object.meshdeform_bind(modifier=mod.name)


t0 = time.perf_counter()
probe0 = new_copy("direct", b[head] + field[head])
results["direct_shape_key"] = {"rms_mm": 0.0, "max_mm": 0.0, "bind_s": 0.0, "eval_s": 0.0, "note": "reference: the field itself"}
run("surface_deform_fine", "SURFACE_DEFORM", 6000, 0.0, bind_surface)
run("surface_deform_coarse", "SURFACE_DEFORM", 1500, 0.0, bind_surface)
try:
    run("mesh_deform_coarse", "MESH_DEFORM", 1500, 0.012, bind_mesh)
except Exception as e:
    results["mesh_deform_coarse"] = {"error": str(e)[:200]}
    print("mesh deform failed", e)
json.dump(results, open(out, "w"), indent=0)

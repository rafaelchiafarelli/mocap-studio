"""Puts the catalogue of folds on a body as shape keys that follow the pose. Run with --blend. Args: folds.json out.blend
Each fold gets a dent along its line, with a small bulge beside it, and a driver from its bone's rotation. HM_controls has one fader per fold (fold_<name>, 0 to 3) and fold_fat (0 to 1) for all of them. Drivers are plain expressions, so auto-run can stay off."""
import json, os, sys
import bpy
import numpy as np
HERE = os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1]))
sys.path[:0] = [HERE, os.path.dirname(HERE)]
import hmblender as hb
import posed_mesh as pm
from hmcore import deltamush as dm
from hmcore import folds as fd

a = hb.args()
catalogue = json.load(open(a[0], encoding="utf-8"))["folds"]
rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
pm.set_display(body, False)
rig.data.pose_position = "REST"
bpy.context.view_layer.update()
rest = pm.read(body)[: pm.N_BODY]
rig.data.pose_position = "POSE"
bpy.context.view_layer.update()
tris = pm.triangles(body)
edges = fd.edges_of(tris)
normals = dm.vertex_normals(rest, tris)
if body.data.shape_keys is None:
    body.shape_key_add(name="Basis", from_mix=False)
basis = np.empty(len(body.data.vertices) * 3)
body.data.shape_keys.key_blocks[0].data.foreach_get("co", basis)
basis = basis.reshape(-1, 3)
to_object = np.array(body.matrix_world.inverted())[:3, :3]
ctrl = hb.controls_object("HM_controls")
hb.add_prop(ctrl, "fold_fat", 0.5, 0.0, 1.0)
AXIS = {"X": "ROT_X", "Y": "ROT_Y", "Z": "ROT_Z"}
for fold in catalogue:
    label = fold["name"] + (f"_{fold['side']}" if fold["side"] else "")
    width, depth = fold["width_cm"] / 100.0, fold["depth_mm"] / 1000.0
    distance = fd.surface_distance(rest, edges, fold["vertices"], 3.0 * width)
    shape = fd.profile(distance, width)
    delta = -normals * (shape * depth)[:, None]
    co = basis.copy()
    co[: pm.N_BODY] += delta @ to_object.T
    name = f"fold.{label}"
    kb = body.data.shape_keys.key_blocks.get(name) or body.shape_key_add(name=name, from_mix=False)
    kb.data.foreach_set("co", co.ravel())
    kb.slider_min, kb.slider_max = 0.0, 3.0
    prop = f"fold_{label}"
    hb.add_prop(ctrl, prop, 1.0, 0.0, 3.0)
    kb.driver_remove("value")
    d = kb.driver_add("value").driver
    d.type = "SCRIPTED"
    v = d.variables.new()
    v.name, v.type = "x", "TRANSFORMS"
    t = v.targets[0]
    t.id, t.bone_target, t.transform_type, t.transform_space, t.rotation_mode = rig, fold["driver"]["bone"], AXIS[fold["driver"]["axis"]], "LOCAL_SPACE", "XYZ"
    for var, path in (("g", f'["{prop}"]'), ("f", '["fold_fat"]')):
        w = d.variables.new()
        w.name = var
        w.targets[0].id, w.targets[0].data_path = ctrl, path
    e0, e1, r = fold["driver"]["rest"], fold["driver"]["deep"], fold["at_rest"]
    d.expression = f"({r:.3f}+(1-{r:.3f})*min(1,max(0,(x-({e0:.5f}))/({e1 - e0:.5f}))))*g*(0.4+1.2*f)"
pm.set_display(body, True)
bpy.ops.wm.save_as_mainfile(filepath=a[1])
print("folds", len(catalogue))

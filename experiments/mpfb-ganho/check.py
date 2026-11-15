"""Checks the installed add-on without its interface, on a file with an MPFB human. Args: out.json
Sets sliders past 1 through the scene properties MPFB's panels draw, measures the skin, and resets."""
import json, sys
import bpy
import numpy as np
a = sys.argv[sys.argv.index("--") + 1:]
import importlib
g = importlib.import_module("bl_ext.user_default.mpfb_ganho")
assert g.apply(), "MPFB not ready"
body = next(o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Human"))
bpy.context.view_layer.objects.active = body
body.select_set(True)
scene = bpy.context.scene


def verts():
    dg = bpy.context.evaluated_depsgraph_get()
    m = body.evaluated_get(dg).to_mesh()
    v = np.array([x.co[:] for x in m.vertices[:13380]])
    body.evaluated_get(dg).to_mesh_clear()
    return v


def height():
    v = verts()
    return float(v[:, 2].max() - v[:, 2].min())


base = verts()
report = {"properties": g._state["properties"], "rest_height": height()}
pm = "mpfb_macropanel_"
rows = {}
for name, values in {"weight": [0.0, 0.5, 1.0, 2.0, 3.0, -1.0], "height": [1.0, 3.0, -3.0], "gender": [1.0, 3.0, -2.0], "african": [3.0, -1.0]}.items():
    for v in values:
        g.reset_human(body)
        setattr(scene, pm + name, v)
        got = getattr(scene, pm + name)
        rows[f"{name}={v}"] = {"read": round(got, 4), "height_m": round(height(), 4), "move_mm": round(float(np.abs(verts() - base).max()) * 1000, 1)}
    setattr(scene, pm + name, 0.5 if name != "african" else 0.33)
report["macros"] = rows
names = [p.identifier for p in bpy.types.Scene.bl_rna.properties]
mods = [n for n in names if n.startswith("nose_")][:3] + [n for n in names if n.startswith("torso_")][:2] + [n for n in names if n.startswith("armslegs_") and "_l_" in n][:1]
mrows = {}
for ident in mods:
    p = bpy.types.Scene.bl_rna.properties[ident]
    for v in [1.0, 3.0, -3.0]:
        setattr(scene, ident, v)
        mrows[f"{ident}={v}"] = {"read": round(getattr(scene, ident), 4), "range": [p.hard_min, p.hard_max], "move_mm": round(float(np.abs(verts() - base).max()) * 1000, 1)}
        g.reset_human(body)
report["modifiers"] = mrows
setattr(scene, pm + "weight", 2.5)
setattr(scene, mods[0], 2.5)
removed = g.reset_human(body)
report["reset"] = {"removed": removed, "weight": getattr(scene, pm + "weight"), "move_mm": round(float(np.abs(verts() - base).max()) * 1000, 3), "keys": [k.name for k in body.data.shape_keys.key_blocks]}
json.dump(report, open(a[0], "w"), indent=1)
print(json.dumps(report, indent=1))

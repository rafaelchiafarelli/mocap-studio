"""Tissue add-on on a skin patch: can it give surface pattern or micro relief at a cost we can pay? Args: addon.zip out_prefix. Run with --blend a built model. Doesn't change the file."""
import json, os, sys, time
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
a = hb.args()
zip_path, prefix = a[0], a[1]
report = {}
try:
    bpy.ops.extensions.package_install_files(filepath=zip_path, repo="user_default", enable_on_install=True)
    report["install"] = "ok"
except Exception as e:
    report["install"] = str(e)[:300]
print("install", report["install"])
import addon_utils
mods = [m.__name__ for m in addon_utils.modules() if "tissue" in m.__name__.lower()]
print("modules", mods)
if mods:
    addon_utils.enable(mods[0], default_set=False)
report["operators"] = [o for o in dir(bpy.ops.object) if "tessell" in o or "tissue" in o][:10]
print(report["operators"])
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
# a forehead and cheek patch of the skin as the base, a small pyramid as the pore unit
verts = hb.world_verts(skin)
rig = bpy.data.objects["HM_rig"]
top = (rig.matrix_world @ rig.data.bones["nose"].head_local)
ids = np.flatnonzero((verts[:, 2] > top.z + 0.01) & (verts[:, 2] < top.z + 0.07) & (np.abs(verts[:, 0]) < 0.05) & (verts[:, 1] < top.y + 0.05) & (np.arange(len(verts)) < 13380))
index = {v: i for i, v in enumerate(ids)}
faces = [[index[v] for v in p.vertices] for p in skin.data.polygons if all(v in index for v in p.vertices)]
col = hb.collection("HM_tissue_test")
base = hb.mesh_object("tissue_base", verts[ids], faces, col)
unit_v = [(-.5, -.5, 0), (.5, -.5, 0), (.5, .5, 0), (-.5, .5, 0), (0, 0, .4)]
unit_f = [(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4)]
unit = hb.mesh_object("tissue_unit", unit_v, unit_f, col)
bpy.context.view_layer.objects.active = base
base.select_set(True)
report["base_faces"] = len(base.data.polygons)
t0 = time.perf_counter()
try:
    r = bpy.ops.object.tissue_tessellate(component=unit.name) if "tissue_tessellate" in report["operators"] else bpy.ops.object.tissue_update_tessellate()
    report["tessellate"] = list(r)
except Exception as e:
    report["tessellate"] = "failed: " + str(e)[:300]
report["seconds"] = time.perf_counter() - t0
made = [o for o in bpy.data.objects if o.name.startswith(("tissue_base", "Tessellate")) and o is not base]
report["result_objects"] = [(o.name, len(o.data.vertices)) for o in made if o.type == "MESH"]
json.dump(report, open(prefix + "_tissue.json", "w"), indent=0)
print(report)

"""Builds an MPFB human from a recipe and exports what the fit needs. Args: recipe.json out.npz [out.json]
The recipe: {"macros": {...}}. Output: skin verts and faces, joint table, vertex groups."""
import json, sys
import addon_utils, bpy
import numpy as np
args = sys.argv[sys.argv.index("--") + 1:]
recipe = json.load(open(args[0], encoding="utf-8"))
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
body = HumanService.create_human(macro_detail_dict=recipe["macros"])
rig = HumanService.add_builtin_rig(body, "rigify.human")
dg = bpy.context.evaluated_depsgraph_get()
mesh = body.evaluated_get(dg).to_mesh()
n = len(mesh.vertices)
co = np.empty(n * 3, dtype=np.float32)
mesh.vertices.foreach_get("co", co)
co = co.reshape(-1, 3) @ np.array(body.matrix_world)[:3, :3].T.astype(np.float32) + np.array(body.matrix_world)[:3, 3].astype(np.float32)
loops = np.empty(len(mesh.loops), dtype=np.int32)
mesh.loops.foreach_get("vertex_index", loops)
starts = np.empty(len(mesh.polygons), dtype=np.int32)
mesh.polygons.foreach_get("loop_start", starts)
sizes = np.empty(len(mesh.polygons), dtype=np.int32)
mesh.polygons.foreach_get("loop_total", sizes)
M = np.array(rig.matrix_world)
bones = {b.name: {"head": (M[:3, :3] @ np.array(b.head_local) + M[:3, 3]).tolist(), "tail": (M[:3, :3] @ np.array(b.tail_local) + M[:3, 3]).tolist(), "parent": b.parent.name if b.parent else None} for b in rig.data.bones}
groups = {}
for g in body.vertex_groups:
    groups[g.name] = []
for v in body.data.vertices:
    for g in v.groups:
        if g.weight > 0:
            groups[body.vertex_groups[g.group].name].append([v.index, g.weight])
np.savez_compressed(args[1], verts=co, loops=loops, starts=starts, sizes=sizes)
json.dump({"bones": bones, "groups": groups, "macros": recipe["macros"], "shape_keys": [k.name for k in (body.data.shape_keys.key_blocks if body.data.shape_keys else [])]}, open(args[2], "w"))
print("verts", n, "bones", len(bones), "groups", len(groups))

"""Step 11a: the rigged body at rest, as arrays for the tetrahedral tissue, and the same body with no breasts.

    python3 human-model/blender_run.py --blend 02_corpo_com_rig.blend human-model/investigations/pose-capture/tissue_export.py OUT.npz

OUT.npz: `skin` (13,380 x 3, rest, world, shape keys on, no pose), `flat` (the same vertices with MPFB's cup size at its least
and the breast and nipple targets at zero: the chest without breasts, from which each breast's volume is cut), `tris`
(body triangles), `bone_names`, `bone_head`, `bone_tail`, `bone_matrix` (rest, armature space = world here), `bone_parent`, and
`weights` (13,380 x bones) the skin's deform weights per rig bone, and `sub_verts`, `sub_faces` (quads): the skin with
helpers masked and subdivided twice, at rest, for the simulated skin. The file isn't saved: the cup change stays in memory.
"""
import os, sys
import addon_utils, bpy
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])), "..", "..", "blender"))
import posed_mesh as pm

out = sys.argv[sys.argv.index("--") + 1:][0]
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.entities.objectproperties import HumanObjectProperties

rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
rig.data.pose_position = "REST"
pm.set_display(body, False)
bpy.context.view_layer.update()
skin = pm.read(body)[: pm.N_BODY]
tris = pm.triangles(body)

names = [b.name for b in rig.data.bones if b.use_deform]
index = {n: i for i, n in enumerate(names)}
W = np.zeros((pm.N_BODY, len(names)), np.float32)
groups = {g.index: g.name for g in body.vertex_groups}
for v in body.data.vertices[: pm.N_BODY]:
    for g in v.groups:
        n = groups[g.group]
        if n in index:
            W[v.index, index[n]] = g.weight
R = np.array(rig.matrix_world)
head = np.array([R[:3, :3] @ np.array(rig.data.bones[n].head_local) + R[:3, 3] for n in names])
tail = np.array([R[:3, :3] @ np.array(rig.data.bones[n].tail_local) + R[:3, 3] for n in names])
mats = np.array([R @ np.array(rig.data.bones[n].matrix_local) for n in names])
parents = [rig.data.bones[n].parent.name if rig.data.bones[n].parent else "" for n in names]

# the skin subdivided twice (Catmull-Clark, Blender's Subsurf after the Mask), at rest: MPFB's own skin has only about 4,000
# vertices on the trunk and limbs, a vertex every ~2 cm, too coarse to show what 3 mm tetrahedra do
for m in body.modifiers:
    if m.type == "MASK":
        m.show_viewport = True
sub = body.modifiers.new("tissue_sub", "SUBSURF")
sub.levels = 2
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(dg)
me = ev.to_mesh()
sv = np.empty(len(me.vertices) * 3)
me.vertices.foreach_get("co", sv)
sv = sv.reshape(-1, 3) @ np.array(body.matrix_world)[:3, :3].T + np.array(body.matrix_world)[:3, 3]
sub_faces = np.array([list(p.vertices) for p in me.polygons], np.int32)
ev.to_mesh_clear()
body.modifiers.remove(sub)
pm.set_display(body, False)
bpy.context.view_layer.update()

# the chest without breasts: least cup, and the breast and nipple targets off
before = HumanObjectProperties.get_value("cupsize", entity_reference=body)
HumanObjectProperties.set_value("cupsize", 0.0, entity_reference=body)
TargetService.reapply_macro_details(body)
off = []
for k in body.data.shape_keys.key_blocks:
    if k.name.startswith(("breast-", "nipple-")) or "breast" in k.name.lower() and not k.name.startswith("$md"):
        off.append((k.name, k.value))
        k.value = 0.0
bpy.context.view_layer.update()
flat = pm.read(body)[: pm.N_BODY]
moved = np.linalg.norm(flat - skin, axis=1)
np.savez_compressed(out, skin=skin.astype(np.float32), flat=flat.astype(np.float32), tris=tris.astype(np.int32),
                    bone_names=np.array(names), bone_head=head.astype(np.float32), bone_tail=tail.astype(np.float32),
                    bone_matrix=mats.astype(np.float32), bone_parent=np.array(parents), weights=W,
                    sub_verts=sv.astype(np.float32), sub_faces=sub_faces)
print({"cupsize_was": before, "targets_off": off, "flat_moved_mm_max": float(moved.max() * 1000),
       "vertices_moved_over_2mm": int((moved > 0.002).sum()), "bones": len(names), "sub_verts": len(sv), "sub_faces": len(sub_faces)})

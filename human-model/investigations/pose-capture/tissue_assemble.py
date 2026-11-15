"""Step 11e: the simulated skin into the moving body's file, for Blender and for stage_video.py.

    python3 human-model/blender_run.py --blend 07_movimento_duas_cameras_31-43s.blend human-model/investigations/pose-capture/tissue_assemble.py TECIDOS.npz PELE.pc2 OUT.blend

Adds `HM_pele_simulada`: tissue_mesh.py's shown skin (MPFB's skin subdivided twice, trunk and limbs) played by a Mesh Cache
modifier from PELE.pc2 (tissue_sim.py), path relative to OUT.blend. HM_body keeps head, hands and feet, skinned by the rig as
before: a second Mask modifier hides the simulated part, but keeps two rings of faces past the cut so the seam doesn't open.
"""
import os, sys
import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
m = np.load(a[0])
pc2, out = a[1], a[2]
body = bpy.data.objects["HM_body"]
verts, faces = m["sub_rest"].astype(float), m["sub_faces"]

me = bpy.data.meshes.new("HM_pele_simulada")
me.from_pydata(verts.tolist(), [], faces.tolist())
me.update()
for p in me.polygons:
    p.use_smooth = True
ob = bpy.data.objects.new("HM_pele_simulada", me)
bpy.context.scene.collection.objects.link(ob)
for mat in body.data.materials:
    me.materials.append(mat)
mc = ob.modifiers.new("simulacao", "MESH_CACHE")
mc.cache_format = "PC2"
# relative to the open file: saving as OUT remaps it to OUT's folder. Made relative to OUT's folder, the save remapped it a second
# time, and with the motion in another folder (tet_v7_movimento/) the cache wasn't found and the skin stood still at frame 1
mc.filepath = bpy.path.relpath(pc2)
mc.frame_start = bpy.context.scene.frame_start
mc.forward_axis, mc.up_axis = "POS_Y", "POS_Z"

# the body shows only what isn't simulated, and two rings into it
patch = np.zeros(13380, bool)
patch[m["skin_ids"]] = True
tri = m["patch"]
keep = ~patch
for _ in range(2):
    near = np.zeros(13380, bool)
    for p in body.data.polygons:
        v = [i for i in p.vertices if i < 13380]
        if v and keep[v].any():
            near[v] = True
    keep |= near
g = body.vertex_groups.new(name="fora_da_simulacao")
g.add(np.flatnonzero(keep).tolist(), 1.0, "REPLACE")
helpers = list(range(13380, len(body.data.vertices)))
mask = body.modifiers.new("so_fora_da_simulacao", "MASK")
mask.vertex_group = g.name
# keep the original helper mask in charge of the helpers: they aren't in the new group, so they stay hidden
bpy.ops.wm.save_as_mainfile(filepath=out)
print("simulated skin", len(verts), "vertices,", len(faces), "faces; body keeps", int(keep.sum()), "vertices; cache", mc.filepath)

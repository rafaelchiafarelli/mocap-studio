"""Step 17c: the simulated clothes into a file that already has the simulated skin (tissue_assemble.py's, staged or not).

    python3 human-model/blender_run.py --blend IN.blend human-model/investigations/pose-capture/dress_assemble.py VESTIDA.blend SIM_DIR PECAS OUT.blend [ROUPAS.json]

VESTIDA.blend: dress_rest.py's (its HM_<piece> objects, materials and textures are appended). SIM_DIR: tissue_cloth_sim.py's,
with <piece>.pc2 for each piece in PECAS (comma list), played by a Mesh Cache modifier; HM_pele_simulada's cache is pointed
at SIM_DIR's pele.pc2 too. With ROUPAS.json, each piece is shown with its `espessura_mm` (solver_tetraedros) by a Solidify
modifier centred on the simulated surface (Rafael, 2026-11-15: the clothes are 2 mm thick). Every path is written relative to OUT.blend (bpy.path.relpath had given tissue_assemble.py's skin a
path four folders up, which loaded nothing: the skin stood in the A pose, first test).
"""
import os, sys
import bpy

a = sys.argv[sys.argv.index("--") + 1:]


def rel(path):
    return "//" + os.path.relpath(os.path.abspath(path), os.path.dirname(os.path.abspath(out)))


dressed, sim_dir, pieces, out = a[0], a[1], a[2].split(","), a[3]
fabric = None
if len(a) > 4:
    import json
    fabric = json.load(open(a[4], encoding="utf-8"))["solver_tetraedros"]["pecas"]
names = ["HM_" + p for p in pieces]
with bpy.data.libraries.load(dressed, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n in names]
# Blender rewrites relative paths when it appends and again when it saves elsewhere, so paths are set absolute first and
# made relative to OUT after it is saved (computing them before the save left textures and skin cache four folders off)
paths = {}
for ob in dst.objects:
    bpy.context.scene.collection.objects.link(ob)
    mc = ob.modifiers.new("simulacao", "MESH_CACHE")
    mc.cache_format = "PC2"
    mc.frame_start = bpy.context.scene.frame_start
    mc.forward_axis, mc.up_axis = "POS_Y", "POS_Z"
    paths[mc] = os.path.join(sim_dir, ob.name[3:] + ".pc2")
    if fabric and ob.name[3:] in fabric:
        so = ob.modifiers.new("espessura", "SOLIDIFY")
        so.thickness = fabric[ob.name[3:]]["espessura_mm"] / 1000
        so.offset = 0.0
        so.use_even_offset = True
paths[bpy.data.objects["HM_pele_simulada"].modifiers["simulacao"]] = os.path.join(sim_dir, "pele.pc2")
images = {img: bpy.path.abspath(img.filepath) for img in bpy.data.images if img.name.startswith("female_casualsuit01")}
bpy.ops.wm.save_as_mainfile(filepath=out)
for holder, p in list(paths.items()) + list(images.items()):
    holder.filepath = rel(p)
for img in images:
    img.reload()
bpy.ops.wm.save_mainfile()
print("clothes", [o.name for o in dst.objects], "->", out, {h.name: h.filepath for h in list(paths) + list(images)})

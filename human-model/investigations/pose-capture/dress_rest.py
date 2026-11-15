"""Step 17a: the body dressed at rest (MPFB's A pose), for the tissue and cloth to be simulated together.

    python3 human-model/blender_run.py --blend 02_corpo_com_rig.blend \
        human-model/investigations/pose-capture/dress_rest.py CLOTHES_DIR OUT.blend OUT.npz [GAP_MM]

CLOTHES_DIR holds MPFB's female_casualsuit01 (CC0): its upper part becomes HM_blusinha, its lower HM_jeans. Each is fitted by
its mhclo on HM_body at rest (shape keys on, no pose: exactly MPFB's own fitting), subdivided once (edges ~1 cm), and any
vertex nearer the skin than GAP_MM (default 3) is pushed out to it. The skin is the one the tissue shows: MPFB's, masked and
subdivided twice (as tissue_export.py).

OUT.blend: the rest body with both pieces, textures in OUT's folder `<name>_texturas`. OUT.npz, per piece P:
`P_verts` (world, m), `P_tris` (the same vertices, triangulated), `P_quads_faces` and `P_quads_len` (the faces as shown).
Prints, per piece, how many vertices started inside the skin or nearer than the gap, and how deep.
"""
import json, os, shutil, sys
import bpy, bmesh
import numpy as np
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1]))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "blender"))
import mhclo_fit as mf
import posed_mesh as pm

a = sys.argv[sys.argv.index("--") + 1:]
cdir, out, out_npz = a[0], a[1], a[2]
GAP = (float(a[3]) if len(a) > 3 else 3.0) / 1000
SUIT = "female_casualsuit01"
PIECES = {"blusinha": "cima", "jeans": "baixo"}

rig, body = bpy.data.objects["HM_rig"], bpy.data.objects["HM_body"]
rig.data.pose_position = "REST"
pm.set_display(body, False)
bpy.context.view_layer.update()
rest = pm.read(body)  # helpers included: the suit hangs partly on them

scale, tri, w, d = mf.read_mhclo(os.path.join(cdir, SUIT + ".mhclo"))
faces, fuv, vt = mf.read_obj(os.path.join(cdir, SUIT + ".obj"))
X = mf.fit(rest, scale, tri, w, d)
part = mf.parts(X, faces)

# the shown skin at rest: masked, subdivided twice
for m in body.modifiers:
    if m.type == "MASK":
        m.show_viewport = True
sub = body.modifiers.new("vestir_sub", "SUBSURF")
sub.levels = 2
bpy.context.view_layer.update()
tree = BVHTree.FromObject(body, bpy.context.evaluated_depsgraph_get())
body.modifiers.remove(sub)
for m in body.modifiers:
    m.show_viewport = True


def signed(pts):
    d = np.empty(len(pts))
    nrm, near = np.zeros((len(pts), 3)), np.zeros((len(pts), 3))
    for i, p in enumerate(pts):
        loc, n, _, dist = tree.find_nearest(p)
        s = np.dot(np.array(p) - np.array(loc), np.array(n))
        d[i] = dist if s >= 0 else -dist
        nrm[i], near[i] = n, loc
    return d, nrm, near


tex_dir = os.path.join(os.path.dirname(out), os.path.splitext(os.path.basename(out))[0] + "_texturas")
os.makedirs(tex_dir, exist_ok=True)
for t in ("diffuse", "normal"):
    shutil.copy(os.path.join(cdir, f"{SUIT}_{t}.png"), tex_dir)


def image(name, colour):
    img = bpy.data.images.load(os.path.join(tex_dir, f"{SUIT}_{name}.png"))
    img.filepath = bpy.path.relpath(img.filepath, start=os.path.dirname(out))
    if not colour:
        img.colorspace_settings.name = "Non-Color"
    return img


mat = bpy.data.materials.new("HM_roupa")
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes.get("Principled BSDF")
tex = nt.nodes.new("ShaderNodeTexImage")
tex.image = image("diffuse", True)
nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
ntex = nt.nodes.new("ShaderNodeTexImage")
ntex.image = image("normal", False)
nmap = nt.nodes.new("ShaderNodeNormalMap")
nt.links.new(ntex.outputs["Color"], nmap.inputs["Color"])
nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
bsdf.inputs["Roughness"].default_value = 0.85
mat.diffuse_color = (0.25, 0.35, 0.6, 1)

arrays, report = {}, {"fonte": SUIT + " (MakeHuman system assets, CC0)", "folga_mm": GAP * 1000}
for name, which in PIECES.items():
    keep = part[which]
    idx = np.flatnonzero(keep)
    remap = -np.ones(len(X), int)
    remap[idx] = np.arange(len(idx))
    fsel = [k for k, f in enumerate(faces) if keep[f[0]]]
    me = bpy.data.meshes.new("HM_" + name)
    me.from_pydata(X[idx].tolist(), [], [[int(remap[i]) for i in faces[k]] for k in fsel])
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", np.concatenate([vt[fuv[k]] for k in fsel]).ravel())
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bm.to_mesh(me)
    bm.free()
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    dist, nrm, near = signed(V)
    push = dist < GAP
    report[name] = {"vertices": len(V), "dentro_da_pele": int((dist < 0).sum()),
                    "mais_fundo_mm": round(float(max(0.0, -dist.min())) * 1000, 1),
                    "mais_perto_que_a_folga": int(push.sum()),
                    "distancia_mediana_mm": round(float(np.median(dist)) * 1000, 1)}
    V[push] = near[push] + nrm[push] * GAP
    me.vertices.foreach_set("co", V.ravel())
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    me.update()
    ob = bpy.data.objects.new("HM_" + name, me)
    bpy.context.scene.collection.objects.link(ob)
    qf = [list(p.vertices) for p in me.polygons]
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    tris = np.array([[v.index for v in f.verts] for f in bm.faces], np.int32)
    bm.free()
    arrays[f"{name}_verts"] = V.astype(np.float32)
    arrays[f"{name}_tris"] = tris
    arrays[f"{name}_quads_faces"] = np.concatenate(qf).astype(np.int32)
    arrays[f"{name}_quads_len"] = np.array([len(f) for f in qf], np.int32)
    report[name]["area_m2"] = round(float(sum(p.area for p in me.polygons)), 3)

# show the body as the tissue does: subdivided twice. Unsubdivided, its coarse skin stands out of the smooth one on every
# curve and came through the top under the breasts and at the nipples (first run)
show = body.modifiers.new("como_o_tecido", "SUBSURF")
show.levels = show.render_levels = 2
np.savez_compressed(out_npz, **arrays)
bpy.ops.wm.save_as_mainfile(filepath=out)
print(json.dumps(report, indent=1))
json.dump(report, open(os.path.splitext(out_npz)[0] + ".json", "w"), indent=1)

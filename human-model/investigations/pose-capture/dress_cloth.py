"""Step 16: clothes on the step-12 body as cloth, the simulated skin pushing them (Rafael, 2026-11-14, option b).

    python3 human-model/blender_run.py --blend 12_cenario_tetraedros_v5.blend \
        human-model/investigations/pose-capture/dress_cloth.py CLOTHES_DIR ROUPAS.json PECAS OUT.blend REPORT.json [LAST_FRAME]

CLOTHES_DIR holds MPFB's female_casualsuit01 (.mhclo, .obj, textures; CC0). PECAS is a comma list of roupas.json's pieces
(blusinha, jeans). For each piece:

1. Fit: every clothes vertex is MPFB's mhclo rule, three body vertices weighted plus an offset scaled by the body's size
   (as MPFB's ClothesService.fit_clothes_to_human), read on HM_body posed in frame 1 (armature on, masks off); the offset
   turns with its triangle from rest to that pose. The suit is one mesh: its upper part is the top, its lower the jeans.
2. Subdivided once (edges ~1 cm), pushed out of the simulated skin of frame 1 to `folga_inicial_mm`; `encolhimento` shrinks the
   cloth's rest lengths, so it pulls over the body instead of following every hollow.
3. Pinned: vertices within `presa_*_mm` of the opening that holds the piece (neck for the top, waist for the jeans)
   follow HM_pele_simulada through a Surface Deform bound in frame 1; the rest is Blender cloth.
4. HM_pele_simulada and HM_body (head, hands, feet) collide; the cloth doesn't push back on them.
5. Cache (in memory, saved in OUT.blend) from frame 1 - acomodacao_quadros: before frame 1 the body stands still in frame 1's pose (the Mesh Cache and the
   action hold), so the cloth settles under gravity, then the dance runs.
   `massa_vertice_kg`, if given, replaces the mass from `gramatura_g_m2` (Blender's presets use 0.3 kg per vertex).

REPORT.json: vertices, pinned, pushed out at the start, bake time, and per 10 frames how many cloth vertices lie inside the
simulated skin and how deep.
"""
import json, os, sys, time
import bpy, bmesh
import numpy as np
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import mhclo_fit as mf

a = sys.argv[sys.argv.index("--") + 1:]
cdir, params_path, pieces, out, report_path = a[0], a[1], a[2].split(","), a[3], a[4]
LAST = int(a[5]) if len(a) > 5 else None  # a shorter run, for testing
P = json.load(open(params_path))
SUIT = "female_casualsuit01"
sc = bpy.context.scene
if LAST:
    sc.frame_end = LAST
body, skin = bpy.data.objects["HM_body"], bpy.data.objects["HM_pele_simulada"]


def evaluated(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    e = ob.evaluated_get(dg)
    me = e.to_mesh()
    c = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", c)
    e.to_mesh_clear()
    M = np.array(ob.matrix_world)
    return c.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]


def skin_tree():
    dg = bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(skin, dg)


def signed_dist(tree, pts):
    d = np.empty(len(pts))
    nrm = np.zeros((len(pts), 3))
    near = np.zeros((len(pts), 3))
    for i, p in enumerate(pts):
        loc, n, _, dist = tree.find_nearest(p)
        if loc is None:
            d[i] = 1.0
            continue
        s = np.dot(np.array(p) - np.array(loc), np.array(n))
        d[i] = dist if s >= 0 else -dist
        nrm[i], near[i] = n, loc
    return d, nrm, near


# --- the body in rest and in frame 1 ---------------------------------------------------------------------------------
sc.frame_set(1)
saved = {m.name: m.show_viewport for m in body.modifiers}
for m in body.modifiers:
    m.show_viewport = False
rest = evaluated(body)
for m in body.modifiers:
    m.show_viewport = m.type == "ARMATURE"
posed = evaluated(body)
for m in body.modifiers:
    m.show_viewport = saved[m.name]

scale, tri, wts, offs = mf.read_mhclo(os.path.join(cdir, SUIT + ".mhclo"))
faces, fuv, vt = mf.read_obj(os.path.join(cdir, SUIT + ".obj"))
X = mf.fit(rest, scale, tri, wts, offs, posed=posed)

# the suit's upper part is the top, the lower the jeans
part_mask = mf.parts(X, faces)

# textures beside the output
tex_dir = os.path.join(os.path.dirname(out), os.path.splitext(os.path.basename(out))[0] + "_texturas")
os.makedirs(tex_dir, exist_ok=True)
import shutil
for t in ("diffuse", "normal"):
    shutil.copy(os.path.join(cdir, f"{SUIT}_{t}.png"), tex_dir)


def make_material():
    mat = bpy.data.materials.get("HM_roupa") or bpy.data.materials.new("HM_roupa")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    img = nt.nodes.new("ShaderNodeTexImage")
    img.image = bpy.data.images.load(os.path.join(tex_dir, f"{SUIT}_diffuse.png"))
    img.image.filepath = bpy.path.relpath(img.image.filepath, start=os.path.dirname(out))
    nt.links.new(img.outputs["Color"], bsdf.inputs["Base Color"])
    nimg = nt.nodes.new("ShaderNodeTexImage")
    nimg.image = bpy.data.images.load(os.path.join(tex_dir, f"{SUIT}_normal.png"))
    nimg.image.filepath = bpy.path.relpath(nimg.image.filepath, start=os.path.dirname(out))
    nimg.image.colorspace_settings.name = "Non-Color"
    nm = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(nimg.outputs["Color"], nm.inputs["Color"])
    nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.85
    mat.diffuse_color = (0.25, 0.35, 0.6, 1)
    return mat


mat = make_material()
tree1 = skin_tree()
report = {"fonte": P["fonte"], "pecas": {}}

# the simulated skin in triangles: Surface Deform won't bind to its concave quads (it bound nothing and the collar stayed
# behind while the body danced away, first test run)
if not any(m.type == "TRIANGULATE" for m in skin.modifiers):
    skin.modifiers.new("triangulos", "TRIANGULATE")
# collisions on the bodies: the simulated skin, and head, hands and feet
for ob in (skin, body):
    if not any(m.type == "COLLISION" for m in ob.modifiers):
        ob.modifiers.new("colisao", "COLLISION")
    ob.collision.thickness_outer = 0.001
    ob.collision.cloth_friction = 5.0
    ob.collision.damping = 0.1

settle = int(P["acomodacao_quadros"])
cloths = []
for name in pieces:
    q = P["pecas"][name]
    keep = part_mask[q["parte"]]
    idx = np.flatnonzero(keep)
    remap = -np.ones(len(X), int)
    remap[idx] = np.arange(len(idx))
    fsel = [k for k, f in enumerate(faces) if keep[f[0]]]
    me = bpy.data.meshes.new("HM_" + name)
    me.from_pydata(X[idx].tolist(), [], [[int(remap[i]) for i in faces[k]] for k in fsel])
    uv = me.uv_layers.new(name="UVMap")
    loop_uv = np.concatenate([vt[fuv[k]] for k in fsel])
    uv.data.foreach_set("uv", loop_uv.ravel())
    me.materials.append(mat)
    ob = bpy.data.objects.new("HM_" + name, me)
    sc.collection.objects.link(ob)

    # subdivide once: edges ~1 cm
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=1, use_grid_fill=True)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    V = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)

    # out of the skin by the starting gap
    gap = q["folga_inicial_mm"] / 1000
    d, nrm, near = signed_dist(tree1, V)
    push = d < gap
    V[push] = near[push] + nrm[push] * gap
    me.vertices.foreach_set("co", V.ravel())
    me.update()

    # the opening that holds the piece: the highest boundary loop
    bm = bmesh.new()
    bm.from_mesh(me)
    bverts = {v.index for e in bm.edges if e.is_boundary for v in e.verts}
    adj = {i: set() for i in bverts}
    for e in bm.edges:
        if e.is_boundary:
            i, j = e.verts[0].index, e.verts[1].index
            adj[i].add(j)
            adj[j].add(i)
    bm.free()
    loops, seen = [], set()
    for s in bverts:
        if s in seen:
            continue
        stack, comp = [s], []
        while stack:
            v = stack.pop()
            if v in seen:
                continue
            seen.add(v)
            comp.append(v)
            stack.extend(adj[v] - seen)
        loops.append(comp)
    top = max(loops, key=lambda c: V[c, 2].mean())
    reach = (q.get("presa_ate_gola_mm") or q.get("presa_ate_cos_mm")) / 1000
    dist_open = np.min(np.linalg.norm(V[:, None, :] - V[top][None, :, :], axis=2), axis=1)
    pinned = np.flatnonzero(dist_open <= reach)
    g = ob.vertex_groups.new(name="presa")
    g.add(pinned.tolist(), 1.0, "REPLACE")

    # pinned part follows the simulated skin
    sd = ob.modifiers.new("segue_pele", "SURFACE_DEFORM")
    sd.target = skin
    sd.falloff = 4.0
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.surfacedeform_bind(modifier=sd.name)
    if not sd.is_bound:
        raise RuntimeError("Surface Deform did not bind " + ob.name)

    # cloth
    area = sum(p.area for p in me.polygons)
    cl = ob.modifiers.new("tecido", "CLOTH")
    s = cl.settings
    s.quality = int(q["qualidade"])
    s.mass = q.get("massa_vertice_kg") or q["gramatura_g_m2"] / 1000 * area / len(V)
    s.air_damping = q["amortecimento_ar"]
    s.tension_stiffness, s.compression_stiffness = q["tracao"], q["compressao"]
    s.shear_stiffness, s.bending_stiffness = q["cisalhamento"], q["flexao"]
    s.vertex_group_mass = "presa"
    # fitted on the skin the cloth has no tension and follows every hollow; shrunk a little it pulls like jersey over a body
    s.shrink_min = q.get("encolhimento", 0.0)
    c = cl.collision_settings
    c.use_collision = True
    c.distance_min = q["distancia_colisao_mm"] / 1000
    c.collision_quality = 4
    c.use_self_collision = True
    c.self_distance_min = q["auto_colisao_mm"] / 1000
    c.self_friction = q["atrito"]
    c.friction = q["atrito"]
    pc = cl.point_cache
    pc.frame_start, pc.frame_end = 1 - settle, sc.frame_end
    cloths.append((name, ob, cl))
    report["pecas"][name] = {"tecido": q["tecido"], "vertices": len(V), "faces": len(me.polygons),
                             "area_m2": round(area, 3), "massa_g": round(q["gramatura_g_m2"] * area, 1),
                             "massa_por_vertice_kg": s.mass, "presos": int(len(pinned)),
                             "empurrados_para_fora_no_inicio": int(push.sum())}

sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=out)
# the cache stays in memory and is saved inside OUT.blend: a disk cache from a negative frame (the settling) was written
# but never read back, and the cloth showed its input

t0 = time.time()
for name, ob, cl in cloths:
    # stepping frames and baking from that memory cache left 0 frames on disk (first test run): bake directly
    with bpy.context.temp_override(scene=sc, point_cache=cl.point_cache):
        bpy.ops.ptcache.bake(bake=True)
    print(name, cl.point_cache.info, round(time.time() - t0, 1), "s", flush=True)
report["tempo_simulacao_s"] = round(time.time() - t0, 1)
report["cache"] = {name: cl.point_cache.info for name, ob, cl in cloths}

# how much cloth ends inside the simulated skin
check = {}
for f in list(range(1, sc.frame_end + 1, 10)) + [0, 1 - settle]:
    sc.frame_set(f)
    tree = skin_tree()
    row = {}
    for name, ob, cl in cloths:
        d, _, _ = signed_dist(tree, evaluated(ob))
        row[name] = {"dentro": int((d < 0).sum()), "mais_fundo_mm": round(float(-d.min()) * 1000, 1) if (d < 0).any() else 0.0}
    check[f] = row
report["dentro_da_pele_por_quadro"] = check
sc.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=out)
json.dump(report, open(report_path, "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: v for k, v in report.items() if k != "dentro_da_pele_por_quadro"}, indent=1))

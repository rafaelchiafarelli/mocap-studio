"""Step 11e: the simulated skin into the moving body's file, for Blender and for stage_video.py.

    python3 human-model/blender_run.py --blend 07_movimento_duas_cameras_31-43s.blend human-model/investigations/pose-capture/tissue_assemble.py TECIDOS.npz PELE.pc2 OUT.blend [--aneis]

Adds `HM_pele_simulada`: tissue_mesh.py's shown skin (MPFB's skin subdivided twice, trunk and limbs) played by a Mesh Cache
modifier from PELE.pc2 (tissue_sim.py), path relative to OUT.blend. HM_body keeps head, hands and feet, skinned by the rig.

The seam (2026-11-15, Rafael saw wrists and ankles "descolando"): HM_body is shown subdivided twice too, like the skin the
simulation was built from (tissue_export.py: helpers masked, then Subsurf 2), and a Geometry Nodes modifier deletes exactly
the subdivided faces the simulated skin has (`sub_ids`), so the two meet border to border. The flag per subdivided face sits
on `HM_faces_simuladas`, a mesh of points only (one per face, attribute `simulada`), read by index. Shown coarse with two
rings under the simulated skin (`--aneis`, the way until tet_v10), the coarse rings crossed the smooth skin in a jagged line.
"""
import os, sys
import bpy
import numpy as np

a = sys.argv[sys.argv.index("--") + 1:]
rings = "--aneis" in a
a = [x for x in a if x != "--aneis"]
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


def cut_by_rings():
    """The old way: the body coarse, two rings of faces kept past the cut, under the simulated skin."""
    patch = np.zeros(13380, bool)
    patch[m["skin_ids"]] = True
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
    mask = body.modifiers.new("so_fora_da_simulacao", "MASK")
    mask.vertex_group = g.name
    # the original helper mask stays in charge of the helpers: they aren't in the new group, so they stay hidden
    return f"body keeps {int(keep.sum())} coarse vertices"


def cut_exact():
    """Subsurf 2 as tissue_export.py had it, then the simulated faces deleted by index."""
    for md in body.modifiers:
        if md.type in ("SUBSURF", "NODES"):
            md.show_viewport = md.show_render = False
    sub = body.modifiers.new("subdividido_como_a_simulacao", "SUBSURF")
    sub.levels = sub.render_levels = 2
    rig = bpy.data.objects["HM_rig"]
    was = rig.data.pose_position
    rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    ev = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    em = ev.to_mesh()
    nf = len(em.polygons)
    loops = np.empty(len(em.loops), np.int64)
    em.loops.foreach_get("vertex_index", loops)
    start = np.empty(nf, np.int64)
    em.polygons.foreach_get("loop_start", start)
    total = np.empty(nf, np.int64)
    em.polygons.foreach_get("loop_total", total)
    ev.to_mesh_clear()
    rig.data.pose_position = was
    keys = {tuple(sorted(loops[s:s + t].tolist())): i for i, (s, t) in enumerate(zip(start, total))}
    sid = m["sub_ids"]
    flag = np.zeros(nf, bool)
    missing = 0
    for q in faces:
        i = keys.get(tuple(sorted(sid[q].tolist())))
        if i is None:
            missing += 1
        else:
            flag[i] = True
    assert missing == 0, f"{missing} simulated faces not found in the subdivided body"
    pm = bpy.data.meshes.new("HM_faces_simuladas")
    pm.vertices.add(nf)
    at = pm.attributes.new("simulada", "BOOLEAN", "POINT")
    at.data.foreach_set("value", flag)
    holder = bpy.data.objects.new("HM_faces_simuladas", pm)
    bpy.context.scene.collection.objects.link(holder)
    holder.hide_render = True
    holder.hide_select = True
    holder.display_type = "BOUNDS"

    ng = bpy.data.node_groups.new("corta_simulada", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n = ng.nodes
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    info = n.new("GeometryNodeObjectInfo")
    info.inputs["Object"].default_value = holder
    attr = n.new("GeometryNodeInputNamedAttribute")
    attr.data_type = "BOOLEAN"
    attr.inputs["Name"].default_value = "simulada"
    idx = n.new("GeometryNodeInputIndex")
    samp = n.new("GeometryNodeSampleIndex")
    samp.data_type, samp.domain = "BOOLEAN", "POINT"
    dele = n.new("GeometryNodeDeleteGeometry")
    dele.domain = "FACE"
    L = ng.links
    L.new(info.outputs["Geometry"], samp.inputs["Geometry"])
    L.new(attr.outputs["Attribute"], samp.inputs["Value"])
    L.new(idx.outputs["Index"], samp.inputs["Index"])
    L.new(gi.outputs[0], dele.inputs["Geometry"])
    L.new(samp.outputs[0], dele.inputs["Selection"])
    L.new(dele.outputs[0], go.inputs[0])
    gn = body.modifiers.new("corta_a_parte_simulada", "NODES")
    gn.node_group = ng
    bpy.context.view_layer.update()
    shown = len(body.evaluated_get(bpy.context.evaluated_depsgraph_get()).data.polygons)
    assert shown == nf - flag.sum(), (shown, nf, int(flag.sum()))
    glue_border()
    return f"body subdivided: {nf} faces, {int(flag.sum())} simulated deleted, {shown} shown"


def glue_border():
    """The simulated skin's border lies up to ~1.4 mm off the body's (seam_gap.py on tet_v10), a crack in close-ups: its border
    vertices are moved onto the body's nearest surface (attribute `costura`, Geometry Nodes after the Mesh Cache)."""
    edges = {}
    for f in faces:
        for i in range(4):
            e = tuple(sorted((int(f[i]), int(f[(i + 1) % 4]))))
            edges[e] = edges.get(e, 0) + 1
    w = np.zeros(len(verts), np.float32)
    w[np.unique([v for e, c in edges.items() if c == 1 for v in e])] = 1.0
    at = me.attributes.new("costura", "FLOAT", "POINT")
    at.data.foreach_set("value", w)
    ng = bpy.data.node_groups.new("cola_na_costura", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    n, L = ng.nodes, ng.links
    gi, go = n.new("NodeGroupInput"), n.new("NodeGroupOutput")
    info = n.new("GeometryNodeObjectInfo")
    info.transform_space = "RELATIVE"
    info.inputs["Object"].default_value = body
    prox = n.new("GeometryNodeProximity")
    prox.target_element = "FACES"
    pos = n.new("GeometryNodeInputPosition")
    attr = n.new("GeometryNodeInputNamedAttribute")
    attr.data_type = "FLOAT"
    attr.inputs["Name"].default_value = "costura"
    sub = n.new("ShaderNodeVectorMath")
    sub.operation = "SUBTRACT"
    scale = n.new("ShaderNodeVectorMath")
    scale.operation = "SCALE"
    setp = n.new("GeometryNodeSetPosition")
    L.new(info.outputs["Geometry"], prox.inputs[0])
    L.new(pos.outputs[0], prox.inputs["Source Position"])
    L.new(prox.outputs["Position"], sub.inputs[0])
    L.new(pos.outputs[0], sub.inputs[1])
    L.new(sub.outputs[0], scale.inputs[0])
    L.new(attr.outputs["Attribute"], scale.inputs["Scale"])
    L.new(gi.outputs[0], setp.inputs["Geometry"])
    L.new(attr.outputs["Attribute"], setp.inputs["Selection"])
    L.new(scale.outputs[0], setp.inputs["Offset"])
    L.new(setp.outputs[0], go.inputs[0])
    gm = ob.modifiers.new("cola_na_costura", "NODES")
    gm.node_group = ng


msg = cut_by_rings() if rings else cut_exact()
bpy.ops.wm.save_as_mainfile(filepath=out)
print("simulated skin", len(verts), "vertices,", len(faces), "faces;", msg, "; cache", mc.filepath)

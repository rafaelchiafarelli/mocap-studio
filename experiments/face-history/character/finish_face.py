"""Opened on character_v1.blend. Arg: output .blend. Saves the 52 ARKit shapes and binds all strands to the skin."""
import sys
import addon_utils, bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
out = sys.argv[sys.argv.index("--") + 1]
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.faceservice import FaceService, ARKIT_FACEUNITS

body = bpy.data.objects["character.body"]
FaceService.load_targets(body, load_microsoft_visemes=False, load_arkit_faceunits=True)
FaceService.interpolate_targets(body)
units = set(ARKIT_FACEUNITS)
for o in bpy.data.objects:
    if o.type == "MESH" and o is not body and o.data.shape_keys:
        if any(k in o.name for k in ("worksuit", "shoes")):  # clothes need no face shapes
            o.shape_key_clear()
print("RESULT with_arkit", [(o.name, sum(k.name in units for k in o.data.shape_keys.key_blocks)) for o in bpy.data.objects if o.type == "MESH" and o.data.shape_keys])

# Neutral skin: shape keys applied, helpers and hidden parts gone, no armature or subdivision.
saved = {m.name: m.show_viewport for m in body.modifiers}
for m in body.modifiers:
    if m.type in ("ARMATURE", "SUBSURF"):
        m.show_viewport = False
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
surf = body.evaluated_get(dg).to_mesh()
surf.calc_loop_triangles()
verts = [v.co.copy() for v in surf.vertices]
tri_verts = [tuple(t.vertices) for t in surf.loop_triangles]
tri_loops = [tuple(t.loops) for t in surf.loop_triangles]  # copied: the evaluated mesh is freed by the next to_mesh()
bvh = BVHTree.FromPolygons(verts, tri_verts, all_triangles=True)
uvs = np.zeros((len(surf.loops), 2)); surf.uv_layers.active.data.foreach_get("uv", uvs.reshape(-1))
uv_name = body.data.uv_layers.active.name

# Same, but with every vertex of the base mesh: the rest position the strands are measured against.
for m in body.modifiers:
    m.show_viewport = False
bpy.context.view_layer.update()
full = body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
rest = np.zeros(len(full.vertices) * 3, dtype=np.float32); full.vertices.foreach_get("co", rest)
assert len(full.vertices) == len(body.data.vertices)
attr = body.data.attributes.get("rest_position") or body.data.attributes.new("rest_position", "FLOAT_VECTOR", "POINT")
attr.data.foreach_set("vector", rest)
for m in body.modifiers:
    m.show_viewport = saved[m.name]

group = bpy.data.node_groups.new("character.deform_on_skin", "GeometryNodeTree")
group.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
group.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
gi, go = group.nodes.new("NodeGroupInput"), group.nodes.new("NodeGroupOutput")
deform = group.nodes.new("GeometryNodeDeformCurvesOnSurface")
group.links.new(gi.outputs[0], deform.inputs[0]); group.links.new(deform.outputs[0], go.inputs[0])

for o in [c for c in bpy.data.objects if c.type == "CURVES"]:
    d = o.data
    pts = np.zeros(len(d.attributes["position"].data) * 3, dtype=np.float32)
    d.attributes["position"].data.foreach_get("vector", pts)
    n_pts = len(pts) // 3 // len(d.curves)
    roots = pts.reshape(-1, n_pts, 3)[:, 0]
    # strands were generated at rest, so positions are already world and the bone parent can go
    o.parent = None; o.parent_type = "OBJECT"; o.parent_bone = ""; o.matrix_parent_inverse.identity(); o.matrix_world.identity()
    o.parent = body; o.matrix_parent_inverse = body.matrix_world.inverted()
    uv = np.zeros((len(roots), 2), dtype=np.float32)
    dist = np.zeros(len(roots))
    for i, r in enumerate(roots):
        loc, _, idx, dist[i] = bvh.find_nearest(Vector(r))
        a, b, c = (verts[v] for v in tri_verts[idx])
        v0, v1, v2 = b - a, c - a, loc - a
        dn = v0.dot(v0) * v1.dot(v1) - v0.dot(v1) ** 2 or 1e-12
        w1 = (v1.dot(v1) * v0.dot(v2) - v0.dot(v1) * v1.dot(v2)) / dn
        w2 = (v0.dot(v0) * v1.dot(v2) - v0.dot(v1) * v0.dot(v2)) / dn
        l0, l1, l2 = tri_loops[idx]
        uv[i] = uvs[l0] * (1 - w1 - w2) + uvs[l1] * w1 + uvs[l2] * w2
    a = d.attributes.get("surface_uv_coordinate") or d.attributes.new("surface_uv_coordinate", "FLOAT2", "CURVE")
    a.data.foreach_set("vector", uv.ravel())
    d.surface, d.surface_uv_map = body, uv_name
    o.modifiers.new("DeformOnSkin", "NODES").node_group = group
    print("RESULT bound", o.name, len(roots), "root_to_skin_mm p50", round(float(np.median(dist)) * 1000, 2), "max", round(float(dist.max()) * 1000, 2))


# Subdivision makes the surface sit slightly inside the coarse mesh the strands were rooted on, and the deform node
# keeps that offset. Measure it at neutral and shift each strand so its root sits on the skin the character really shows.
def eval_roots(o, dg):
    e = o.evaluated_get(dg).data
    p = np.zeros(len(e.attributes["position"].data) * 3, dtype=np.float32)
    e.attributes["position"].data.foreach_get("vector", p)
    return p.reshape(-1, len(p) // 3 // len(e.curves), 3)[:, 0].copy()


for round_ in range(3):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    m = body.evaluated_get(dg).to_mesh()
    skin = BVHTree.FromPolygons([v.co.copy() for v in m.vertices], [tuple(q.vertices) for q in m.polygons])
    for o in [c for c in bpy.data.objects if c.type == "CURVES"]:
        roots = eval_roots(o, dg)
        hits = np.array([skin.find_nearest(Vector(r))[0] for r in roots], dtype=np.float32)
        delta = hits - roots
        d = o.data
        pts = np.zeros(len(d.attributes["position"].data) * 3, dtype=np.float32)
        d.attributes["position"].data.foreach_get("vector", pts)
        n_pts = len(pts) // 3 // len(d.curves)
        pts = (pts.reshape(-1, n_pts, 3) + delta[:, None, :]).ravel()
        d.attributes["position"].data.foreach_set("vector", pts)
        d.update_tag()
        print("RESULT snap", round_, o.name, "p50", round(float(np.median(np.linalg.norm(delta, axis=1))) * 1000, 2), "max", round(float(np.linalg.norm(delta, axis=1).max()) * 1000, 2), "mm")
bpy.ops.wm.save_mainfile(filepath=out)
print("RESULT saved", out)

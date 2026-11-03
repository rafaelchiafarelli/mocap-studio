"""Seeded strand generator: scalp hair, eyebrows, fine facial hair as Blender Curves. Deterministic from the recipe."""
import math
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def _triangles(mesh, keep_poly=None):
    mesh.calc_loop_triangles()
    tris = [t for t in mesh.loop_triangles if keep_poly is None or keep_poly(t.polygon_index)]
    verts = np.array([v.co for v in mesh.vertices], dtype=np.float64)
    loops = np.array([t.loops for t in tris])
    idx = np.array([t.vertices for t in tris])
    return verts[idx], loops


def _sample(tris, n, rng):
    a = np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1) / 2
    pick = rng.choice(len(tris), n, p=a / a.sum())
    u, v = rng.random(n), rng.random(n)
    flip = u + v > 1
    u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
    t = tris[pick]
    return t[:, 0] * (1 - u - v)[:, None] + t[:, 1] * u[:, None] + t[:, 2] * v[:, None], pick, u, v


def _curves(name, strands, radii, melanin, parent_rig, surface, material):
    n_pts = strands.shape[1]
    data = bpy.data.hair_curves.new(name)
    data.add_curves([n_pts] * len(strands))
    data.attributes["position"].data.foreach_set("vector", strands.reshape(-1))
    data.attributes.new("radius", "FLOAT", "POINT").data.foreach_set("value", radii.reshape(-1))
    data.attributes.new("melanin", "FLOAT", "CURVE").data.foreach_set("value", melanin)
    data.materials.append(material)
    data.surface = surface
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent, obj.parent_type, obj.parent_bone = parent_rig, "BONE", "spine.006"
    bone = parent_rig.data.bones["spine.006"]
    obj.matrix_parent_inverse = (parent_rig.matrix_world @ bone.matrix_local @ _bone_tail_offset(bone)).inverted()
    return obj


def _bone_tail_offset(bone):
    from mathutils import Matrix
    return Matrix.Translation((0, bone.length, 0))


def hair_material(spec):
    m = bpy.data.materials.new("character.hair")
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    b = t.nodes.new("ShaderNodeBsdfHairPrincipled")
    b.parametrization = "MELANIN"
    a = t.nodes.new("ShaderNodeAttribute")
    a.attribute_name, a.attribute_type = "melanin", "GEOMETRY"
    t.links.new(a.outputs["Fac"], b.inputs["Melanin"])
    b.inputs["Melanin Redness"].default_value = spec.get("redness", 0.25)
    b.inputs["Roughness"].default_value = spec.get("roughness", 0.32)
    b.inputs["Radial Roughness"].default_value = spec.get("radial_roughness", 0.45)
    b.inputs["Random Roughness"].default_value = 0.2
    b.inputs["Random Color"].default_value = 0.12
    t.links.new(b.outputs[0], out.inputs["Surface"])
    return m


def _melanin(n, spec, rng):
    white = rng.random(n) < spec["white_fraction"]
    return np.where(white, rng.uniform(0.02, 0.12, n), rng.uniform(spec["dark_melanin"][0], spec["dark_melanin"][1], n))


def _grow(roots, normals, dirs, lengths, n_pts, spec, bvh, rng):
    """Walk strands along `dirs`, sagging, wandering, and kept off the skin via the BVH."""
    pos = np.zeros((len(roots), n_pts, 3))
    pos[:, 0] = roots
    wander = spec.get("wander", 0.3)
    sag = spec.get("sag", 0.2)
    lift = spec.get("lift", 0.6)
    clearance = spec.get("clearance", 0.0012)
    d = dirs + normals * lift
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    drift = rng.normal(0, 1, dirs.shape)
    for i in range(1, n_pts):
        f = i / (n_pts - 1)
        d = d + drift * wander * 0.35 + rng.normal(0, wander * 0.25, d.shape)
        d[:, 2] -= sag * f
        d -= normals * lift * 0.28 * f
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        pos[:, i] = pos[:, i - 1] + d * (lengths / (n_pts - 1))[:, None]
        for k in range(len(pos)):
            p = Vector(pos[k, i])
            hit = bvh.find_nearest(p)
            if hit[0] is None:
                continue
            away = p - hit[0]
            inside = away.dot(hit[1]) < 0
            if inside or away.length < clearance:
                pos[k, i] = np.array(hit[0] + hit[1] * clearance)
    return pos


def _root_normals(bvh, roots):
    out = np.zeros_like(roots)
    for i, r in enumerate(roots):
        out[i] = bvh.find_nearest(Vector(r))[1]
    return out


def _smooth(edge0, edge1, x):
    t = np.clip((x - edge0) / (edge1 - edge0), 0, 1)
    return t * t * (3 - 2 * t)


def scalp(mesh, frame, spec, rig, surface, mat, bvh, seed):
    rng = np.random.default_rng(seed)
    tris, _ = _triangles(mesh, lambda i: mesh.polygons[i].material_index == 0)
    n = spec["strands"]
    pts, _, _, _ = _sample(tris, n * 5, rng)
    x, y, z = pts[:, 0] - frame["cx"], pts[:, 1] - frame["cy"], pts[:, 2]
    # 0 = front of the head, pi = back. Hairline height depends on the angle around the head.
    ang = np.arctan2(np.abs(x), -y)
    knots = np.radians([0, 22, 45, 75, 100, 135, 180])
    h = np.array(spec["hairline"]) + frame["eye_z"]
    line = np.interp(ang, knots, h)
    line += spec["hairline_side_shift"] * np.sign(x) * (ang < 1.0)
    line += rng.normal(0, 0.003, len(line))
    p = _smooth(line, line + spec["hairline_feather"], z)
    # the back of the ear stays clear
    ear = (np.abs(x) > frame["ear_x"]) & (z < frame["eye_z"] + 0.035) & (np.abs(y) < 0.035)
    p[ear] = 0
    keep = rng.random(len(p)) < p
    roots = pts[keep][:n]
    density = p[keep][:n]
    normals = _root_normals(bvh, roots)
    # combed: from a parting on one side, over the top; down on the sides and back
    rel = roots - np.array([frame["cx"], frame["cy"], frame["top_z"] - 0.03])
    outward = rel / np.linalg.norm(rel, axis=1, keepdims=True)
    part = spec["part_x"]
    comb = np.zeros_like(roots)
    comb[:, 0] = np.tanh((roots[:, 0] - frame["cx"] - part) / spec["part_soft"]) * spec["sweep"]
    comb[:, 1] = 0.35
    comb[:, 2] = -0.5
    d = comb + outward * 0.35
    d -= normals * np.sum(d * normals, axis=1, keepdims=True)
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    # shorter over the sides and back, and at the hairline
    side = np.clip((frame["top_z"] - roots[:, 2]) / 0.11, 0, 1)
    lengths = rng.uniform(*spec["length"], len(roots)) * (1 - 0.66 * side) * (1 - spec["nape_short"] * np.clip((frame["eye_z"] - roots[:, 2] + 0.01) / 0.07, 0, 1)) * (0.45 + 0.55 * density)
    n_pts = spec["points"]
    strands = _grow(roots, normals, d, lengths, n_pts, spec, bvh, rng)
    taper = np.linspace(1, 0.12, n_pts)
    radii = np.outer(rng.uniform(0.75, 1.25, len(roots)) * spec["radius"], taper)
    return _curves("character.scalp_hair", strands.astype(np.float32), radii.astype(np.float32),
                   _melanin(len(roots), spec, rng).astype(np.float32), rig, surface, mat)


def eyebrows(brow_obj, frame, spec, rig, surface, mat, bvh, seed):
    """Roots come from the fitted MPFB eyebrow card, kept where its alpha says brow."""
    rng = np.random.default_rng(seed)
    me = brow_obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    tris, loops = _triangles(me)
    uv = np.zeros((len(me.loops), 2))
    me.uv_layers.active.data.foreach_get("uv", uv.reshape(-1))
    nodes = brow_obj.data.materials[0].node_tree.nodes
    img = next(x.image for x in nodes if x.bl_idname == "ShaderNodeTexImage" and x.image)
    w, h = img.size
    px = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(px)
    alpha = px.reshape(h, w, 4)[:, :, 3]
    pts, pick, u, v = _sample(tris, spec["strands"] * 14, rng)
    tuv = uv[loops[pick]]
    puv = tuv[:, 0] * (1 - u - v)[:, None] + tuv[:, 1] * u[:, None] + tuv[:, 2] * v[:, None]
    a = alpha[np.clip((puv[:, 1] * h).astype(int), 0, h - 1), np.clip((puv[:, 0] * w).astype(int), 0, w - 1)]
    keep = rng.random(len(a)) < a ** 1.5
    pts = pts[keep][:spec["strands"]]
    roots, normals = np.zeros_like(pts), np.zeros_like(pts)
    for i, r in enumerate(pts):
        hit = bvh.find_nearest(Vector(r))
        roots[i], normals[i] = hit[0], hit[1]
    # brows grow up and out, flatter toward the tail
    sx = np.sign(roots[:, 0] - frame["cx"])
    along = np.clip(np.abs(roots[:, 0] - frame["cx"]) / 0.06, 0, 1)
    d = np.stack([sx * (0.25 + 1.1 * along), -0.1 * np.ones(len(roots)), 1.0 - 0.75 * along], axis=1)
    d -= normals * np.sum(d * normals, axis=1, keepdims=True)
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    lengths = rng.uniform(*spec["length"], len(roots))
    wild = rng.random(len(roots)) < spec["wild_fraction"]
    lengths[wild] *= spec["wild_scale"]
    n_pts = spec["points"]
    strands = _grow(roots, normals, d, lengths, n_pts, spec, bvh, rng)
    taper = np.linspace(1, 0.15, n_pts)
    radii = np.outer(rng.uniform(0.8, 1.2, len(roots)) * spec["radius"], taper)
    return _curves("character.eyebrows", strands.astype(np.float32), radii.astype(np.float32),
                   _melanin(len(roots), spec, rng).astype(np.float32), rig, surface, mat)


def fine_hair(mesh, frame, spec, rig, surface, mat, bvh, seed):
    """Short sparse hair over the face: stubble and vellus. It catches rim light the way real skin does."""
    rng = np.random.default_rng(seed)
    tris, _ = _triangles(mesh, lambda i: mesh.polygons[i].material_index == 0)
    pts, _, _, _ = _sample(tris, spec["strands"] * 12, rng)
    head = (pts[:, 2] > frame["eye_z"] - spec["below_eye"]) & (pts[:, 2] < frame["eye_z"] + 0.05) & (pts[:, 1] < frame["cy"] + 0.02)
    roots = pts[head][:spec["strands"]]
    normals = _root_normals(bvh, roots)
    d = np.tile(np.array([0.0, 0.0, -1.0]), (len(roots), 1)) + rng.normal(0, 0.25, roots.shape)
    d -= normals * np.sum(d * normals, axis=1, keepdims=True)
    d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    lengths = rng.uniform(*spec["length"], len(roots))
    strands = _grow(roots, normals, d, lengths, spec["points"], spec, bvh, rng)
    taper = np.linspace(1, 0.2, spec["points"])
    radii = np.outer(np.full(len(roots), spec["radius"]), taper)
    return _curves("character.fine_hair", strands.astype(np.float32), radii.astype(np.float32),
                   _melanin(len(roots), spec, rng).astype(np.float32), rig, surface, mat)

"""Sharpens the folds on a skin finer than MPFB's, leaving the 13,380 vertices and the sliders alone. Run with --blend on a file with fold shape keys. Args: folds.json out.blend [levels]
MPFB's skin has about 2 cm between points, too coarse for a crease. A Geometry Nodes modifier after the Subsurf pushes the skin along its normals, by images in the skin's UV space that hold a thin line per fold, multiplied by that fold's shape key value."""
import json, os, sys
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

a = hb.args()
catalogue = json.load(open(a[0], encoding="utf-8"))["folds"]
LEVELS = int(a[2]) if len(a) > 2 else 2
SIZE = 2048
SIGMA_M = 0.0035  # half-width of the crease's core
SHARE = 0.45  # how deep the crease goes, as a share of the fold's depth, on top of the broad dent
body = bpy.data.objects["HM_body"]
me = body.data
uv_name = me.uv_layers.active.name
uvs = np.empty(len(me.loops) * 2)
me.uv_layers.active.data.foreach_get("uv", uvs)
uvs = uvs.reshape(-1, 2)
loop_v = np.empty(len(me.loops), dtype=np.int32)
me.loops.foreach_get("vertex_index", loop_v)
uv_of = {}
for loop, v in enumerate(loop_v.tolist()):
    uv_of.setdefault(v, uvs[loop])
co = np.empty(len(me.vertices) * 3)
me.vertices.foreach_get("co", co)
co = co.reshape(-1, 3)


def fold_image(fold, label):
    """Distance to the fold's line, in pixels turned into metres by the line's own scale, as a gaussian."""
    pts = [v for v in fold["vertices"] if v in uv_of]
    uv = np.array([uv_of[v] for v in pts])
    keep = [i for i in range(len(pts) - 1) if np.linalg.norm(uv[i + 1] - uv[i]) < 0.06]
    if not keep:
        return None
    uv_pass = uv.copy()
    for _ in range(3):  # the line goes through mesh vertices, so it zigzags: smoothed here, in the image only
        uv_pass[1:-1] = (uv_pass[:-2] + 2 * uv_pass[1:-1] + uv_pass[2:]) / 4
    px = uv_pass * SIZE
    scales = [np.linalg.norm(co[pts[i + 1]] - co[pts[i]]) / max(np.linalg.norm(px[i + 1] - px[i]), 1e-6) for i in keep]
    metres_per_pixel = float(np.median(scales))
    sigma = SIGMA_M / max(metres_per_pixel, 1e-9)
    image = np.zeros((SIZE, SIZE), np.float32)
    margin = int(4 * sigma) + 3
    for i in keep:
        p, q = px[i], px[i + 1]
        x0, x1 = int(max(min(p[0], q[0]) - margin, 0)), int(min(max(p[0], q[0]) + margin, SIZE))
        y0, y1 = int(max(min(p[1], q[1]) - margin, 0)), int(min(max(p[1], q[1]) + margin, SIZE))
        if x1 <= x0 or y1 <= y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1) + 0.5, np.arange(y0, y1) + 0.5)
        d = q - p
        t = np.clip(((gx - p[0]) * d[0] + (gy - p[1]) * d[1]) / max(d @ d, 1e-9), 0, 1)
        dist2 = (gx - p[0] - t * d[0]) ** 2 + (gy - p[1] - t * d[1]) ** 2
        value = np.exp(-dist2 / (sigma * sigma)).astype(np.float32)
        image[y0:y1, x0:x1] = np.maximum(image[y0:y1, x0:x1], value)
    name = f"fold_{label}"
    img = bpy.data.images.get(name) or bpy.data.images.new(name, SIZE, SIZE, float_buffer=True, alpha=False)
    img.colorspace_settings.name = "Non-Color"
    rgba = np.stack([image, image, image, np.ones_like(image)], axis=2).ravel()
    img.pixels.foreach_set(rgba)
    img.pack()
    return img


group = bpy.data.node_groups.get("HM_fine_folds") or bpy.data.node_groups.new("HM_fine_folds", "GeometryNodeTree")
group.nodes.clear()
group.interface.clear()
group.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
group.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
inp, out = group.nodes.new("NodeGroupInput"), group.nodes.new("NodeGroupOutput")
uv = group.nodes.new("GeometryNodeInputNamedAttribute")
uv.data_type = "FLOAT_VECTOR"
uv.inputs["Name"].default_value = uv_name
add = None
sockets = {}
for fold in catalogue:
    label = fold["name"] + (f"_{fold['side']}" if fold["side"] else "")
    img = fold_image(fold, label)
    if img is None:
        print("no image for", label)
        continue
    value = group.nodes.new("ShaderNodeValue")  # a value inside the group: Blender 5's modifiers don't take drivers on inputs from scripts
    value.name = f"v_{label}"
    sockets[label] = value.name
    tex = group.nodes.new("GeometryNodeImageTexture")
    tex.inputs["Image"].default_value = img
    group.links.new(uv.outputs["Attribute"], tex.inputs["Vector"])
    times = group.nodes.new("ShaderNodeMath")
    times.operation = "MULTIPLY"
    group.links.new(tex.outputs["Color"], times.inputs[0])
    group.links.new(value.outputs[0], times.inputs[1])
    if add is None:
        add = times
    else:
        total = group.nodes.new("ShaderNodeMath")
        total.operation = "ADD"
        group.links.new(add.outputs[0], total.inputs[0])
        group.links.new(times.outputs[0], total.inputs[1])
        add = total
normal = group.nodes.new("GeometryNodeInputNormal")
scale = group.nodes.new("ShaderNodeVectorMath")
scale.operation = "SCALE"
group.links.new(normal.outputs["Normal"], scale.inputs[0])
negative = group.nodes.new("ShaderNodeMath")
negative.operation = "MULTIPLY"
negative.inputs[1].default_value = -1.0
group.links.new(add.outputs[0], negative.inputs[0])
group.links.new(negative.outputs[0], scale.inputs["Scale"])
setp = group.nodes.new("GeometryNodeSetPosition")
group.links.new(inp.outputs["Geometry"], setp.inputs["Geometry"])
group.links.new(scale.outputs[0], setp.inputs["Offset"])
group.links.new(setp.outputs["Geometry"], out.inputs["Geometry"])

for m in body.modifiers:
    if m.type == "SUBSURF":
        m.levels, m.render_levels = LEVELS, LEVELS
mod = body.modifiers.get("HM_fine_folds") or body.modifiers.new("HM_fine_folds", "NODES")
mod.node_group = group
keys = me.shape_keys
for fold in catalogue:
    label = fold["name"] + (f"_{fold['side']}" if fold["side"] else "")
    if label not in sockets:
        continue
    d = group.driver_add(f'nodes["{sockets[label]}"].outputs[0].default_value').driver
    d.type = "SCRIPTED"
    v = d.variables.new()
    v.name = "k"
    v.targets[0].id_type = "KEY"
    v.targets[0].id = keys
    v.targets[0].data_path = f'key_blocks["fold.{label}"].value'
    d.expression = f"k*{fold['depth_mm'] / 1000.0 * SHARE:.5f}"
body.update_tag()
bpy.ops.wm.save_as_mainfile(filepath=a[1])
print("fine folds", len(sockets), "levels", LEVELS)

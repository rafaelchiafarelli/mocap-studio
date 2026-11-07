"""The skin before and after tools/skin_over_bone.py, painted by how far each vertex moved, with stills. Args: SKIN_FIT.npz BUILD_EXPORT.npz OUT.blend
Before on the left, after on the right, 70 cm apart. White hasn't moved; full red moved the most push (15 mm by default).
Stills: <stem>_front.png and <stem>_back.png."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

N_BODY = 13380  # as in export_blend.py
APART = np.array([0.7, 0.0, 0.0])


def painted(name, verts, faces, values, top, collection):
    used, inv = np.unique(faces, return_inverse=True)
    ob = hb.mesh_object(name, verts[used], inv.reshape(-1, 3), collection)
    m = hb.bpy.data.materials.new(f"{name}_push")
    m.use_nodes = True
    attr = m.node_tree.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "push"
    bsdf = next(n for n in m.node_tree.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    m.node_tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    ob.data.materials.append(m)
    t = np.clip(values[used] / top, 0, 1)
    rgba = np.column_stack([np.full(len(t), 0.92), 0.92 - 0.8 * t, 0.92 - 0.8 * t, np.ones(len(t))]).astype(np.float32)
    ob.data.color_attributes.new("push", "FLOAT_COLOR", "POINT").data.foreach_set("color", rgba.ravel())
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def main(fit_npz, export_npz, out):
    d, e = np.load(fit_npz), np.load(export_npz)
    hb.clear_scene()
    col = hb.collection("skin_fit")
    patch, push = d["patch"], d["push"]
    before, after = e["verts"][:N_BODY].astype(float), d["verts"][:N_BODY].astype(float)
    top = max(float(push.max()), 1e-6)
    painted("skin_before", before - APART / 2, patch, np.zeros(len(push)), top, col)
    painted("skin_after", after + APART / 2, patch, push, top, col)
    hb.bpy.ops.wm.save_as_mainfile(filepath=out)
    centre = np.array([0.0, 0.0, 0.85])
    hb.setup_render((1200, 1100))
    stem = os.path.splitext(out)[0]
    for name, eye in (("front", (0.0, -3.6, 0.85)), ("back", (0.0, 3.6, 0.85))):
        hb.render(f"{stem}_{name}.png", hb.camera_look("HM_cam", eye, tuple(centre), lens=50))


main(*hb.args())

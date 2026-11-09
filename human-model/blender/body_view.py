"""The body in layers of tools/body_layers.py as a .blend, with stills beside it. Args: LAYERS.npz OUT.blend
Collections: body_layers (skin, each layer's surface), body_cutaway (the back half in section).
Stills: <stem>_section_front.png (the back half from the front), <stem>_section_side.png (the left half from the left), <stem>_zones.png."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

LABELS = ("bone", "muscle", "fat", "skin", "cavity")
COLORS = {"bone": (0.9, 0.86, 0.75), "muscle": (0.6, 0.12, 0.1), "fat": (0.95, 0.8, 0.35), "skin": (0.85, 0.65, 0.55), "cavity": (0.45, 0.55, 0.8), "fat_deep": (0.85, 0.65, 0.25)}


def compact(verts, faces):
    used, inv = np.unique(faces, return_inverse=True)
    return verts[used], inv.reshape(-1, 3)


ZONES = ("neck", "chest", "breast_L", "breast_R", "upper_back", "belly", "flanks", "lower_back", "hips", "buttocks_upper_center", "buttocks_upper_side", "buttocks_lower_center", "buttocks_lower_side",
         "thigh_front", "thigh_back", "thigh_inner", "thigh_outer", "knee", "calf_front", "calf_back",
         "upper_arm_front", "upper_arm_back", "forearm")  # as hmcore/body.py, which this Blender can't import


def zone_material():
    m = hb.bpy.data.materials.new("zones")
    m.use_nodes = True
    nodes = m.node_tree.nodes
    attr = nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "zone"
    bsdf = next(n for n in nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    m.node_tree.links.new(attr.outputs["Color"], bsdf.inputs["Base Color"])
    return m


def paint_zones(ob, zone_per_vertex):
    """Each zone a colour, from a fixed list so the same zone keeps its colour between runs."""
    import colorsys
    palette = {z: colorsys.hsv_to_rgb((i * 0.618) % 1.0, 0.65, 0.95) for i, z in enumerate(ZONES)}
    col = ob.data.color_attributes.new("zone", "FLOAT_COLOR", "POINT")
    rgba = np.array([(*palette.get(str(z), (0.5, 0.5, 0.5)), 1.0) for z in zone_per_vertex], np.float32)
    col.data.foreach_set("color", rgba.ravel())


def main(npz, out):
    d = np.load(npz)
    hb.clear_scene()
    whole, section, side = hb.collection("body_layers"), hb.collection("body_cutaway"), hb.collection("body_cutaway_side")
    nodes = d["nodes"]
    used = np.unique(d["patch"])
    skin = hb.mesh_object("skin", *compact(d["skin"], d["patch"]), whole, material=zone_material())
    paint_zones(skin, d["zone"][used])
    for label in LABELS:
        m = hb.material(label, COLORS[label])
        hb.mesh_object(f"{label}_surface", *compact(nodes, d[f"surface_{label}"]), whole, material=m).hide_set(True)
        hb.mesh_object(f"cutaway_{label}", *compact(nodes, d[f"surface_cutaway_{label}"]), section, material=m)
    # The left half, cut on the body's middle plane, seen from the left
    tets, lab = d["tets"], d["tet_label"]
    from_left = nodes[tets].mean(axis=1)[:, 0] < 0
    for k, label in enumerate(LABELS):
        f = boundary(tets[from_left & (lab == k)])
        hb.mesh_object(f"side_{label}", *compact(nodes, f), side, material=hb.material(label, COLORS[label]))
    hb.bpy.ops.wm.save_as_mainfile(filepath=out)

    centre = nodes.mean(axis=0)
    height = np.ptp(nodes[:, 2])
    hb.setup_render((900, 1400))
    stem = os.path.splitext(out)[0]
    shots = {"section_front": ([section], centre + np.array([0, -3.2, 0])), "section_side": ([side], centre + np.array([3.2, 0, 0])),
             "zones": ([whole], centre + np.array([0, -3.2, 0]))}
    for name, (shown, eye) in shots.items():
        for c in (whole, section, side):
            for ob in c.objects:
                ob.hide_render = c not in shown or (c is whole and ob.name != "skin")
        cam = hb.camera_look("HM_cam", tuple(eye), tuple(centre), lens=50 * 1.6 / max(height, 1e-3))
        hb.render(f"{stem}_{name}.png", cam)


def boundary(tets):
    faces = np.concatenate([tets[:, [0, 2, 1]], tets[:, [0, 1, 3]], tets[:, [0, 3, 2]], tets[:, [1, 2, 3]]])
    key = np.sort(faces, axis=1)
    _, inv, count = np.unique(key, axis=0, return_inverse=True, return_counts=True)
    return faces[count[inv.ravel()] == 1]


main(*hb.args())

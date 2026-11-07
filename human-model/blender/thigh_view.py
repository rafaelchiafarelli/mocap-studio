"""The layered thigh of tools/thigh_layers.py as a .blend to look at: skin, femur, each layer's surface and the back half in section.
Also renders two stills beside the .blend: <stem>_section.png (the back half from the front) and <stem>_inside.png (muscle and bone through the skin). Args: LAYERS.npz OUT.blend"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

COLORS = {"bone": (0.9, 0.86, 0.75), "muscle": (0.6, 0.12, 0.1), "fat": (0.95, 0.8, 0.35), "skin": (0.85, 0.65, 0.55)}


def compact(verts, faces):
    used, inv = np.unique(faces, return_inverse=True)
    return verts[used], inv.reshape(-1, 3)


def main(npz, out):
    d = np.load(npz)
    hb.clear_scene()
    whole, section = hb.collection("thigh_layers"), hb.collection("thigh_cutaway")
    nodes = d["nodes"]
    skin = hb.mesh_object("skin", *compact(d["skin"], d["patch"]), whole, material=hb.material("skin", COLORS["skin"], alpha=0.35))
    skin.data.materials[0].surface_render_method = "BLENDED"
    hb.mesh_object("femur", d["femur_v"], d["femur_f"], whole, material=hb.material("bone", COLORS["bone"]))
    for label in ("bone", "muscle", "fat"):
        m = hb.material(label, COLORS[label])
        ob = hb.mesh_object(f"{label}_surface", *compact(nodes, d[f"surface_{label}"]), whole, material=m)
        ob.hide_set(label == "fat")
        hb.mesh_object(f"cutaway_{label}", *compact(nodes, d[f"surface_cutaway_{label}"]), section, material=m)
    for ob in list(whole.objects) + list(section.objects):
        ob.data.validate()
    hb.bpy.ops.wm.save_as_mainfile(filepath=out)
    centre = nodes.mean(axis=0)
    hb.setup_render(res=(800, 1100))
    cam = hb.camera_look("HM_cam", centre + np.array([0.0, -0.9, 0.0]), centre, lens=50)
    stem = os.path.splitext(out)[0]
    for ob in whole.objects:
        ob.hide_render = True
    hb.render(f"{stem}_section.png", cam)
    for ob in whole.objects:
        ob.hide_render = ob.name == "fat_surface"
    for ob in section.objects:
        ob.hide_render = True
    hb.render(f"{stem}_inside.png", cam)
    for ob in list(whole.objects) + list(section.objects):
        ob.hide_render = False


main(*hb.args())

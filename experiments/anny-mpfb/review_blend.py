"""Test 3's bodies as MPFB humans in one .blend, live sliders: per seed, the truth and the fits side by side. Runs in Blender.
    python3 human-model/blender_run.py experiments/anny-mpfb/review_blend.py OUT.blend RESULT_DIR [variant ...]
Variants default to macros_only and macros_and_body_locals. A negative value on a two-way target is its opposite target (MPFB's target.json),
as Anny reads it."""
import glob, json, os, sys
import bpy
a = sys.argv[sys.argv.index("--") + 1:]
out_blend, result_dir = a[0], a[1]
variants = a[2:] or ["macros_only", "macros_and_body_locals"]
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from bl_ext.user_default.mpfb.services.locationservice import LocationService

meta = json.load(open(os.path.join(LocationService.get_mpfb_data("targets"), "target.json")))
opposite = {}
for section in meta.values():
    for cat in section["categories"]:
        if "opposites" in cat:
            for side in ("left", "right", "unsided"):
                pos, neg = cat["opposites"].get(f"positive-{side}"), cat["opposites"].get(f"negative-{side}")
                if pos and neg:
                    opposite[pos], opposite[neg] = neg, pos

LABEL = {"truth": "verdadeiro", "macros_only": "ajuste: só macros", "macros_and_locals": "ajuste: macros + todos os alvos",
         "macros_and_body_locals": "ajuste: macros + alvos do corpo"}
COLOR = {"truth": (0.75, 0.75, 0.75), "macros_only": (0.85, 0.55, 0.35), "macros_and_locals": (0.5, 0.7, 0.4), "macros_and_body_locals": (0.35, 0.55, 0.85)}


def material(name, color):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*color, 1.0)
    return m


def human(recipe, name, x, y, color):
    body = HumanService.create_human(macro_detail_dict=recipe["macros"])
    loaded = []
    for t, v in recipe["targets"].items():
        if v < 0 and t in opposite:
            t, v = opposite[t], -v
        path = TargetService.target_full_path(t)
        if not path:
            print("no target", t)
            continue
        TargetService.load_target(body, path, weight=v, name=t)
        loaded.append(t)
    body.name = name
    body.location.x += x
    body.location.y += y
    body.data.materials.clear()
    body.data.materials.append(material("rev_" + name.split(" ")[-1], color))
    return body, loaded


def text(s, x, y, z=-0.15, size=0.07):
    c = bpy.data.curves.new("t", "FONT")
    c.body, c.size, c.align_x = s, size, "CENTER"
    o = bpy.data.objects.new("rótulo " + s[:30], c)
    o.location = (x, y, z)
    o.rotation_euler = (1.5708, 0, 0)
    bpy.context.scene.collection.objects.link(o)


for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
files = sorted(glob.glob(os.path.join(result_dir, "synthetic_seed*.json")))
summary = []
for row, f in enumerate(files):
    d = json.load(open(f))
    seed = d["seed"]
    y = row * 1.5
    col = bpy.data.collections.new(f"corpo de teste {row + 1} (seed {seed})")
    bpy.context.scene.collection.children.link(col)
    entries = [("truth", d["truth"], None)] + [(v, d[v]["recipe"], d[v]["error"]) for v in variants if v in d]
    for i, (key, recipe, err) in enumerate(entries):
        x = i * 0.8
        body, loaded = human(recipe, f"teste{row + 1} {key}", x, y, COLOR[key])
        for c in list(body.users_collection):
            c.objects.unlink(body)
        col.objects.link(body)
        label = LABEL[key] if err is None else f"{LABEL[key]}\nerro médio {err['mean_mm']:.0f} mm, altura {err['height_err_mm']:+.0f} mm"
        text(f"teste {row + 1}: " + label, x, y - 0.25)
        summary.append({"seed": seed, "variant": key, "targets_loaded": len(loaded), "error": err})
bpy.context.scene.render.fps = 24
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print(json.dumps(summary))

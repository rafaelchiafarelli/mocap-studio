"""Measures people with the editor's tape, to judge the tape itself. Args: out.json STILLS_DIR|- recipe.json [recipe.json ...]. Ages below an adult's are raised to 0.5 (bug human-model/8), and the result says so.
Prints one column per person in centimetres, and how long a whole measurement takes. With a folder, also renders each person with the tape's paths on the body."""
import json, os, sys, time
import bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
from bl_ext.user_default.hm_editor import human, tape

a = sys.argv[sys.argv.index("--") + 1:]
rows = {}
stills = None if a[1] == "-" else a[1]
for path in a[2:]:
    recipe = json.load(open(path, encoding="utf-8"))
    raised = recipe["macros"]["age"] < 0.5
    recipe["macros"]["age"] = max(recipe["macros"]["age"], 0.5)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    body = human.create(recipe)
    human.settle(body)
    started = time.time()
    topology = human.tape_topology(body)
    built = time.time()
    values, lines, marks = tape.measure(topology, human.all_verts(body))
    rows[recipe["name"]] = {"cm": {k: round(v * 100, 1) for k, v in values.items()}, "raised_age": raised, "topology_s": round(built - started, 2), "measure_s": round(time.time() - built, 2),
                            "armpit_above_bust_cm": round((marks["armpit"] - marks["nipple_z"]) * 100, 1), "underbust_below_bust_cm": round((marks["nipple_z"] - marks["underbust"]) * 100, 1)}
    if stills:
        human.show_tape(lines)
        h = values["height"]
        hb.setup_render((800, 1100), 16)
        for tag, place in (("front", (0.0, -3.4, 0.55 * h)), ("side", (3.4, 0.0, 0.55 * h)), ("back", (0.0, 3.4, 0.55 * h))):
            hb.render(os.path.join(stills, f"{recipe['name']}_{tag}.png"), hb.camera_look("cam_" + tag, place, (0, 0, 0.5 * h), 60))
json.dump(rows, open(a[0], "w"), indent=1)
names = list(rows)
print("%-16s" % "", *["%9s" % n[:9] for n in names])
for key in tape.MEASURE_KEYS:
    print("%-16s" % key, *["%9.1f" % rows[n]["cm"][key] for n in names])
for field in ("armpit_above_bust_cm", "underbust_below_bust_cm", "measure_s", "topology_s"):
    print("%-16s" % field[:16], *["%9s" % rows[n][field] for n in names])

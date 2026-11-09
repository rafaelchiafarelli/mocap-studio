"""The first shape of a character on the new path: a neutral MPFB human moved to the sheet's measures by the editor's sliders (human.fit_measures). Args: SHEET.json NEUTRAL_RECIPE.json RECIPE_OUT.json SHAPE_OUT.json NAME
SHEET.json is what fast_review.py writes. RECIPE_OUT is the recipe of that shape, for build_model.py; SHAPE_OUT what was asked and reached, in cm."""
import json, os, sys
import bpy
from bl_ext.user_default.hm_editor import catalog, human, recipe as rc, tape

sheet_json, neutral, recipe_out, shape_out, name = sys.argv[sys.argv.index("--") + 1:][:5]
sheet = json.load(open(sheet_json, encoding="utf-8"))
fields, sex = sheet["resolved"]["fields"], sheet["resolved"]["sex"]
recipe = json.load(open(neutral, encoding="utf-8"))
recipe["name"] = rc.safe_name(name)
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
body = human.create(recipe)
human.settle(body)
targets_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(human.__file__))), "mpfb", "data", "targets", "target.json")
by_name = {s.name: s for s in catalog.sliders(json.load(open(targets_json, encoding="utf-8")))}
asked = {k: f["value"] / 100 for k, f in fields.items() if k in tape.MEASURE_KEYS and (k in tape.DRIVERS or k == "height") and f["source"] != "current"}
result = human.fit_measures(body, asked, by_name) if asked else {}
human.settle(body)
values, _, _ = tape.measure(human.tape_topology(body), human.all_verts(body))
out = human.read_recipe(body, recipe["name"], sex, assets=recipe.get("assets"))
wrong = rc.problems(out)
if wrong:
    raise SystemExit("; ".join(wrong))
with open(recipe_out, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=1)
with open(shape_out, "w", encoding="utf-8") as f:
    json.dump({"asked_cm": {k: round(v * 100, 1) for k, v in asked.items()}, "reached_cm": {k: round(float(values[k]) * 100, 1) for k in asked}, "at_limit": [k for k, (_, limit) in result.items() if limit], "measures_cm": {k: round(float(v) * 100, 1) for k, v in values.items()}}, f, indent=1)
print("shape", name, "asked", len(asked))

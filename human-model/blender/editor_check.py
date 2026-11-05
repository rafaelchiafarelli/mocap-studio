"""Checks the installed Human Model Editor without its interface. Args: built.blend's recipe.json out_dir. Run with --blend on a built model.
Built side: controls reach the skin and the recipe reads back. Design side: sliders, macros and the recipe round trip on a plain human. Writes editor_check.json and exits 1 on a failure."""
import json, os, sys
import bpy
import numpy as np
import bl_ext.user_default.hm_editor as ed
from bl_ext.user_default.hm_editor import human, recipe as rc

a = sys.argv[sys.argv.index("--") + 1:]
expected = json.load(open(a[0], encoding="utf-8"))
out = a[1]
os.makedirs(out, exist_ok=True)
results = {}


def check(name, ok, detail=""):
    results[name] = {"ok": bool(ok), "detail": str(detail)}
    print("PASS" if ok else "FAIL", name, detail)


def verts(ob):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    c = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", c)
    ev.to_mesh_clear()
    return c.reshape(-1, 3)


scene = bpy.context.scene
check("slider catalogue loaded", len(ed.SLIDERS) == 230, len(ed.SLIDERS))

# ---- built model
check("file is seen as built", human.is_built())
skin = human.built_skin()
read = human.read_recipe(skin, expected["name"], bpy.data.objects["HM_rig"]["hm_sex"], expected.get("assets"))
check("built file reads back to its recipe", read["macros"] == expected["macros"] and read["targets"] == expected.get("targets", {}), {k: read[k] for k in ("macros", "targets")})
rest = verts(skin)
scene.hm_muscles.zygomaticus_major = 0.6
ctrl = bpy.data.objects["HM_controls"]
check("both-sides muscle sets each side", ctrl["m_zygomaticus_major_L"] == ctrl["m_zygomaticus_major_R"] == scene.hm_muscles.zygomaticus_major)
moved = np.linalg.norm(verts(skin) - rest, axis=1).max()
check("muscle slider moves the skin", moved > 0.002, f"{moved * 1000:.1f} mm")
bpy.ops.hm_editor.reset_controls()
back = np.linalg.norm(verts(skin) - rest, axis=1).max()
check("reset returns the skin", back < 1e-5, f"{back * 1000:.3f} mm")
e = scene.hm_editor
bones_before = e.show_bones
e.show_bones = not bones_before
check("bones toggle", e.show_bones != bones_before)
e.show_bones = bones_before
e.skin_view = "WIRE"
check("skin wire view", skin.display_type == "WIRE")
e.skin_view = "SOLID"

# ---- design side, in a clean file. No interface, so operators that replace the file run directly.
bpy.ops.wm.read_homefile(use_empty=True)
scene = bpy.context.scene
check("clean file isn't built", not human.is_built())
source = {**expected, "targets": {"nose-hump-incr": 0.6, "l-upperarm-muscle-incr": 0.4, "r-upperarm-muscle-incr": 0.4}}
ed._start(scene, source)
e, sl = scene.hm_editor, scene.hm_sliders
body = e.body
check("recipe's slider shows on load", abs(sl.s_nose_hump_decr_incr - 0.6) < 1e-4, sl.s_nose_hump_decr_incr)
check("sided slider shows on load", abs(sl.s_upperarm_muscle_decr_incr_l - 0.4) < 1e-4)
shape = verts(body)[:human.N_BODY]
sl.s_nose_hump_decr_incr = -0.5
keys = body.data.shape_keys.key_blocks
check("going negative swaps the target", keys["nose-hump-incr"].value == 0 and abs(keys["nose-hump-decr"].value - 0.5) < 1e-4)
check("slider moves the skin", np.linalg.norm(verts(body)[:human.N_BODY] - shape, axis=1).max() > 0.001)
e.symmetric = True
sl.s_upperleg_fat_decr_incr_l = 0.3
check("symmetric moves both sides", abs(keys["r-upperleg-fat-incr"].value - 0.3) < 1e-4)
e.symmetric = False
sl.s_upperleg_fat_decr_incr_l = 0.1
check("apart moves one side", abs(keys["r-upperleg-fat-incr"].value - 0.3) < 1e-4 and abs(keys["l-upperleg-fat-incr"].value - 0.1) < 1e-4)
e.symmetric = True
check("age stops at an adult", e.bl_rna.properties["macro_age"].hard_min == 0.5)
e.race_african = 0.7
race = [e.race_african, e.race_asian, e.race_caucasian]
check("ancestry still sums to 1", abs(sum(race) - 1) < 1e-3, race)
e.sex = "female"
check("sex sets gender", human.get_macro(body, "gender") == 0.0)
e.sex = expected["sex"]
reached = human.set_stature(body, 1.82)
check("stature reaches the target", abs(human.stature(body) - 1.82) < 0.002, f"{reached:.3f} m")
try:
    human.set_stature(body, 2.9)
    check("impossible stature is refused", False)
except ValueError as err:
    check("impossible stature is refused", True, err)
reading = human.settle(body)
check("readout has plausible sizes", 1.7 < reading["stature_m"] < 1.95 and 30 < reading["mass_kg"] < 130, reading)
z = human._evaluated_body(body)[:, 2].min()
check("feet stand on the floor", abs(z) < 1e-4, z)
e.character = "editor_check"
path = os.path.join(out, "editor_check.recipe.json")
r = ed._write_recipe(scene, path)
written = json.load(open(path, encoding="utf-8"))
check("saved recipe is valid", rc.problems(written) == [], rc.problems(written))
check("saved recipe holds the sliders", written["targets"].get("nose-hump-decr") == 0.5 and written["targets"].get("l-upperleg-fat-incr") == 0.1 and "nose-hump-incr" not in written["targets"], written["targets"])
before = verts(body)[:human.N_BODY]
ed._start(scene, written, path)
after = verts(scene.hm_editor.body)[:human.N_BODY]
gap = np.linalg.norm((after - after.mean(0)) - (before - before.mean(0)), axis=1).max()
check("reloading the recipe gives the same skin", gap < 0.001, f"{gap * 1000:.3f} mm")
bad = rc.new("child", "male")
bad["macros"]["age"] = 0.3
try:
    ed._start(scene, bad)
    check("a child's recipe is refused", False)
except ValueError as err:
    check("a child's recipe is refused", True, err)
check("refusing keeps the human", scene.hm_editor.body is not None)

# ---- the tape
import time
ed._start(scene, rc.new("tape_check", "female"))
e, body = scene.hm_editor, scene.hm_editor.body
check("the tape measures on load", ed._state["tape"] and 70 < ed._state["tape"]["bust"] * 100 < 110, ed._state["tape"] and ed._state["tape"]["bust"])
started = time.time()
e.tape_bust = 92.0
e.tape_waist = 68.0
e.tape_hip = 98.0
e.tape_height = 165.0
took = time.time() - started
now = human.measure_body(body)[0]
for key, want in (("bust", 92.0), ("waist", 68.0), ("hip", 98.0), ("height", 165.0)):
    check(f"typed {key} holds with the others", abs(now[key] * 100 - want) < 0.5, f"{now[key] * 100:.1f} cm, {took:.1f} s in all")
e.tape_wrist = 40.0
check("an unreachable measure says so", "Limite" in ed._state["message"], ed._state["message"])
pins = ed._pins(scene)
del pins["wrist"]
ed._set_pins(scene, pins)
for s in ed.SLIDERS:
    if s.name == "measure-wrist-circ-decr-incr":
        for _, pair in s.sides:
            human.set_side(body, pair, 0.0)
e.show_tape = True
check("the tape's lines appear", "HM_tape" in bpy.data.objects and len(bpy.data.objects["HM_tape"].data.splines) == 23, len(bpy.data.objects["HM_tape"].data.splines))
e.show_tape = False
check("the tape's lines go away", "HM_tape" not in bpy.data.objects)
path = os.path.join(out, "editor_check_tape.recipe.json")
written = ed._write_recipe(scene, path)
check("the recipe keeps the typed measures", json.load(open(path, encoding="utf-8")).get("measures_cm", {}).get("bust") == 92.0)
check("a recipe with measures is valid", rc.problems(written) == [])
ed._start(scene, written, path)
check("reloading keeps them", ed._pins(scene).get("hip") == 98.0)
check("reloading gives the same size", abs(human.measure_body(scene.hm_editor.body)[0]["bust"] * 100 - 92.0) < 0.5)

failed = [k for k, v in results.items() if not v["ok"]]
json.dump(results, open(os.path.join(out, "editor_check.json"), "w"), indent=1)
print("checks", len(results), "failed", failed)
sys.exit(1 if failed else 0)

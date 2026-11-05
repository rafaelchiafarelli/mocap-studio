"""How far each slider moves each tape measure, for both sexes. Args: out.json. Run without --blend. Kept in data/measure_sweep.json, the evidence for tape.DRIVERS."""
import json, sys
import bpy
import bl_ext.user_default.hm_editor as ed
from bl_ext.user_default.hm_editor import human, recipe as rc, tape

out = sys.argv[sys.argv.index("--") + 1]
# The measure sliders, and others that might move what those don't, such as the armhole's depth.
NAMES = [x for x in (s.name for s in ed.SLIDERS) if x.startswith("measure-")] + ["torso-scale-vert-decr-incr", "hip-scale-vert-decr-incr", "hip-waist-down-up", "breast-dist-decr-incr", "breast-trans-down-up", "breast-volume-vert-down-up", "torso-scale-depth-decr-incr", "torso-scale-horiz-decr-incr", "torso-vshape-decr-incr", "upperarm-scale-vert-decr-incr"]
BY_NAME = {s.name: s for s in ed.SLIDERS}
rows = {}
for sex in ("female", "male"):
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o)
    body = human.create({**rc.new(sex, sex), "assets": {}})
    topology = human.tape_topology(body)
    keep = lambda: tape.measure(topology, human.all_verts(body))[0]
    base = keep()
    rows[sex] = {"base_cm": {k: round(v * 100, 1) for k, v in base.items()}, "sliders": {}}
    for name in NAMES:
        result = {}
        for value in (0.5, -0.5):
            for _, pair in BY_NAME[name].sides:
                human.set_side(body, pair, value)
            now = keep()
            result[str(value)] = {k: round((now[k] - base[k]) * 100, 1) for k in base if abs(now[k] - base[k]) >= 0.002}
            for _, pair in BY_NAME[name].sides:
                human.set_side(body, pair, 0.0)
        rows[sex]["sliders"][name] = result
        print(sex, name, result["0.5"], flush=True)
json.dump(rows, open(out, "w"), indent=1)

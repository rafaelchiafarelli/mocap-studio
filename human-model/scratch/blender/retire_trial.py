"""One layer out, under the rule in human-model.md: removes the muscle bodies and measures the skin through a walk. Args: out.json. Run with --blend. The file isn't saved."""
import json, os, sys, time
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
out = hb.args()[0]
scene = bpy.context.scene
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
ctrl = bpy.data.objects["HM_controls"]
frames = list(range(scene.frame_start, min(scene.frame_end, scene.frame_start + 40)))


def run():
    ctrl["m_zygomaticus_major_L"] = 0.8
    ctrl["breath"] = 0.5
    ctrl.update_tag()
    t = time.perf_counter()
    res = []
    for f in frames:
        scene.frame_set(f)
        res.append(hb.evaluated_verts(skin))
    return np.array(res), (time.perf_counter() - t) / len(frames) * 1000


before, ms_before = run()
for name in ("HM_muscles", "HM_muscle_rig"):
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o)
for o in list(bpy.data.collections["HM_muscle_targets"].objects):
    bpy.data.objects.remove(o)
after, ms_after = run()
d = np.linalg.norm(before - after, axis=2)
res = {"frames": len(frames), "max_mm": float(d.max() * 1000), "rms_mm": float(np.sqrt((d ** 2).mean()) * 1000), "ms_per_frame_with": ms_before, "ms_per_frame_without": ms_after}
json.dump(res, open(out, "w"), indent=0)
print(res)

"""Frames per second of the model through a walking action, layer by layer. Args: out.json. Run with --blend."""
import json, os, sys, time
import bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
scene = bpy.context.scene
skin = next(o for o in bpy.data.objects if o.name.endswith(".skin"))
out = sys.argv[sys.argv.index("--") + 1]
skin_keys = skin.data.shape_keys.key_blocks
vl = bpy.context.view_layer


def fps(label, frames=48):
    t = time.perf_counter()
    start = scene.frame_start
    for f in range(frames):
        scene.frame_set(start + f % max(1, scene.frame_end - start))
        dg = bpy.context.evaluated_depsgraph_get()
        skin.evaluated_get(dg).to_mesh()
        skin.evaluated_get(dg).to_mesh_clear()
    v = frames / (time.perf_counter() - t)
    print(label, round(v, 1))
    return v


res = {}
res["all_layers"] = fps("all layers")
for c in ("HM_muscles", "HM_muscle_targets"):
    if c in bpy.data.collections:
        bpy.data.collections[c].hide_viewport = True
        vl.layer_collection.children[c].exclude = True
res["without_muscle_bodies"] = fps("without muscle bodies")
if "HM_bones" in bpy.data.collections:
    vl.layer_collection.children["HM_bones"].exclude = True
res["skin_and_rig_only"] = fps("skin and rig only")
json.dump(res, open(out, "w"), indent=0)

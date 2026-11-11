"""An MPFB2 human from a recipe and nothing else: its own rig, helpers masked, skin subdivided on display, no inner layers. Args: recipe.json out.blend out.json
The rig is named HM_rig so blender/walk.py and the other tools can use it. Vertex order stays MPFB's: the first 13,380 are the body."""
import json, os, sys
import addon_utils, bpy
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

N_BODY = 13380
a = hb.args()
recipe = json.load(open(a[0], encoding="utf-8"))
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService

hb.clear_scene()
body = HumanService.create_human(macro_detail_dict=recipe["macros"])
for name, value in recipe.get("targets", {}).items():
    path = TargetService.target_full_path(name)
    if not path:
        raise SystemExit(f"no target {name}")
    TargetService.load_target(body, path, weight=value, name=name)
rig = HumanService.add_builtin_rig(body, "rigify.human")
rig.name = "HM_rig"
body.name = "HM_body"
for poly in body.data.polygons:
    poly.use_smooth = True
if not any(m.type == "SUBSURF" for m in body.modifiers):
    sub = body.modifiers.new("smooth", "SUBSURF")
    sub.levels, sub.render_levels = 1, 2
body.data.materials.clear()
body.data.materials.append(hb.material("HM_skin", (0.72, 0.56, 0.48), roughness=0.5))
bpy.context.view_layer.update()
scene = bpy.context.scene
scene.render.fps = 24
bpy.ops.wm.save_as_mainfile(filepath=a[1])

V = hb.evaluated_verts(body)
mods = [(m.name, m.type) for m in body.modifiers]
base = len(body.data.vertices)
report = {"recipe": recipe.get("name"), "vertices_with_helpers": base, "body_vertices": N_BODY, "modifiers": mods, "bones": len(rig.data.bones),
          "height_m": float(hb.world_verts(body)[:N_BODY, 2].max() - hb.world_verts(body)[:N_BODY, 2].min()), "shape_keys": len(body.data.shape_keys.key_blocks) if body.data.shape_keys else 0}
json.dump(report, open(a[2], "w"), indent=1)
print(report)

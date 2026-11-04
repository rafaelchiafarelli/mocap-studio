"""Renders what each morph target does, for choosing by eye. Args: recipe.json out_dir list.json [head|body]. list.json: {"name": "target,target"}: several targets make one entry, as left and right sides do. One image per entry, from the front and the side."""
import json, os, sys
import addon_utils, bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb
a = hb.args()
recipe = json.load(open(a[0], encoding="utf-8"))
out = a[1]
items = json.load(open(a[2], encoding="utf-8"))
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
hb.clear_scene()
body = HumanService.create_human(macro_detail_dict=recipe["macros"])
hb.setup_render((520, 520), 8)
bpy.context.scene.world.node_tree.nodes["Background"].inputs[1].default_value = 0.5
os.makedirs(out, exist_ok=True)
verts = hb.world_verts(body)
top = verts[:13380, 2].max()
if len(a) > 3 and a[3] == "body":
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 420, 620
    mid = top * 0.60
    front = hb.camera_look("f", (0.0, -2.4, mid), (0, 0, mid), 70)
    side = hb.camera_look("s", (2.4, 0.0, mid), (0, 0, mid), 70)
else:
    front = hb.camera_look("f", (0.10, -0.75, top - 0.11), (0, -0.06, top - 0.115), 70)
    side = hb.camera_look("s", (0.72, -0.08, top - 0.11), (0, -0.06, top - 0.115), 70)
hb.render(os.path.join(out, "_neutral_f.png"), front)
hb.render(os.path.join(out, "_neutral_s.png"), side)
for label, target in items.items():
    names = target.split(",")
    for name in names:
        path = TargetService.target_full_path(name)
        if not path:
            raise SystemExit(f"no target {name}")
        TargetService.load_target(body, path, weight=1.0, name=name)
    bpy.context.view_layer.update()
    hb.render(os.path.join(out, f"{label}_f.png"), front)
    hb.render(os.path.join(out, f"{label}_s.png"), side)
    for name in names:
        body.shape_key_remove(body.data.shape_keys.key_blocks[name])
print("rendered", len(items))

"""Builds the model file. Args: recipe.json bones.npz out.blend [muscles.json fields.npz]
Skin and rig from MPFB, CT and permissive bones parented to the rig, our own jaw, rib and sternum bones, controls and drivers."""
import json, math, os, sys
import addon_utils, bpy
import numpy as np
from mathutils import Matrix, Vector
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hmblender as hb

a = hb.args()
recipe = json.load(open(a[0], encoding="utf-8"))
bones_npz = np.load(a[1])
meta = json.load(open(a[1] + ".json"))
out_blend = a[2]
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.locationservice import LocationService
hb.clear_scene()
body = HumanService.create_human(macro_detail_dict=recipe["macros"])
body.name = recipe.get("name", "human") + ".skin"
from bl_ext.user_default.mpfb.services.targetservice import TargetService
for name, value in recipe.get("targets", {}).items():
    path = TargetService.target_full_path(name)
    if not path:
        raise SystemExit(f"no target {name}")
    TargetService.load_target(body, path, weight=value, name=name)
rig = HumanService.add_builtin_rig(body, "rigify.human")
rig.name = "HM_rig"
# MPFB's weights name a few bones of the generated Rigify rig (DEF-forearm.L.001, ...) that the metarig lacks.
# Merge each into the metarig bone it stands for, or those vertices stay behind when the body bends.
rig_bones = {b.name for b in rig.data.bones}


def metarig_bone(name):
    name = name.removeprefix("DEF-").replace("_master", "")
    while name not in rig_bones and name[-4:-3] == "." and name[-3:].isdigit():
        name = name[:-4]
    return name if name in rig_bones else None


for vg in [g for g in body.vertex_groups if g.name not in rig_bones and g.name.startswith("DEF-")]:
    target_name = metarig_bone(vg.name)
    if target_name is None:
        continue
    target = body.vertex_groups.get(target_name) or body.vertex_groups.new(name=target_name)
    for v in body.data.vertices:
        for g in v.groups:
            if g.group == vg.index and g.weight > 0:
                target.add([v.index], g.weight, "ADD")
    body.vertex_groups.remove(vg)
asset = lambda rel: os.path.join(LocationService.get_user_data(), *rel.split("/"))
assets = {}
for kind, label in (("eyes", "Eyes"), ("teeth", "Teeth"), ("tongue", "Tongue")):
    if recipe.get("assets", {}).get(kind):
        assets[kind] = HumanService.add_mhclo_asset(asset(recipe["assets"][kind]), body, asset_type=label, subdiv_levels=0, material_type="MAKESKIN")
anchors = meta["anchors"]
ctrl = hb.controls_object()
hb.add_prop(ctrl, "jaw_open")
hb.add_prop(ctrl, "breath")

# ---- rig edits: true hip joints, our own jaw, ribs, sternum
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = rig.data.edit_bones
for name, head in anchors.get("rig_edits", {}).items():
    eb[name].head = head
condyle_l, condyle_r = Vector(anchors["condyle_L"]), Vector(anchors["condyle_R"])
pivot = (condyle_l + condyle_r) / 2
jb = eb.new("hm_jaw")
jb.head = pivot
jb.tail = pivot + Vector((0, -0.04, 0))
jb.parent = eb["spine.006"]
jb.use_deform = False
if "jaw_master" in eb:
    eb["jaw_master"].parent = jb
    eb["jaw_master"].use_connect = False
for name, parent in (("hm_hyoid", "spine.005"), ("hm_larynx", "hm_hyoid")):
    h = Vector(anchors[name[3:]])
    nb = eb.new(name)
    nb.head = h
    nb.tail = h + Vector((0, 0, 0.03))
    nb.parent = eb[parent]
    nb.use_deform = False
sb = eb.new("hm_sternum")
top = Vector(anchors["sternum_top"])
sb.head = top
sb.tail = top + Vector((0, 0, -0.1))
sb.parent = eb["spine.003"]
sb.use_deform = False
for i in range(1, 13):
    for side, sign in (("L", 1), ("R", -1)):
        rb = eb.new(f"hm_rib_{i}_{side}")
        h = Vector(anchors[f"rib_head_{i}_{side}"])
        bucket = min(max((i - 1) / 9.0, 0.0), 1.0)
        axis = Vector((sign * (1 - bucket), 0.5 + 0.5 * bucket, 0)).normalized()
        rb.head = h
        rb.tail = h + axis * 0.03
        rb.parent = eb["spine.002" if i > 7 else "spine.003"]
        rb.use_deform = False
bpy.ops.object.mode_set(mode="OBJECT")

# ---- bone meshes
col = hb.collection("HM_bones")
mats = {k: hb.material(f"bone_{k}", c) for k, c in {"ct": (0.86, 0.82, 0.68), "bmf": (0.84, 0.80, 0.70), "rajagopal": (0.80, 0.78, 0.72), "parametric": (0.75, 0.82, 0.86)}.items()}
MAX_FACES = {"cranium": 60000, "mandible": 16000}
for name, b in meta["bones"].items():
    ob = hb.mesh_object(name, bones_npz[f"{name}__v"], bones_npz[f"{name}__f"], col, material=mats[b["source"]])
    hb.decimate(ob, MAX_FACES.get(name, 2400 if name.startswith(("rib", "vertebra")) else 4000))
    for p in ob.data.polygons:
        p.use_smooth = True
    hb.parent_to_bone(ob, rig, b["parent"])

# ---- jaw and breath drivers
jaw = meta.get("jaw")
rig.pose.bones["hm_jaw"].rotation_mode = "XYZ"
if jaw:
    pb = rig.pose.bones["hm_jaw"]
    hb.drive(pb, "rotation_euler", 0, ctrl, "jaw_open", f"x*{jaw['final_rad']:.5f}")
    M = rig.data.bones["hm_jaw"].matrix_local.to_3x3().inverted()
    slide = M @ Vector(jaw["slide_dir"]) * jaw["slide_m"]
    bo = jaw["break_o"]
    for i in range(3):
        hb.drive(pb, "location", i, ctrl, "jaw_open", f"max(x-{bo:.4f},0)/{1 - bo:.4f}*{slide[i]:.6f}")
# The hyoid and larynx follow the jaw, and the head extends a little with it. Both declared, see references/4.
pb = rig.pose.bones["hm_hyoid"]
M = rig.data.bones["hm_hyoid"].matrix_local.to_3x3().inverted()
follow = M @ Vector((0, -0.006, -0.012))
for i in range(3):
    hb.drive(pb, "location", i, ctrl, "jaw_open", f"x*{follow[i]:.5f}")
pb = rig.pose.bones["spine.006"]
pb.rotation_mode = "XYZ"
hb.drive(pb, "rotation_euler", 0, ctrl, "jaw_open", f"x*{math.radians(-4):.5f}")
for i in range(1, 13):
    deg = 9.0 if i <= 10 else 3.0
    for side, sign in (("L", 1), ("R", -1)):
        pb = rig.pose.bones[f"hm_rib_{i}_{side}"]
        pb.rotation_mode = "XYZ"
        hb.drive(pb, "rotation_euler", 1, ctrl, "breath", f"x*{-sign * math.radians(deg):.5f}")
pb = rig.pose.bones["hm_sternum"]
M = rig.data.bones["hm_sternum"].matrix_local.to_3x3().inverted()
lift = M @ Vector((0, -0.010, 0.006))
for i in range(3):
    hb.drive(pb, "location", i, ctrl, "breath", f"x*{lift[i]:.5f}")

# ---- tongue: its own controls on the rig's three tongue bones. Tip raise and back raise are the intrinsic longitudinal muscles and styloglossus; protrude is genioglossus.
for prop, lo, hi in (("tongue_tip_raise", -1.0, 1.0), ("tongue_body_raise", -1.0, 1.0), ("tongue_back_raise", -1.0, 1.0), ("tongue_protrude", -1.0, 1.0)):
    hb.add_prop(ctrl, prop, 0.0, lo, hi)
for bone, prop, deg in (("tongue", "tongue_tip_raise", 35.0), ("tongue.001", "tongue_body_raise", 18.0), ("tongue.002", "tongue_back_raise", 22.0)):
    pb = rig.pose.bones[bone]
    pb.rotation_mode = "XYZ"
    hb.drive(pb, "rotation_euler", 0, ctrl, prop, f"x*{math.radians(deg):.5f}")
pb = rig.pose.bones["tongue.002"]
M = rig.data.bones["tongue.002"].matrix_local.to_3x3().inverted()
forward = M @ Vector((0, -0.016, 0))
for i in range(3):
    hb.drive(pb, "location", i, ctrl, "tongue_protrude", f"x*{forward[i]:.5f}")

# ---- joint limits on the main hinges
limits = meta.get("limits", {})
for side in ("L", "R"):
    for stem, (lo, hi) in limits.items():
        pb = rig.pose.bones.get(f"{stem}.{side}")
        if pb is None:
            continue
        pb["hm_limit_deg"] = [lo, hi]

# ---- muscles and fields
if len(a) > 3:
    muscles = json.load(open(a[3], encoding="utf-8"))
    fields = np.load(a[4]) if len(a) > 4 else None
    import hmmuscles
    if fields is not None:
        hmmuscles.add_fields(body, ctrl, muscles, fields, rig)
    hmmuscles.add_muscle_bodies(rig, body, ctrl, muscles)

rig["hm_sex"] = recipe.get("sex", "male")
bpy.ops.wm.save_as_mainfile(filepath=out_blend, compress=True)
print("saved", out_blend, "objects", len(bpy.data.objects))

"""Args: recipe.json, output.blend. MPFB human + detail targets + CC0 system assets + seeded strand hair."""
import json, os, sys
import addon_utils, bpy
args = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])))
import hair
import aging
recipe = json.load(open(args[0], encoding="utf-8"))
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.locationservice import LocationService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
from mathutils.bvhtree import BVHTree
import numpy as np

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o)
data = LocationService.get_user_data()
asset = lambda rel: os.path.join(data, *rel.split("/"))

body = HumanService.create_human(macro_detail_dict=recipe["macros"])
body.name = recipe["name"] + ".body"
for name, value in recipe["targets"].items():
    path = TargetService.target_full_path(name)
    if not path:
        raise SystemExit(f"no target {name}")
    TargetService.load_target(body, path, weight=value, name=name)
rig = HumanService.add_builtin_rig(body, "rigify.human")
# MPFB's weights name a few bones of the generated Rigify rig (DEF-forearm.L.001, ...) that the metarig lacks:
# merge each into the metarig bone it stands for, or those vertices will not follow the arm.
bones = {b.name for b in rig.data.bones}


def metarig_bone(name):
    name = name.removeprefix("DEF-").replace("_master", "")
    while name not in bones and name[-4:-3] == "." and name[-3:].isdigit():
        name = name[:-4]
    return name if name in bones else None


for vg in [g for g in body.vertex_groups if g.name not in bones and g.name.startswith("DEF-")]:
    target_name = metarig_bone(vg.name)
    if target_name is None:
        continue
    target = body.vertex_groups.get(target_name) or body.vertex_groups.new(name=target_name)
    for v in body.data.vertices:
        for g in v.groups:
            if g.group == vg.index and g.weight > 0:
                target.add([v.index], g.weight, "ADD")
    body.vertex_groups.remove(vg)
HumanService.set_character_skin(asset(recipe["assets"]["skin"]), body, skin_type="ENHANCED_SSS")
objs = {}
for kind, label in (("eyes", "Eyes"), ("teeth", "Teeth"), ("tongue", "Tongue"), ("eyelashes", "Eyelashes")):
    objs[kind] = HumanService.add_mhclo_asset(asset(recipe["assets"][kind]), body, asset_type=label, subdiv_levels=1, material_type="MAKESKIN")
for rel in recipe["assets"]["clothes"]:
    HumanService.add_mhclo_asset(asset(rel), body, asset_type="Clothes", subdiv_levels=1, material_type="MAKESKIN")
before = set(bpy.data.objects)
HumanService.add_mhclo_asset(asset(recipe["assets"]["eyebrow_card"]), body, asset_type="Eyebrows", subdiv_levels=0, material_type="MAKESKIN")
brow_card = (set(bpy.data.objects) - before).pop()


def recolor_clothes(mat, look):
    """Saturated texels (the denim) take the work colour; pale ones (the shirt) take the under colour."""
    t = mat.node_tree
    bsdf = next(n for n in t.nodes if n.bl_idname == "ShaderNodeBsdfPrincipled")
    link = bsdf.inputs["Base Color"].links[0]
    src = link.from_socket
    sep = t.nodes.new("ShaderNodeSeparateColor"); sep.mode = "HSV"
    t.links.new(src, sep.inputs[0])
    mask = t.nodes.new("ShaderNodeMapRange")
    mask.inputs["From Min"].default_value, mask.inputs["From Max"].default_value = 0.12, 0.3
    t.links.new(sep.outputs[1], mask.inputs["Value"])
    mix_colour = t.nodes.new("ShaderNodeMix"); mix_colour.data_type = "RGBA"
    mix_colour.inputs["A"].default_value = (*look["under_rgb"], 1)
    mix_colour.inputs["B"].default_value = (*look["work_rgb"], 1)
    t.links.new(mask.outputs[0], mix_colour.inputs["Factor"])
    mult = t.nodes.new("ShaderNodeMath"); mult.operation = "MULTIPLY"; mult.inputs[1].default_value = 1.7
    t.links.new(sep.outputs[2], mult.inputs[0])
    shade = t.nodes.new("ShaderNodeMix"); shade.data_type = "RGBA"; shade.blend_type = "MULTIPLY"; shade.inputs["Factor"].default_value = 1
    t.links.new(mix_colour.outputs["Result"], shade.inputs["A"])
    comb = t.nodes.new("ShaderNodeCombineColor")
    for i in range(3):
        t.links.new(mult.outputs[0], comb.inputs[i])
    t.links.new(comb.outputs[0], shade.inputs["B"])
    t.links.remove(link)
    t.links.new(shade.outputs["Result"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.85


for o in bpy.data.objects:
    if "worksuit" in o.name:
        recolor_clothes(o.data.materials[0], recipe["clothes_look"])

# Strand hair is generated on the final deformed mesh (shape keys applied, helpers and hidden parts gone).
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get()
surface = body.evaluated_get(dg).to_mesh()
eye = np.array([(objs["eyes"].matrix_world @ v.co) for v in objs["eyes"].data.vertices])
verts = np.array([v.co for v in surface.vertices])
top_z = verts[:, 2].max()
near = verts[verts[:, 2] > eye[:, 2].mean()]
frame = {"cx": float(near[:, 0].mean()), "cy": float((near[:, 1].min() + near[:, 1].max()) / 2), "eye_z": float(eye[:, 2].mean()),
         "top_z": float(top_z), "ear_x": float(np.abs(near[:, 0] - near[:, 0].mean()).max() * 0.86)}
print("RESULT frame", {k: round(v, 3) for k, v in frame.items()})
bvh = BVHTree.FromPolygons([v.co.copy() for v in surface.vertices], [tuple(p.vertices) for p in surface.polygons])
mat = hair.hair_material(recipe["hair_look"])
seed = recipe["seed"]
hair.scalp(surface, frame, recipe["scalp_hair"], rig, body, mat, bvh, seed)
hair.eyebrows(brow_card, frame, recipe["brows"], rig, body, mat, bvh, seed + 1)
hair.fine_hair(surface, frame, recipe["fine_hair"], rig, body, mat, bvh, seed + 2)
bpy.data.objects.remove(brow_card)



def tune_skin(look):
    seen = set()
    for mat in bpy.data.materials:
        for n in (mat.node_tree.nodes if mat.use_nodes else []):
            if n.bl_idname != "ShaderNodeGroup":
                continue
            for key, value in look.items():
                if key in n.inputs and n.inputs[key].type == "RGBA":
                    n.inputs[key].default_value = (*value, 1)
                elif key in n.inputs:
                    n.inputs[key].default_value = value
            t = n.node_tree
            if t.name in seen:  # material instances share one group; tint it once
                continue
            seen.add(t.name)
            bsdf = next(x for x in t.nodes if x.bl_idname == "ShaderNodeBsdfPrincipled")
            link = bsdf.inputs["Base Color"].links[0]
            hsv = t.nodes.new("ShaderNodeHueSaturation")
            hsv.inputs["Saturation"].default_value = look["saturation"]
            hsv.inputs["Value"].default_value = look["value"]
            t.links.new(link.from_socket, hsv.inputs["Color"])
            t.links.new(hsv.outputs[0], bsdf.inputs["Base Color"])


def tune_eye(mat, look):
    t = mat.node_tree
    bsdf = next(x for x in t.nodes if x.bl_idname == "ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = look["roughness"]
    link = bsdf.inputs["Base Color"].links[0]
    hsv = t.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Hue"].default_value = look["hue"]
    hsv.inputs["Saturation"].default_value = look["saturation"]
    hsv.inputs["Value"].default_value = look["value"]
    t.links.new(link.from_socket, hsv.inputs["Color"])
    t.links.new(hsv.outputs[0], bsdf.inputs["Base Color"])


tune_skin(recipe["skin_look"])
teeth = np.array([(objs["teeth"].matrix_world @ v.co) for v in objs["teeth"].data.vertices])
right = eye[eye[:, 0] > frame["cx"]]
head_verts = verts[(verts[:, 2] > frame["eye_z"] - 0.13) & (verts[:, 2] < frame["eye_z"]) & (np.abs(verts[:, 0] - frame["cx"]) < 0.015) & (verts[:, 1] < frame["cy"])]
nose_tip_z = float(head_verts[np.argmin(head_verts[:, 1]), 2])
chin_candidates = verts[(np.abs(verts[:, 0] - frame["cx"]) < 0.012) & (verts[:, 2] < float(teeth[:, 2].mean())) & (verts[:, 2] > float(teeth[:, 2].mean()) - 0.08) & (verts[:, 1] < frame["cy"] - 0.02)]
face = {"cx": frame["cx"], "cy": frame["cy"], "eye_x": float(np.abs(right[:, 0].mean() - frame["cx"])), "eye_z": frame["eye_z"],
        "brow_z": frame["eye_z"] + 0.02, "nose_z": nose_tip_z, "mouth_z": float(teeth[:, 2].mean()),
        "chin_z": float(chin_candidates[:, 2].min()), "neck_z": frame["eye_z"] - 0.26}
print("RESULT face", {k: round(v, 3) for k, v in face.items()})
height_img, tone_img = aging.build_maps(surface, face, recipe["aging"], seed + 3, args[1].rsplit("\\", 1)[0])
group = next(n.node_tree for n in bpy.data.materials["character.body"].node_tree.nodes if n.bl_idname == "ShaderNodeGroup")
aging.apply_maps(group, height_img, tone_img, recipe["aging"])
tune_eye(objs["eyes"].data.materials[0], recipe["eye_look"])
for o in bpy.data.objects:
    for mod in (o.modifiers if o.type == "MESH" else []):
        if mod.type == "SUBSURF":
            mod.render_levels = 2
sub = body.modifiers.new("Subdivision", "SUBSURF")
sub.levels, sub.render_levels = 1, 2
group = next(n.node_tree for n in bpy.data.materials["character.body"].node_tree.nodes if n.bl_idname == "ShaderNodeGroup")
print("RESULT skin_group", group.name, sorted({n.bl_idname for n in group.nodes}), [i.name for i in group.interface.items_tree][:16])
print("RESULT height", round(max((body.matrix_world @ v.co).z for v in body.data.vertices), 3))
import hashlib
for o in bpy.data.objects:
    if o.type == "CURVES":
        a = np.empty(len(o.data.attributes["position"].data) * 3, dtype=np.float32)
        o.data.attributes["position"].data.foreach_get("vector", a)
        print("RESULT hash", o.name, len(o.data.curves), hashlib.sha256(a.tobytes()).hexdigest()[:16])
bpy.ops.wm.save_mainfile(filepath=args[1])

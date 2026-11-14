"""Step 2 of the pose-capture investigation: gives Rafael's MPFB body (object `Human`, no rig) MPFB's Rigify metarig, in place.

    python3 human-model/blender_run.py --blend BODY.blend human-model/investigations/pose-capture/rig_body.py OUT.blend CHECK_DIR

The body is not rebuilt from a recipe: MPFB fits the rig to the mesh as it is, shape keys included, so the body stays exactly his.
The rig is named HM_rig and the body HM_body, as `blender/clean_body.py` does, so `blender/body_drive.py` can key it.
The orphan DEF-* weights are merged into real bones as in `clean_body.py`, or the limbs tear.
CHECK_DIR gets stills of the body at rest and in a test pose (arms up, one knee bent, trunk turned), to check the skinning.
"""
import json, math, os, sys
import addon_utils, bpy
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(sys.argv[sys.argv.index("--python") + 1])), "..", "..", "blender"))
import hmblender as hb
from mathutils import Vector

a = hb.args()
out, check = a[0], a[1]
addon_utils.enable("rigify", default_set=True)
from bl_ext.user_default.mpfb.services.humanservice import HumanService

body = bpy.data.objects["Human"]
rig = HumanService.add_builtin_rig(body, "rigify.human")
rig.name, body.name = "HM_rig", "HM_body"
HEAD_BONE = "spine.006"


def merge_orphan_weights():
    """Same as clean_body.py's: MPFB's weights name Rigify's generated twist bones, which the metarig lacks."""
    bones = {b.name for b in rig.data.bones}
    merged = {}
    for name in [g.name for g in body.vertex_groups if g.name.startswith("DEF-") and g.name not in bones]:
        target = HEAD_BONE if "eye_master" in name else name[len("DEF-"):].replace(".001", "")
        if target not in bones:
            continue
        source, sink = body.vertex_groups[name], body.vertex_groups.get(target) or body.vertex_groups.new(name=target)
        count = 0
        for v in body.data.vertices:
            for g in v.groups:
                if g.group == source.index and g.weight > 0:
                    sink.add([v.index], g.weight, "ADD")
                    count += 1
        body.vertex_groups.remove(source)
        merged[name] = (target, count)
    return merged


merged = merge_orphan_weights()
unweighted = sum(1 for v in body.data.vertices[:13380] if not any(g.weight > 0 and body.vertex_groups[g.group].name in rig.data.bones for g in v.groups))
for poly in body.data.polygons:
    poly.use_smooth = True
if not body.data.materials:
    body.data.materials.append(hb.material("HM_skin", (0.72, 0.56, 0.48), roughness=0.5))
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=out)
report = {"bones": len(rig.data.bones), "merged_orphan_weights": merged, "body_vertices_without_bone_weight": unweighted,
          "bone_names": [b.name for b in rig.data.bones]}
json.dump(report, open(os.path.join(check, "rig_report.json"), "w"), indent=1)
print({k: v for k, v in report.items() if k != "bone_names"})

# stills for checking the skinning; not saved in OUT.blend
hb.setup_render(res=(900, 1300), samples=16)
top = max((body.matrix_world @ Vector(c)).z for c in body.bound_box)
cam = hb.camera_look("check_cam", (0.0, -4.2, top * 0.55), (0.0, 0.0, top * 0.5), lens=50)
cam2 = hb.camera_look("check_cam_side", (4.2, 0.0, top * 0.55), (0.0, 0.0, top * 0.5), lens=50)
hb.render(os.path.join(check, "rest_front.png"), cam)
hb.render(os.path.join(check, "rest_side.png"), cam2)
P = rig.pose.bones
for pb in P:
    pb.rotation_mode = "XYZ"
P["upper_arm.L"].rotation_euler = (0, 0, math.radians(-70))
P["upper_arm.R"].rotation_euler = (0, 0, math.radians(70))
P["forearm.L"].rotation_euler = (math.radians(60), 0, 0)
P["thigh.R"].rotation_euler = (math.radians(50), 0, 0)
P["shin.R"].rotation_euler = (math.radians(-80), 0, 0)
P["spine.002"].rotation_euler = (0, math.radians(25), 0)
P["spine.004"].rotation_euler = (math.radians(20), 0, 0)
bpy.context.view_layer.update()
hb.render(os.path.join(check, "pose_front.png"), cam)
hb.render(os.path.join(check, "pose_side.png"), cam2)

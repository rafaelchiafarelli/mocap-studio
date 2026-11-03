"""Opened on a .blend keyed with upper face and head. Args: data JSON, output .blend. Adds the control object, drivers and first bake."""
import json, math, sys
import bpy
from mathutils import Vector
data_path, out = sys.argv[sys.argv.index("--") + 1:][:2]
txt = bpy.data.texts.new("mouth_data.json"); txt.write(open(data_path).read())
d = json.loads(txt.as_string())
props = sorted({k for p in d["poses"].values() for k in p})
s = bpy.context.scene
ctrl = bpy.data.objects.new("mouth_control", None); s.collection.objects.link(ctrl)
for k in props:
    ctrl[k] = 0.0
def drive(owner, path, prop, index=-1, scale=1.0):
    fc = owner.driver_add(path, index) if index >= 0 else owner.driver_add(path)
    drv = fc.driver; drv.type = "SCRIPTED"
    v = drv.variables.new(); v.name = "x"; v.type = "SINGLE_PROP"
    v.targets[0].id = ctrl; v.targets[0].data_path = f'["{prop}"]'
    drv.expression = f"x*{scale:.6f}" if scale != 1.0 else "x"
n = 0
for o in bpy.data.objects:
    if o.type == "MESH" and o.data.shape_keys:
        for k in props:
            kb = o.data.shape_keys.key_blocks.get(k)
            if kb:
                drive(kb, "value", k); n += 1
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for name, deg in (("tongue", 22), ("tongue.001", 30), ("tongue.002", 30)):
    b = rig.pose.bones[name]; b.rotation_mode = "XYZ"
    drive(b, "rotation_euler", "tongueUp", 0, math.radians(deg)); n += 1
# F: the lower lip's bones pull back and up, under the upper teeth.
bite = Vector((0, 0.004, 0.0035))
for name in ("lip.B.L", "lip.B.L.001", "lip.B.R", "lip.B.R.001"):
    b = rig.pose.bones[name]
    local = rig.data.bones[name].matrix_local.to_3x3().inverted() @ bite
    for i in range(3):
        if abs(local[i]) > 1e-6:
            drive(b, "location", "lipBite", i, local[i]); n += 1
print("RESULT drivers", n, "props", props)
import addon_utils
addon_utils.enable("bl_ext.user_default.mouth_faders", default_set=True)
import bl_ext.user_default.mouth_faders as mf
mf.bake(s)
for scr in bpy.data.screens:
    for area in scr.areas:
        if area.type == "VIEW_3D":
            area.spaces.active.show_region_ui = True
bpy.ops.wm.save_mainfile(filepath=out)
print("RESULT saved", out)

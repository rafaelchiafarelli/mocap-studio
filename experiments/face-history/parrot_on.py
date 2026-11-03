"""Opened on a .blend keyed with upper face and head. Args: poses JSON, phoneme table, output .blend.
Adds the control object and drivers, then runs Parrot unmodified except for telling the recognizer the language."""
import json, math, sys
import bpy
from bpy_extras import anim_utils
poses_path, table, out = sys.argv[sys.argv.index("--") + 1:][:3]
poses = json.load(open(poses_path))
props = sorted({k for p in poses.values() for k in p})
s = bpy.context.scene
ctrl = bpy.data.objects.new("character.mouth", None); s.collection.objects.link(ctrl)
for k in props:
    ctrl[k] = 0.0
def drive(owner, path, prop, index=-1, scale=1.0):
    d = owner.driver_add(path, index) if index >= 0 else owner.driver_add(path)
    drv = d.driver; drv.type = "SCRIPTED"
    v = drv.variables.new(); v.name = "x"; v.type = "SINGLE_PROP"
    v.targets[0].id = ctrl; v.targets[0].data_path = f'["{prop}"]'
    drv.expression = f"x*{scale}" if scale != 1.0 else "x"
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
print("RESULT drivers", n, "props", len(props))
for name, p in poses.items():
    a = bpy.data.actions.new(name); a.use_fake_user = True
    slot = a.slots.new(id_type="OBJECT", name="pose")
    bag = anim_utils.action_ensure_channelbag_for_slot(a, slot)
    for k in props:  # every pose keys every property, so nothing sticks from the pose before
        bag.fcurves.new(f'["{k}"]').keyframe_points.insert(1, p.get(k, 0.0))
pp = s.props
pp.phoneme_table_path = table
bpy.ops.parrot.reload_phoneme_table()
for item in pp.phoneme_poses:
    item.pose = bpy.data.actions[item.group]
pp.target_object = ctrl
pp.key_interpolation = "bezier"
for st in s.sequence_editor.strips_all:
    st.select = st.type == "SOUND"
print("RESULT strips", [(x.name, x.type, x.select, x.sound.filepath) for x in s.sequence_editor.strips_all if x.type == "SOUND"])
import bl_ext.user_default.parrot_lipsync.parrot_lipsync as parrot
class Portuguese:
    def __init__(self, model): self.model = model
    def recognize(self, path, timestamp=True): return self.model.recognize(path, lang_id="por", timestamp=timestamp)
parrot.allosaurus_model = Portuguese(parrot.read_recognizer("latest"))
print("RESULT op", bpy.ops.parrot.render_lipsync_to_object_nla())
ad = ctrl.animation_data
for t in ad.nla_tracks:
    for st in t.strips:
        a = st.action; slot = a.slots[0]; st.action_slot = slot
        bag = anim_utils.action_get_channelbag_for_slot(a, slot)
        for fc in bag.fcurves:
            fc.update()  # Parrot copies the poses' absolute handles; recompute them at the new times
        print("RESULT action", a.name, a.frame_range[:], "curves", len(bag.fcurves), "markers", [(m.name, m.frame) for m in a.pose_markers][:12], "strip", st.frame_start, st.frame_end)
        vals = [fc.evaluate(f / 2) for fc in bag.fcurves for f in range(2, 1200, 3)]
        print("RESULT eval range", round(min(vals), 3), round(max(vals), 3))
bpy.ops.wm.save_mainfile(filepath=out)
print("RESULT saved", out)

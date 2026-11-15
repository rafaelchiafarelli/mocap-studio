"""MPFB ganho 3: every slider in MPFB's Model panel goes from -3 to 3, at the same scale, and a Reset button returns the human to MPFB's defaults.
Exploratory (Rafael, 2026-11-14). Patches MPFB 2.0.18 from outside, at run time: MPFB's files on disk aren't touched.

What changes:
- Shape keys MPFB loads or sets get slider_min -10 and slider_max 10 (Blender's most), since Blender clamps a key's value to its slider range (0 to 1 by default) and a macro's targets take products of weights, which pass 3.
- A key at a negative value is kept: MPFB removed any key below 0.0001 when pruning.
- Macros (gender, age, muscle, weight, height, proportions, cupsize, firmness) outside 0 to 1 continue the nearest of MPFB's segments in a straight line, so their low and high targets can take negative weights or weights above 1.
- A negative race weight gets its race-gender-age targets with negative weight.
- The scene properties MPFB's panels draw are registered again with min -3 and max 3, with MPFB's own getters and setters."""
import importlib
import itertools
import os
import sys

import bpy

LIMIT = 3.0
KEY_LIMIT = 10.0  # Blender's most for a shape key: a macro's targets mix products of weights, which pass 3 when two macros are past their ends
MPFB = "bl_ext.user_default.mpfb"
CUTOFF = 0.01
_state = {"applied": False, "originals": {}}


def _mpfb_ready():
    return MPFB in sys.modules and hasattr(bpy.types, "MPFB_PT_Model_Panel")


def _mods():
    ts = importlib.import_module(MPFB + ".services.targetservice")
    sub = importlib.import_module(MPFB + ".ui.model._modelsubpanels")
    mac = importlib.import_module(MPFB + ".ui.model._macrosubpanel")
    return ts, sub, mac


def _widen(key):
    if key.slider_min > -KEY_LIMIT:
        key.slider_min = -KEY_LIMIT
    if key.slider_max < KEY_LIMIT:
        key.slider_max = KEY_LIMIT


def _patch_services(ts):
    TS = ts.TargetService
    orig = _state["originals"]
    for name in ("set_target_value", "load_target", "_interpolate_macro_components", "calculate_target_stack_from_macro_info_dict", "reapply_macro_details"):
        orig[name] = TS.__dict__[name]
    load = orig["load_target"].__func__
    interpolate = orig["_interpolate_macro_components"].__func__
    stack = orig["calculate_target_stack_from_macro_info_dict"].__func__
    cfg = ts._MACRO_CONFIG["macrotargets"]

    def set_target_value(blender_object, target_name, value, delete_target_on_zero=False):
        if blender_object is None or not target_name:
            raise ValueError("Empty object or target")
        keys = blender_object.data.shape_keys
        if keys is None or len(keys.key_blocks) < 1:
            raise ValueError("Empty object or target")
        key = keys.key_blocks.get(target_name)
        if key is None:
            return
        _widen(key)
        key.value = value
        if abs(value) < 0.0001 and delete_target_on_zero:
            blender_object.shape_key_remove(key)

    def load_target(blender_object, full_path, *, weight=0.0, name=None):
        key = load(blender_object, full_path, weight=0.0, name=name)
        if key is not None:
            _widen(key)
            key.value = weight
        return key

    def interpolate_macro_components(macro_name, value):
        parts = cfg[macro_name]["parts"]
        if parts[0]["lowest"] < value < parts[-1]["highest"]:
            return interpolate(macro_name, value)
        # Outside MPFB's range: the nearest segment, continued in a straight line with MPFB's own formula, so the scale doesn't change.
        part = parts[0] if value <= parts[0]["lowest"] else parts[-1]
        t = (value - part["lowest"]) / (part["highest"] - part["lowest"])
        out = []
        if part["low"]:
            out.append([part["low"], round(1 - t, 4)])
        if part["high"]:
            out.append([part["high"], round(t, 4)])
        return out

    def calculate_target_stack(macro_info=None, cutoff=CUTOFF):
        if macro_info is None:
            macro_info = TS.get_default_macro_info_dict()
        # MPFB keeps weights above the cutoff; a straight line past an end gives negative ones, so take all and cut by size.
        targets = [t for t in stack(macro_info, cutoff=-1e9) if abs(t[1]) > cutoff]
        races = macro_info["race"]
        ages = TS._interpolate_macro_components("age", macro_info["age"])
        genders = TS._interpolate_macro_components("gender", macro_info["gender"])
        for race, rw in races.items():
            if rw < -0.0001:
                for (age, aw), (gender, gw) in itertools.product(ages, genders):
                    w = rw * gw * aw
                    if abs(w) > cutoff:
                        targets.append(["macrodetails/" + race + "-" + gender + "-" + age, w])
        return targets

    def reapply_macro_details(basemesh, remove_zero_weight_targets=True):
        macro_info = TS.get_macro_info_dict_from_basemesh(basemesh)
        for target in TS.get_current_macro_targets(basemesh, decode_names=False):
            basemesh.data.shape_keys.key_blocks[target].value = 0.0
        current = TS.get_current_macro_targets(basemesh, decode_names=True)
        required = TS.calculate_target_stack_from_macro_info_dict(macro_info)
        location = importlib.import_module(MPFB + ".services.locationservice").LocationService
        for target in required:
            requested = str(TS.macrodetail_filename_to_shapekey_name(target[0], encode_name=False)).strip()
            if requested not in current:
                to_load = os.path.join(location.get_mpfb_data("targets"), target[0] + ".target.gz")
                TS.load_target(basemesh, to_load, weight=0.0, name=TS.macrodetail_filename_to_shapekey_name(to_load, encode_name=True))
        for target in required:
            TS.set_target_value(basemesh, str(TS.macrodetail_filename_to_shapekey_name(target[0], encode_name=True)).strip(), target[1])
        if remove_zero_weight_targets and basemesh.data.shape_keys:
            for key in list(basemesh.data.shape_keys.key_blocks):
                if str(key.name).startswith("$md") and abs(key.value) < 0.0001:
                    basemesh.shape_key_remove(key)

    TS.set_target_value = staticmethod(set_target_value)
    TS.load_target = staticmethod(load_target)
    TS._interpolate_macro_components = staticmethod(interpolate_macro_components)
    TS.calculate_target_stack_from_macro_info_dict = staticmethod(calculate_target_stack)
    TS.reapply_macro_details = staticmethod(reapply_macro_details)


def _widen_scene_properties(sub, mac):
    """MPFB's scene properties again, with MPFB's getters and setters and min -3, max 3."""
    from bpy.props import FloatProperty
    count = 0
    for section_name, section in sub._sections.items():
        for i, cat in enumerate(section["categories"]):
            if cat["has_left_and_right"]:
                for side in ("left", "right"):
                    ident = sub._category_identifier(section_name, cat["name"], side)
                    get = sub._sided_getter_factory(section_name, ident, i, side)
                    set_ = sub._sided_setter_factory(section_name, ident, i, side)
                    setattr(bpy.types.Scene, ident, FloatProperty(name=ident, get=get, set=set_, description="Set target value (ganho 3)", min=-LIMIT, max=LIMIT))
                    count += 1
            else:
                ident = sub._category_identifier(section_name, cat["name"])
                get = sub._unsided_getter_factory(section_name, ident, i)
                set_ = sub._unsided_setter_factory(section_name, ident, i)
                setattr(bpy.types.Scene, ident, FloatProperty(name=ident, get=get, set=set_, description="Set target value (ganho 3)", min=-LIMIT, max=LIMIT))
                count += 1
    for targets in mac._MACROTARGETS.values():
        for target in targets:
            old = bpy.types.Scene.bl_rna.properties.get(mac._INTERNAL_PREFIX + target)
            label = old.name if old else target
            text = old.description if old else target
            setattr(bpy.types.Scene, mac._INTERNAL_PREFIX + target, FloatProperty(name=label, description=text + " (ganho 3)", get=mac._macro_getter_factory(target), set=mac._macro_setter_factory(target), min=-LIMIT, max=LIMIT))
            count += 1
    return count


def _basemesh(context):
    from importlib import import_module
    obj = import_module(MPFB + ".services.objectservice").ObjectService
    return obj.find_object_of_type_amongst_nearest_relatives(context.active_object, "Basemesh") if context.active_object else None


def reset_human(basemesh):
    """MPFB's defaults: macros as get_default_macro_info_dict, every other target removed. Returns how many targets went."""
    ts = importlib.import_module(MPFB + ".services.targetservice").TargetService
    props = importlib.import_module(MPFB + ".entities.objectproperties").HumanObjectProperties
    defaults = ts.get_default_macro_info_dict()
    for name, value in defaults.items():
        if name == "race":
            for race, rv in value.items():
                props.set_value(race, rv, entity_reference=basemesh)
        else:
            props.set_value(name, value, entity_reference=basemesh)
    removed = 0
    keys = basemesh.data.shape_keys
    if keys:
        for key in list(keys.key_blocks)[1:]:
            if not str(key.name).startswith("$md"):
                basemesh.shape_key_remove(key)
                removed += 1
    ts.reapply_macro_details(basemesh, remove_zero_weight_targets=True)
    from importlib import import_module
    model = import_module(MPFB + ".ui.model.modelpanel")
    if model.MODEL_PROPERTIES.get_value("refit", entity_reference=bpy.context.scene):
        import_module(MPFB + ".services.humanservice").HumanService.refit(basemesh)
    return removed


class MPFBGANHO_OT_reset(bpy.types.Operator):
    """Every MPFB slider of this human back to MPFB's default: macros 0.5, races 0.33, modifiers 0"""
    bl_idname = "mpfb_ganho.reset"
    bl_label = "Reset"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return _basemesh(context) is not None

    def execute(self, context):
        removed = reset_human(_basemesh(context))
        self.report({"INFO"}, f"Padrão MPFB: {removed} modificadores removidos")
        return {"FINISHED"}


class MPFBGANHO_PT_panel(bpy.types.Panel):
    bl_label = "Ganho 3 e Reset"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_parent_id = "MPFB_PT_Model_Panel"
    bl_order = 0

    def draw(self, context):
        col = self.layout.column()
        col.label(text=f"Sliders de {-LIMIT:g} a {LIMIT:g}" if _state["applied"] else "MPFB não encontrado", icon="INFO")
        col.operator(MPFBGANHO_OT_reset.bl_idname, icon="LOOP_BACK")


def apply():
    """Patches MPFB once it's loaded. Returns True when done."""
    if _state["applied"]:
        return True
    if not _mpfb_ready():
        return False
    ts, sub, mac = _mods()
    _patch_services(ts)
    n = _widen_scene_properties(sub, mac)
    MPFBGANHO_PT_panel.bl_category = bpy.types.MPFB_PT_Model_Panel.bl_category
    bpy.utils.register_class(MPFBGANHO_PT_panel)
    _state["applied"] = True
    _state["properties"] = n
    print(f"mpfb_ganho: {n} sliders from {-LIMIT:g} to {LIMIT:g}")
    return True


def _retry():
    return None if apply() else 0.5


def register():
    bpy.utils.register_class(MPFBGANHO_OT_reset)
    if not apply():
        bpy.app.timers.register(_retry, first_interval=0.5, persistent=True)


def unregister():
    if _state["applied"]:
        bpy.utils.unregister_class(MPFBGANHO_PT_panel)
        ts = importlib.import_module(MPFB + ".services.targetservice").TargetService
        for name, fn in _state["originals"].items():
            setattr(ts, name, fn)
        _state["applied"] = False
    bpy.utils.unregister_class(MPFBGANHO_OT_reset)

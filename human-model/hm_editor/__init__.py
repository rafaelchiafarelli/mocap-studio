"""Human Model Editor: the sidebar tab "Human". On a plain MPFB human: every slider, saving the recipe, and building every layer.
On a built model: the live controls and the layers. Identity is baked in a built file, so its identity sliders are never shown there (docs/character-editor.md)."""
import json, os, tempfile, textwrap
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty
from . import builder, catalog, human, recipe as rc, tape

SLIDERS = []
_state = {"message": "", "readout": None, "build": None, "built_blend": None, "unsaved": False, "failed": None, "tape": None}
SETTLE_DELAY_S = 0.3
MACROS = (("age", "Age", 0.5, 1.0, "From 0.5, adult, to 1, old. Below 0.5 MPFB makes a child's body, so it stops there"), ("height", "Height", 0.0, 1.0, "Not linear: use Stature above for metres"),
          ("weight", "Weight", 0.0, 1.0, "A narrow range: full weight is still a normal BMI. A heavy character also needs Belly and fat sliders"),
          ("muscle", "Muscle •", 0.0, 1.0, "Skin only: the muscle layer doesn't follow it (bug 6)"), ("proportions", "Proportions", 0.0, 1.0, "Body proportions"),
          ("cupsize", "Cup size •", 0.0, 1.0, "Skin only: there's no breast tissue layer"), ("firmness", "Firmness •", 0.0, 1.0, "Skin only"))
SEX_ITEMS = (("male", "Male", "Male skin, CT donor, joint limits and walking"), ("female", "Female", "Female skin, CT donor, joint limits and walking"))


def _body(scene):
    return human.find_body(scene)


def _wrapped(layout, text, icon="NONE", width=38):
    """A label is cut at the panel's edge, so long sentences go on several lines."""
    col = layout.column(align=True)
    for i, line in enumerate(textwrap.wrap(text, width)):
        col.label(text=line, icon=icon if i == 0 else "NONE")


def _redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _settle_now():
    scene = bpy.context.scene
    body = _body(scene) if not human.is_built() else None
    if body is not None:
        _state["readout"] = human.settle(body)
        _refresh_tape(scene, body)
    _redraw()


def _refresh_tape(scene, body):
    values, lines = human.measure_body(body)
    _state["tape"] = values
    if scene.hm_editor.show_tape:
        human.show_tape(lines)


def _pins(scene):
    """The measures typed in by hand, in centimetres."""
    return json.loads(scene.hm_editor.pins_json or "{}")


def _set_pins(scene, pins):
    scene.hm_editor.pins_json = json.dumps(pins)


def _fit(scene, body):
    """Holds every measure typed so far, and says which ones couldn't be reached."""
    pins = _pins(scene)
    by_name = {s.name: s for s in SLIDERS}
    result = human.fit_measures(body, {k: v / 100 for k, v in pins.items()}, by_name)
    labels = {m.key: m.label for m in tape.MEASURES}
    short = [f"{labels[k]} {reached * 100:.1f} (pediu {pins[k]:.1f})" for k, (reached, limit) in result.items() if abs(reached * 100 - pins[k]) > 0.5]
    _state["message"] = "Limite dos faders: " + ", ".join(short) if short else ""
    _refresh_tape(scene, body)


def _settle_timer():
    try:
        _settle_now()
    except Exception as e:
        _state["message"] = f"Couldn't refit: {e}"
    return None


def _changed():
    """Sliders move fast, and refitting eyes and measuring isn't instant, so it waits until the slider stops."""
    _state["unsaved"] = True
    if bpy.app.background:
        return
    if bpy.app.timers.is_registered(_settle_timer):
        bpy.app.timers.unregister(_settle_timer)
    bpy.app.timers.register(_settle_timer, first_interval=SETTLE_DELAY_S)


def _later(action):
    """Replacing the file can't happen inside the operator that asked for it. Headless, there are no timers, so it runs now."""
    def run():
        try:
            action()
        except Exception as e:
            _state["message"] = str(e)
            print("hm_editor:", e)
            _redraw()
        return None
    if bpy.app.background:
        run()
    else:
        bpy.app.timers.register(run, first_interval=0.05)


def _window_override():
    return bpy.context.temp_override(window=bpy.context.window_manager.windows[0])


def _frame_view(body):
    """A front view of the whole body. The body faces -Y."""
    h = _state["readout"]["stature_m"] if _state["readout"] else 1.7
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                space = area.spaces.active
                space.show_region_ui = True
                space.region_3d.view_rotation = (0.7071, 0.7071, 0, 0)
                space.region_3d.view_location = (0, 0, h / 2)
                space.region_3d.view_distance = h * 1.7
                space.region_3d.view_perspective = "PERSP"


def _backup(scene):
    """Replacing a human throws its sliders away, so a copy is kept in case it was by accident."""
    body = _body(scene)
    if body is None or not _state["unsaved"]:
        return None
    path = os.path.join(tempfile.gettempdir(), "hm_editor_last_sliders.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(rc.dumps(_read(scene)))
    return path


def _read(scene):
    e = scene.hm_editor
    r = human.read_recipe(_body(scene), e.character, e.sex, json.loads(e.assets_json) if e.assets_json else None)
    if _pins(scene):
        r["measures_cm"] = _pins(scene)
    return r


def _start(scene, r, recipe_path=""):
    """Makes the human of this recipe in this file, in place of any earlier one."""
    wrong = rc.problems(r)
    if wrong:
        raise ValueError("; ".join(wrong))
    kept = _backup(scene)
    old = _body(scene)
    if old is not None:
        human.remove(old)
    human.remove_default_cube()
    e = scene.hm_editor
    e.character, e.sex_stored, e.recipe_path, e.assets_json = r["name"], r["sex"], recipe_path, json.dumps(r.get("assets", {}))
    e.pins_json = json.dumps(r.get("measures_cm", {}))
    e.body = human.create(r)
    _state["readout"] = human.settle(e.body)
    _refresh_tape(scene, e.body)
    _state["unsaved"] = False
    _state["message"] = f"Earlier sliders kept in {kept}" if kept else ""
    if not bpy.app.background:
        _frame_view(e.body)
    return e.body


@bpy.app.handlers.persistent
def _file_loaded(_):
    """Another file holds another human, so the readout and the unsaved mark don't carry over."""
    _state["readout"], _state["unsaved"], _state["message"], _state["tape"] = None, False, "", None
    if not bpy.app.background and not human.is_built():
        bpy.app.timers.register(_settle_timer, first_interval=0.1)


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _write_recipe(scene, path):
    r = _read(scene)
    wrong = rc.problems(r)
    if wrong:
        raise ValueError("; ".join(wrong))
    with open(path, "w", encoding="utf-8") as f:
        f.write(rc.dumps(r))
    scene.hm_editor.recipe_path = path
    _state["unsaved"] = False
    return r


def _build_timer():
    build = _state["build"]
    if build is None:
        return None
    status = build.poll()
    _redraw()
    if status == "running":
        return 2.0
    _state["build"] = None
    if status == "done":
        _state["built_blend"], _state["failed"] = build.blend, None
    else:
        _state["failed"] = f"{build.error}. Whole log: {build.log_path}"
    _redraw()
    return None


# ---- properties

def _slider_get(pair):
    def get(self):
        body = _body(self.id_data)
        return human.get_side(body, pair) if body is not None else 0.0
    return get


def _slider_prop(s, label, index):
    """A sided slider is one property per side. While Symmetric is on, moving one also moves the other."""
    pair = s.sides[index][1]
    def set_(self, value):
        body = _body(self.id_data)
        if body is None:
            return
        human.set_side(body, pair, value)
        if s.sided and self.id_data.hm_editor.symmetric:
            human.set_side(body, s.sides[1 - index][1], value)
        _changed()
    ends = f"{s.low} to {s.high}. " if s.low else ""
    note = "Skin only: nothing under the skin follows this. " if s.skin_only else ""
    # The hard limit is MPFB's; the slider stops at 0.8 because some targets break beyond it (docs/character-controls.md). Type a value to go further.
    return FloatProperty(name=label, description=f"{ends}{note}MPFB: {s.name}", min=-1.0 if pair[0] else 0.0, max=1.0, soft_min=-0.8 if pair[0] else 0.0, soft_max=0.8, get=_slider_get(pair), set=set_, precision=2)


def _slider_group():
    annotations = {}
    for s in SLIDERS:
        if s.sided:
            annotations[s.key + "_l"] = _slider_prop(s, s.label, 0)
            annotations[s.key + "_r"] = _slider_prop(s, s.label, 1)
        else:
            annotations[s.key] = _slider_prop(s, s.label, 0)
    return type("HM_Sliders", (bpy.types.PropertyGroup,), {"__annotations__": annotations})


def _macro_prop(name, label, lo, hi, text):
    def get(self):
        body = _body(self.id_data)
        return human.get_macro(body, name) if body is not None else 0.5
    def set_(self, value):
        body = _body(self.id_data)
        if body is not None:
            human.set_macro(body, name, value)
            _changed()
    return FloatProperty(name=label, description=text, min=lo, max=hi, get=get, set=set_, precision=2)


def _ancestry_prop(name):
    def get(self):
        body = _body(self.id_data)
        return human.get_macro(body, name) if body is not None else 0.33
    def set_(self, value):
        body = _body(self.id_data)
        if body is not None:
            human.set_ancestry(body, name, value)
            _changed()
    return FloatProperty(name=name.capitalize(), description="MPFB's ancestry blend. The other two scale so the three sum to 1", min=0.0, max=1.0, get=get, set=set_, precision=2)


def _tape_prop(m):
    def get(self):
        return _state["tape"][m.key] * 100 if _state["tape"] else 0.0
    def set_(self, value):
        scene = self.id_data
        body = _body(scene)
        if body is None:
            return
        pins = _pins(scene)
        pins[m.key] = round(value, 1)
        _set_pins(scene, pins)
        _fit(scene, body)
        _changed()
    return FloatProperty(name=m.label, description=f"{m.text}. Digite o valor em centímetros", min=1.0, max=300.0, precision=1, get=get, set=set_)


def _show_tape_set(self, value):
    self["show_tape_stored"] = value
    tape_object = bpy.data.objects.get("HM_tape")
    if value:
        scene, body = self.id_data, _body(self.id_data)
        if body is not None:
            _refresh_tape(scene, body)
    elif tape_object is not None:
        bpy.data.objects.remove(tape_object)


def _sex_get(self):
    return 0 if self.sex_stored == "male" else 1


def _sex_set(self, value):
    self.sex_stored = SEX_ITEMS[value][0]
    body = _body(self.id_data)
    if body is not None:
        human.set_macro(body, "gender", rc.GENDER[self.sex_stored])
        _changed()


def _collection_visible(name):
    def get(self):
        lc = bpy.context.view_layer.layer_collection.children.get(name)
        return lc is not None and not lc.hide_viewport
    def set_(self, value):
        lc = bpy.context.view_layer.layer_collection.children.get(name)
        if lc is not None:
            lc.hide_viewport = not value
    return get, set_


def _skin_view_get(self):
    skin = human.built_skin()
    if skin is None or skin.hide_get():
        return 2
    return 1 if skin.display_type == "WIRE" else 0


def _skin_view_set(self, value):
    skin = human.built_skin()
    if skin is not None:
        skin.hide_set(value == 2)
        skin.display_type = "WIRE" if value == 1 else "TEXTURED"


def _controls():
    return bpy.data.objects.get("HM_controls")


def _push_controls():
    """A changed control reaches its drivers after update_tag and a frame change (blender/breath_check.py)."""
    ctrl = _controls()
    ctrl.update_tag()
    scene = bpy.context.scene
    scene.frame_set(scene.frame_current)


def _muscle_get(name):
    def get(self):
        ctrl = _controls()
        return max(ctrl.get(f"m_{name}_L", 0.0), ctrl.get(f"m_{name}_R", 0.0)) if ctrl else 0.0
    return get


def _muscle_set(name):
    def set_(self, value):
        ctrl = _controls()
        if ctrl is not None:
            ctrl[f"m_{name}_L"] = ctrl[f"m_{name}_R"] = value
            _push_controls()
    return set_


def _muscle_group():
    annotations = {}
    for _, muscles in catalog.FACE_MUSCLES:
        for name, label, text in muscles:
            annotations[name] = FloatProperty(name=label, description=text, min=0.0, max=1.0, get=_muscle_get(name), set=_muscle_set(name), precision=2)
    return type("HM_Muscles", (bpy.types.PropertyGroup,), {"__annotations__": annotations})


def _editor_group():
    annotations = {
        "body": PointerProperty(type=bpy.types.Object, name="Human"),
        "character": StringProperty(name="Name", default="character", description="Names the output folder, its files and the objects in the built file"),
        "sex_stored": StringProperty(default="male", options={"HIDDEN"}),
        "sex": EnumProperty(name="Sex", items=SEX_ITEMS, get=_sex_get, set=_sex_set),
        "recipe_path": StringProperty(name="Recipe", subtype="FILE_PATH", description="The character's file. It belongs in the film root's characters folder, not in a repository"),
        "assets_json": StringProperty(options={"HIDDEN"}),
        "out_root": StringProperty(name="Build folder", subtype="DIR_PATH", default="G:\\mocap-studio-downloads\\models\\hm-build\\", description="Each character gets a folder here. It must be on G:, the drive Docker can see"),
        "symmetric": BoolProperty(name="Symmetric", default=True, description="Left and right sliders move together"),
        "find": StringProperty(name="Find", options={"TEXTEDIT_UPDATE"}, description="Type part of a name, such as jaw or lip"),
        "target_stature": FloatProperty(name="Stature", unit="LENGTH", default=1.75, min=0.5, max=3.0, precision=3, description="The real height to reach, measured on this body"),
        "separate_sides": BoolProperty(name="Left and right apart", description="One slider per side. These are the ones you can keyframe"),
        "pins_json": StringProperty(options={"HIDDEN"}),
        "show_tape": BoolProperty(name="Mostrar as linhas da fita", description="Desenha sobre o corpo onde cada medida é tirada. Não entra na receita", get=lambda self: self.get("show_tape_stored", False), set=_show_tape_set),
        "skin_view": EnumProperty(name="Skin", items=(("SOLID", "Solid", ""), ("WIRE", "Wire", "See through to what's inside"), ("HIDDEN", "Hidden", "")), get=_skin_view_get, set=_skin_view_set),
    }
    for name, label, lo, hi, text in MACROS:
        annotations["macro_" + name] = _macro_prop(name, label, lo, hi, text)
    for name in ("african", "asian", "caucasian"):
        annotations["race_" + name] = _ancestry_prop(name)
    for m in tape.MEASURES:
        annotations["tape_" + m.key] = _tape_prop(m)
    for prop, collection, label in (("show_bones", "HM_bones", "Bones"), ("show_muscles", "HM_muscles", "Muscles"), ("show_targets", "HM_muscle_targets", "Attachments")):
        get, set_ = _collection_visible(collection)
        annotations[prop] = BoolProperty(name=label, get=get, set=set_)
    return type("HM_Editor", (bpy.types.PropertyGroup,), {"__annotations__": annotations})


# ---- operators

class HM_OT_new(bpy.types.Operator):
    bl_idname = "hm_editor.new"
    bl_label = "New human"
    bl_description = "A neutral human of this sex"
    bl_options = {"REGISTER"}
    sex: EnumProperty(items=SEX_ITEMS)

    def invoke(self, context, event):
        if _body(context.scene) is not None:
            return context.window_manager.invoke_confirm(self, event, title="Replace this human?", message="The current human's sliders go away, unless they're saved in a recipe", confirm_text="Replace")
        return self.execute(context)

    def execute(self, context):
        try:
            _start(context.scene, rc.new(self.sex, self.sex))
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class HM_OT_open_recipe(bpy.types.Operator):
    bl_idname = "hm_editor.open_recipe"
    bl_label = "Open recipe"
    bl_description = "Load a recipe's sliders, in place of the current human"
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            _start(context.scene, _read_json(self.filepath), self.filepath)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class HM_OT_save_recipe(bpy.types.Operator):
    bl_idname = "hm_editor.save_recipe"
    bl_label = "Save recipe"
    bl_description = "Write the sliders to the character's file"
    filepath: StringProperty(subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.json", options={"HIDDEN"})
    choose: BoolProperty(options={"HIDDEN", "SKIP_SAVE"})

    def invoke(self, context, event):
        e = context.scene.hm_editor
        if e.recipe_path and not self.choose:
            self.filepath = bpy.path.abspath(e.recipe_path)
            return self.execute(context)
        self.filepath = bpy.path.abspath(e.recipe_path) or rc.safe_name(e.character) + ".json"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        path = bpy.path.ensure_ext(self.filepath, ".json")
        try:
            _write_recipe(context.scene, path)
        except Exception as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        self.report({"INFO"}, f"Saved {path}")
        return {"FINISHED"}


class HM_OT_set_stature(bpy.types.Operator):
    bl_idname = "hm_editor.set_stature"
    bl_label = "Set"
    bl_description = "Move the height slider until this body measures that stature"

    def execute(self, context):
        e = context.scene.hm_editor
        try:
            human.set_stature(_body(context.scene), e.target_stature)
        except ValueError as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}
        _changed()
        return {"FINISHED"}


class HM_OT_refit(bpy.types.Operator):
    bl_idname = "hm_editor.refit"
    bl_label = "Reaplicar medidas"
    bl_description = "Volta às medidas digitadas, depois de mexer em outros faders"

    def execute(self, context):
        _fit(context.scene, _body(context.scene))
        _changed()
        return {"FINISHED"}


class HM_OT_unpin(bpy.types.Operator):
    bl_idname = "hm_editor.unpin"
    bl_label = "Soltar"
    bl_description = "Esta medida deixa de ser mantida. O corpo não muda"
    key: StringProperty()

    def execute(self, context):
        pins = _pins(context.scene)
        pins.pop(self.key, None)
        _set_pins(context.scene, pins)
        return {"FINISHED"}


class HM_OT_reset_slider(bpy.types.Operator):
    bl_idname = "hm_editor.reset_slider"
    bl_label = "Reset"
    bl_description = "Back to zero. Empty means every slider"
    name: StringProperty()

    def execute(self, context):
        body = _body(context.scene)
        for s in SLIDERS:
            if not self.name or s.name == self.name:
                for _, pair in s.sides:
                    if human.get_side(body, pair) != 0:
                        human.set_side(body, pair, 0.0)
        _changed()
        return {"FINISHED"}


class HM_OT_build(bpy.types.Operator):
    bl_idname = "hm_editor.build"
    bl_label = "Build full model"
    bl_description = "Save the recipe and rebuild skin, rig, bones, muscles and fields, about 4.5 minutes. You can keep working here"

    @classmethod
    def poll(cls, context):
        return _state["build"] is None and bool(context.scene.hm_editor.recipe_path)

    def _blend(self, context):
        e = context.scene.hm_editor
        name = rc.safe_name(e.character)
        return os.path.join(bpy.path.abspath(e.out_root), name, name + ".blend")

    def invoke(self, context, event):
        if os.path.exists(self._blend(context)):
            name = rc.safe_name(context.scene.hm_editor.character)
            return context.window_manager.invoke_confirm(self, event, title=f"Replace the built {name}?", message="A model with this name is already built. Rename the character to keep it", confirm_text="Replace")
        return self.execute(context)

    def execute(self, context):
        e = context.scene.hm_editor
        path = bpy.path.abspath(e.recipe_path)
        try:
            r = _write_recipe(context.scene, path)
            _state["build"] = builder.Build(path, bpy.path.abspath(e.out_root), r["name"])
        except Exception as err:
            self.report({"ERROR"}, str(err))
            return {"CANCELLED"}
        _state["failed"] = _state["built_blend"] = None
        bpy.app.timers.register(_build_timer, first_interval=2.0, persistent=True)
        return {"FINISHED"}


class HM_OT_open_built(bpy.types.Operator):
    bl_idname = "hm_editor.open_built"
    bl_label = "Open built model"
    bl_description = "Open the model this build made"

    def invoke(self, context, event):
        if bpy.data.is_dirty:
            return context.window_manager.invoke_confirm(self, event, title="Open the built model?", message="Unsaved changes in this Blender file go away. The recipe is already saved", confirm_text="Open")
        return self.execute(context)

    def execute(self, context):
        path = _state["built_blend"]
        def action():
            with _window_override():
                bpy.ops.wm.open_mainfile(filepath=path, load_ui=False)
        _later(action)
        return {"FINISHED"}


class HM_OT_change_character(bpy.types.Operator):
    bl_idname = "hm_editor.change_character"
    bl_label = "Change this character"
    bl_description = "Read this model's sliders into a plain human you can edit. The built file stays as it is on disk"

    def invoke(self, context, event):
        if bpy.data.is_dirty:
            return context.window_manager.invoke_confirm(self, event, title="Change this character?", message="Unsaved changes in this file, such as a pose, go away", confirm_text="Continue")
        return self.execute(context)

    def execute(self, context):
        skin = human.built_skin()
        r = human.read_recipe(skin, skin.name.removesuffix(".skin"), bpy.data.objects["HM_rig"].get("hm_sex", "male"))
        def action():
            with _window_override():
                bpy.ops.wm.read_homefile(use_empty=True, load_ui=False)
            # MPFB reads bpy.context.object, which a timer's context only has inside a window
            with _window_override():
                _start(bpy.context.scene, r)
        _later(action)
        return {"FINISHED"}


class HM_OT_reset_controls(bpy.types.Operator):
    bl_idname = "hm_editor.reset_controls"
    bl_label = "Reset face"
    bl_description = "Jaw, breath, tongue and face muscles back to zero. A keyed control returns to its keys when the frame changes"

    def execute(self, context):
        ctrl = _controls()
        for k in ctrl.keys():
            if isinstance(ctrl[k], float):
                ctrl[k] = 0.0
        _push_controls()
        return {"FINISHED"}


class HM_OT_pose_mode(bpy.types.Operator):
    bl_idname = "hm_editor.pose_mode"
    bl_label = "Pose the body"
    bl_description = "Select the rig and enter Pose Mode, to rotate the joints by hand"

    def execute(self, context):
        rig = bpy.data.objects["HM_rig"]
        if context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        rig.hide_set(False)
        bpy.ops.object.select_all(action="DESELECT")
        rig.select_set(True)
        context.view_layer.objects.active = rig
        bpy.ops.object.mode_set(mode="POSE")
        return {"FINISHED"}


class HM_OT_reset_pose(bpy.types.Operator):
    bl_idname = "hm_editor.reset_pose"
    bl_label = "Reset pose"
    bl_description = "Every joint back to the rest pose. Jaw and breath come from their controls, and stay"

    def execute(self, context):
        for pb in bpy.data.objects["HM_rig"].pose.bones:
            pb.location = (0, 0, 0)
            pb.rotation_quaternion = (1, 0, 0, 0)
            pb.rotation_euler = (0, 0, 0)
            pb.scale = (1, 1, 1)
        _push_controls()
        return {"FINISHED"}


# ---- panels

class _Panel:
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Human"


def _design_ready(context):
    return not human.is_built() and context.mode == "OBJECT" and _body(context.scene) is not None


def _draw_slider(layout, scene, s):
    sliders, editor = scene.hm_sliders, scene.hm_editor
    label = s.label + (" •" if s.skin_only else "")
    if not s.sided:
        layout.prop(sliders, s.key, text=label, slider=True)
    elif editor.symmetric:
        layout.prop(sliders, s.key + "_l", text=label, slider=True)
    else:
        col = layout.column(align=True)
        col.prop(sliders, s.key + "_l", text=f"{label}, left", slider=True)
        col.prop(sliders, s.key + "_r", text=f"{label}, right", slider=True)


class HM_PT_main(_Panel, bpy.types.Panel):
    bl_idname = "HM_PT_main"
    bl_label = "Human"

    def draw(self, context):
        layout = self.layout
        if not SLIDERS:
            layout.label(text="MPFB wasn't found", icon="ERROR")
            layout.label(text="Install MPFB 2.0.18: see DEPENDENCIES.md")
            return
        if human.is_built():
            self._built(layout, context)
        else:
            self._design(layout, context)
        if _state["message"]:
            _wrapped(layout, _state["message"], "INFO")

    def _built(self, layout, context):
        skin = human.built_skin()
        box = layout.box()
        box.label(text=f"Built model: {skin.name.removesuffix('.skin') if skin else '?'}", icon="ARMATURE_DATA")
        _wrapped(box, "Body and face shape are baked here. To change them, go back to the sliders, then build again:")
        box.operator("hm_editor.change_character", icon="MODIFIER")

    def _design(self, layout, context):
        scene = context.scene
        e = scene.hm_editor
        body = _body(scene)
        if body is None:
            layout.label(text="Start a character:")
            row = layout.row(align=True)
            row.operator("hm_editor.new", text="New male").sex = "male"
            row.operator("hm_editor.new", text="New female").sex = "female"
            layout.operator("hm_editor.open_recipe", icon="FILE_FOLDER")
            layout.label(text="Or open a built model: File > Open")
            return
        if context.mode != "OBJECT":
            layout.label(text="Return to Object Mode to use the sliders", icon="ERROR")
        col = layout.column(align=True)
        col.prop(e, "character")
        col.row(align=True).prop(e, "sex", expand=True)
        readout = _state["readout"]
        box = layout.box()
        if readout:
            box.label(text=f"{readout['stature_m']:.2f} m, about {readout['mass_kg']:.0f} kg, BMI {readout['bmi']:.1f}")
        row = box.row(align=True)
        row.prop(e, "target_stature")
        row.operator("hm_editor.set_stature")
        box = layout.box()
        box.label(text="1. Character file", icon="FILE_TICK")
        if e.recipe_path:
            box.label(text=os.path.basename(bpy.path.abspath(e.recipe_path)) + (" (not saved)" if _state["unsaved"] else ""))
        row = box.row(align=True)
        row.operator("hm_editor.save_recipe", text="Save" if e.recipe_path else "Save as...")
        save_as = row.operator("hm_editor.save_recipe", text="Save as...") if e.recipe_path else None
        if save_as:
            save_as.choose = True
        row.operator("hm_editor.open_recipe", text="Open...")
        row = box.row(align=True)
        row.operator("hm_editor.new", text="New male").sex = "male"
        row.operator("hm_editor.new", text="New female").sex = "female"
        box = layout.box()
        box.label(text="2. Full model", icon="ARMATURE_DATA")
        box.prop(e, "out_root", text="")
        build = _state["build"]
        if build:
            box.label(text=f"Building {build.name}: {build.describe()}", icon="SORTTIME")
        else:
            box.operator("hm_editor.build", icon="PLAY")
            if not e.recipe_path:
                box.label(text="Save the recipe first")
        if _state["failed"]:
            _wrapped(box, f"The build failed: {_state['failed']}", "ERROR")
        if _state["built_blend"]:
            box.label(text="Built", icon="CHECKMARK")
            box.operator("hm_editor.open_built", icon="FILE_BLEND")


class HM_PT_find(_Panel, bpy.types.Panel):
    bl_idname = "HM_PT_find"
    bl_label = "Find a slider"
    bl_parent_id = "HM_PT_main"

    @classmethod
    def poll(cls, context):
        return _design_ready(context)

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        e = scene.hm_editor
        row = layout.row()
        row.prop(e, "find", text="", icon="VIEWZOOM")
        row.prop(e, "symmetric")
        found = catalog.search(SLIDERS, e.find)
        regions = {r[0]: r[1] for r in catalog.REGIONS}
        region = None
        for s in found[:30]:
            if s.region != region:
                region = s.region
                layout.label(text=regions[region])  # "Height" alone doesn't say of what
            _draw_slider(layout, scene, s)
        if len(found) > 30:
            layout.label(text=f"{len(found) - 30} more: type more of the name")
        _wrapped(layout, "• = skin only: nothing under it follows")


class HM_PT_tape(_Panel, bpy.types.Panel):
    bl_idname = "HM_PT_tape"
    bl_label = "Medidas de modelagem (cm)"
    bl_parent_id = "HM_PT_main"

    @classmethod
    def poll(cls, context):
        return _design_ready(context)

    def draw(self, context):
        scene = context.scene
        e = scene.hm_editor
        layout = self.layout
        layout.prop(e, "show_tape")
        if not _state["tape"]:
            layout.label(text="Mexa em um fader para medir")
            return
        pins = _pins(scene)
        col = layout.column(align=True)
        for m in tape.MEASURES:
            row = col.row(align=True)
            value = _state["tape"][m.key] * 100
            if m.key in tape.DRIVERS or m.key == "height":
                row.alert = m.key in pins and abs(value - pins[m.key]) > 0.5
                row.prop(e, "tape_" + m.key)
                if m.key in pins:
                    row.operator("hm_editor.unpin", text="", icon="PINNED").key = m.key
            else:
                row.label(text=f"{m.label}: {value:.1f}")
        if pins:
            layout.operator("hm_editor.refit")
        _wrapped(layout, "Digite um valor: os faders se ajustam e o valor fica mantido. Altura da cava e Ombro são só leitura: nenhum fader os move diretamente")


class HM_PT_changed(_Panel, bpy.types.Panel):
    bl_idname = "HM_PT_changed"
    bl_label = "What I changed"
    bl_parent_id = "HM_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return _design_ready(context)

    def draw(self, context):
        scene = context.scene
        layout = self.layout
        body = _body(scene)
        changed = [s for s in SLIDERS if any(human.get_side(body, p) != 0 for _, p in s.sides)]
        if not changed:
            layout.label(text="No sliders moved")
            return
        for s in changed:
            row = layout.row(align=True)
            _draw_slider(row, scene, s)
            row.operator("hm_editor.reset_slider", text="", icon="X").name = s.name
        layout.operator("hm_editor.reset_slider", text="Reset every slider").name = ""


class HM_PT_whole_body(_Panel, bpy.types.Panel):
    bl_idname = "HM_PT_whole_body"
    bl_label = "Whole body"
    bl_parent_id = "HM_PT_main"

    @classmethod
    def poll(cls, context):
        return _design_ready(context)

    def draw(self, context):
        e = context.scene.hm_editor
        col = self.layout.column(align=True)
        for name, *_ in MACROS:
            col.prop(e, "macro_" + name, slider=True)
        col = self.layout.column(align=True)
        col.label(text="Ancestry")
        for name in ("african", "asian", "caucasian"):
            col.prop(e, "race_" + name, slider=True)
        _wrapped(self.layout, "• = skin only: nothing under it follows")


NOTES = {"mouth": "A smile can tear at the corners on a changed face (bug 7)", "hip": "The pelvis bone grows with the hips, even if they're meant as fat", "asym": "A millimetre or two per slider"}


def _region_panel(region, label, group):
    def draw(self, context):
        scene = context.scene
        layout = self.layout
        layout.prop(scene.hm_editor, "symmetric")
        if region in NOTES:
            _wrapped(layout, NOTES[region], "INFO")
        members = [s for s in SLIDERS if s.region == region]
        col = layout.column(align=True)
        for s in members:
            _draw_slider(col, scene, s)
        if any(s.skin_only for s in members):
            _wrapped(layout, "• = skin only: nothing under it follows")
    return type(f"HM_PT_region_{region}", (_Panel, bpy.types.Panel), {
        "bl_idname": f"HM_PT_region_{region}", "bl_label": f"{'Body' if group == 'body' else 'Face'}: {label}", "bl_parent_id": "HM_PT_main", "bl_options": {"DEFAULT_CLOSED"},
        "poll": classmethod(lambda cls, context: _design_ready(context)), "draw": draw})


class HM_PT_layers(_Panel, bpy.types.Panel):
    bl_idname = "HM_PT_layers"
    bl_label = "Layers"
    bl_parent_id = "HM_PT_main"

    @classmethod
    def poll(cls, context):
        return human.is_built()

    def draw(self, context):
        e = context.scene.hm_editor
        self.layout.row(align=True).prop(e, "skin_view", expand=True)
        row = self.layout.row(align=True)
        row.prop(e, "show_bones", toggle=True)
        row.prop(e, "show_muscles", toggle=True)
        row.prop(e, "show_targets", toggle=True)
        _wrapped(self.layout, "These change this view, not renders")


class HM_PT_face_controls(_Panel, bpy.types.Panel):
    bl_idname = "HM_PT_face_controls"
    bl_label = "Jaw, breath and tongue"
    bl_parent_id = "HM_PT_main"

    @classmethod
    def poll(cls, context):
        return human.is_built()

    def draw(self, context):
        ctrl = _controls()
        col = self.layout.column(align=True)
        for key, label in (("jaw_open", "Jaw open"), ("breath", "Breath"), ("tongue_tip_raise", "Tongue tip"), ("tongue_body_raise", "Tongue body"), ("tongue_back_raise", "Tongue back"), ("tongue_protrude", "Tongue out")):
            if key in ctrl:
                col.prop(ctrl, f'["{key}"]', text=label, slider=True)
        self.layout.operator("hm_editor.reset_controls")
        self.layout.label(text="Hover a slider and press I to keyframe it")


class HM_PT_face_muscles(_Panel, bpy.types.Panel):
    bl_idname = "HM_PT_face_muscles"
    bl_label = "Face muscles"
    bl_parent_id = "HM_PT_main"

    @classmethod
    def poll(cls, context):
        ctrl = _controls()
        return ctrl is not None and "m_zygomaticus_major_L" in ctrl

    def draw(self, context):
        scene = context.scene
        e, ctrl = scene.hm_editor, _controls()
        layout = self.layout
        layout.prop(e, "separate_sides")
        for group, muscles in catalog.FACE_MUSCLES:
            layout.label(text=group)
            col = layout.column(align=True)
            for name, label, _ in muscles:
                if f"m_{name}_L" not in ctrl:
                    continue
                if e.separate_sides:
                    row = col.row(align=True)
                    row.prop(ctrl, f'["m_{name}_L"]', text=f"{label}, L", slider=True)
                    row.prop(ctrl, f'["m_{name}_R"]', text="R", slider=True)
                else:
                    col.prop(scene.hm_muscles, name, slider=True)


class HM_PT_pose(_Panel, bpy.types.Panel):
    bl_idname = "HM_PT_pose"
    bl_label = "Pose"
    bl_parent_id = "HM_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return human.is_built()

    def draw(self, context):
        row = self.layout.row(align=True)
        row.operator("hm_editor.pose_mode", icon="POSE_HLT")
        row.operator("hm_editor.reset_pose")
        self.layout.label(text="Joint limits aren't enforced yet (bug 3)")


OPERATORS = (HM_OT_new, HM_OT_open_recipe, HM_OT_save_recipe, HM_OT_set_stature, HM_OT_refit, HM_OT_unpin, HM_OT_reset_slider, HM_OT_build, HM_OT_open_built, HM_OT_change_character, HM_OT_reset_controls, HM_OT_pose_mode, HM_OT_reset_pose)
_registered = []


def _target_json():
    """MPFB sits beside this add-on in the same extension folder. It isn't imported here: it may not be enabled yet."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mpfb", "data", "targets", "target.json")
    if not os.path.exists(path):
        return None
    return _read_json(path)


def register():
    data = _target_json()
    SLIDERS[:] = catalog.sliders(data) if data else []
    groups = [_slider_group(), _muscle_group(), _editor_group()]
    panels = [HM_PT_main, HM_PT_tape, HM_PT_find, HM_PT_changed, HM_PT_whole_body, *[_region_panel(*r) for r in catalog.REGIONS], HM_PT_layers, HM_PT_face_controls, HM_PT_face_muscles, HM_PT_pose]
    _registered[:] = [*groups, *OPERATORS, *panels]
    for c in _registered:
        bpy.utils.register_class(c)
    bpy.types.Scene.hm_sliders = PointerProperty(type=groups[0])
    bpy.types.Scene.hm_muscles = PointerProperty(type=groups[1])
    bpy.types.Scene.hm_editor = PointerProperty(type=groups[2])
    bpy.app.handlers.load_post.append(_file_loaded)


def unregister():
    bpy.app.handlers.load_post.remove(_file_loaded)
    for timer in (_build_timer, _settle_timer):
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)
    del bpy.types.Scene.hm_editor, bpy.types.Scene.hm_muscles, bpy.types.Scene.hm_sliders
    for c in reversed(_registered):
        bpy.utils.unregister_class(c)
    _registered.clear()

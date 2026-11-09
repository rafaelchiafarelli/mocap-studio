"""The character sheet panel in Blender: silhouette, biotype with its two other parts, height, body fat, the pattern-making distances, shapes and cup, each field of the resolved sheet shown with where it came from; saving the character file (initiative body-type-selection).
Portuguese labels: the trade's terms. Uses hmcore's character module from this add-on's repository."""
import datetime, json, os, subprocess, tempfile, time
import bpy
import numpy as np
from bpy.props import BoolProperty, EnumProperty, FloatProperty, PointerProperty, StringProperty
from . import builder, catalog, human, sheet, tape

N_BODY = tape.N_BODY
PREVIEW_KEY = "HM_breast"
PREVIEW_DELAY_S = 0.15
REVIEW = r"G:\mocap-studio-downloads\review"
BUST_STEPS = 8  # bisection steps for the projection that reads the sheet's bust on the tape


_cache = {"module": None, "resolved": {}, "breast": None, "tris": None, "message": "", "run": None}


def _module():
    if _cache["module"] is None:  # it is read through WSL's network path, too slow for every redraw
        _cache["module"] = sheet.character_module(builder.config())
    return _cache["module"]


def _breast_module():
    if _cache["breast"] is None:
        _cache["breast"] = sheet.repo_module(builder.config(), "breast_skin")
    return _cache["breast"]


def _stage(context):
    """The stage the panels show: sheet.current_stage, from the scene and the run in progress."""
    run = _cache["run"]
    return sheet.current_stage(context.scene.hm_character.stage, human.is_built(), run is not None and not run.get("finished"))


def _review_copy(character, name, stamp, tag=""):
    """A copy of this character in today's review folder, kept with its own name. Returns its path."""
    folder = os.path.join(REVIEW, datetime.date.today().isoformat(), "fichas")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, f"{name}_{stamp}{tag}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(character, f, indent=1, ensure_ascii=False)
    return path


def _redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


def _triangles(body):
    if _cache["tris"] is None:
        faces = [p.vertices[:] for p in body.data.polygons if max(p.vertices) < N_BODY]
        _cache["tris"] = np.array([(f[0], f[i], f[i + 1]) for f in faces for i in range(1, len(f) - 1)])
    return _cache["tris"]


def _breast_table():
    with open(sheet.repo_path(builder.config(), "human-model", "data", "breast_shapes.json"), encoding="utf-8") as f:
        return json.load(f)


def preview(context):
    """The breast faders on the human in the scene, on a shape key: the same outline the build uses. Reports the bust the tape reads."""
    scene, p = context.scene, context.scene.hm_character
    body = human.find_body(scene)
    if body is None or p.sex != "female" or human.is_built():
        return
    m, bs = _module(), _breast_module()
    character = sheet.character_from_values(values(p))
    if m.problems(character):
        return
    keys = body.data.shape_keys.key_blocks
    key = keys.get(PREVIEW_KEY) or body.shape_key_add(name=PREVIEW_KEY, from_mix=False)
    key.value = 0.0
    verts = human.all_verts(body)
    skin = verts[:N_BODY]
    nipple = np.array([v.index for v in body.data.vertices if v.index < N_BODY and any(g.group == body.vertex_groups["nippleTip"].index for g in v.groups)])
    apexes = {1: skin[nipple[skin[nipple, 0] > 0]].mean(axis=0), -1: skin[nipple[skin[nipple, 0] < 0]].mean(axis=0)}
    table, fields, base, wish = _breast_table(), _resolved(character)["fields"], m.base_measures("female"), character.get("breast") or {}
    difference, neutral = fields["bust"]["value"] - fields["underbust"]["value"], base["bust"] - base["underbust"]
    tris = _triangles(body)
    topology = human._topology[0] if human._topology else None
    if topology is None:
        human.measure_body(body)
        topology = human._topology[0]
    z = float((apexes[1][2] + apexes[-1][2]) / 2)
    girth = lambda v: tape.length_of(tape._girth_loop(topology, v, z)) * 100

    def inflated(factor):
        return bs.inflate(skin, tris, [bs.params(apexes[s], s, difference, neutral, wish, table, factor) for s in (1, -1)])

    factor = 1.0
    if not wish.get("projection_cm"):
        low, high = 0.3, 3.0
        for _ in range(BUST_STEPS):
            factor = (low + high) / 2
            low, high = (factor, high) if girth(inflated(factor)) < fields["bust"]["value"] else (low, factor)
    out = inflated(factor)
    basis = np.empty(len(body.data.vertices) * 3)
    keys[0].data.foreach_get("co", basis)
    basis = basis.reshape(-1, 3)
    basis[:N_BODY] += out - skin
    key.data.foreach_set("co", basis.ravel())
    key.value = 1.0
    body.data.update()
    _cache["message"] = f"Busto na fita: {girth(out):.1f} cm (pedido {fields['bust']['value']:.1f})"
    _redraw()


def _preview_timer():
    try:
        preview(bpy.context)
    except Exception as e:  # a bad value mid-drag mustn't break the panel
        _cache["message"] = f"Prévia falhou: {e}"
    return None


def _changed(self, context):
    if bpy.app.background:
        return
    if bpy.app.timers.is_registered(_preview_timer):
        bpy.app.timers.unregister(_preview_timer)
    bpy.app.timers.register(_preview_timer, first_interval=PREVIEW_DELAY_S)


def make_human(context):
    """The character's human in the scene: a neutral body moved to the sheet's measures by the editor's sliders, as the build's first stage does."""
    scene, p = context.scene, context.scene.hm_character
    m, character = _module(), sheet.character_from_values(values(p))
    wrong = m.problems(character)
    if wrong:
        raise ValueError("; ".join(wrong))
    old = human.find_body(scene)
    if old is not None:
        human.remove(old)
    human.remove_default_cube()
    with open(sheet.repo_path(builder.config(), "human-model", "data", "recipes", f"{p.sex}.json"), encoding="utf-8") as f:
        recipe = json.load(f)
    recipe["name"] = p.name or p.sex
    body = human.create(recipe)
    scene.hm_editor.body = body
    human.settle(body)
    target_json = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(human.__file__))), "mpfb", "data", "targets", "target.json")
    with open(target_json, encoding="utf-8") as f:
        by_name = {s.name: s for s in catalog.sliders(json.load(f))}
    fields = _resolved(character)["fields"]
    asked = {k: v["value"] / 100 for k, v in fields.items() if k in tape.MEASURE_KEYS and (k in tape.DRIVERS or k == "height") and v["source"] != "current"}
    if asked:
        human.fit_measures(body, asked, by_name)
    human.settle(body)
    return body


def _run_timer():
    run = _cache["run"]
    if run is None:
        return None
    try:
        with open(run["json"], encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        if run["process"].poll() is not None:  # it ended before writing run.json: don't stay in "generating" for ever
            run["finished"] = True
            _cache["message"] = "A geração terminou sem resultado: veja o log na pasta temporária do Windows"
            _redraw()
            return None
        return 3.0
    _cache["message"] = sheet.stage_line(state)
    _redraw()
    if state.get("status") in ("done", "failed") and run["process"].poll() is not None:
        run["finished"] = True
        return None
    return 5.0


def _resolved(character):
    key = json.dumps(character, sort_keys=True)
    if key not in _cache["resolved"]:
        _cache["resolved"] = {key: _module().resolve(character)}
    return _cache["resolved"][key]


def _ratios():
    return _module().silhouette_ratios()


def _silhouettes(self, context):
    sex = context.scene.hm_character.sex
    try:
        return [("NONE", "(nenhuma)", "")] + [(k, k.replace("_", " ").capitalize(), "") for k in _ratios()[sex]]
    except OSError:
        return [("NONE", "(sem repositório)", "")]


def sheet_safe(text):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in text)


def values(p):
    return {"sex": p.sex, "name": p.name, "silhouette": p.silhouette, "height_cm": p.height_cm, "body_fat_percent": p.body_fat, "underbust_cm": p.underbust, "bust_cm": p.bust, "cup": p.cup,
            "biotype": p.biotype, "others": {k: getattr(p, f"other_{k}") for k, _ in sheet.BIOTYPE_LABELS if k != p.biotype},
            "distances": {k: getattr(p, f"d_{k}") for k, _ in sheet.DISTANCE_LABELS}, "gluteus": p.gluteus, "breast": p.breast, "espacados": p.espacados, "pendentes": p.pendentes, "assimetrico_R": p.assimetrico_R,
            "projection_cm": p.b_projection, "base_cm": p.b_base, "upper": p.b_upper, "lower": p.b_lower, "power": p.b_power,
            "bone_parameters": {"pelvis_width_cm": p.pelvis_width, "thigh_share_of_leg": p.thigh_share, "humerus_share_of_arm": p.humerus_share}}


def _fader(name, lo, hi, default=0.0):
    return FloatProperty(name=name, min=lo, max=hi, default=default, update=_changed)


def _group():
    props = {
        "stage": EnumProperty(name="Etapa", items=(("choices", "Escolhas", ""), ("fine", "Ajustes finos", "")), default="choices"),
        "legacy": BoolProperty(name="Modo antigo (faders soltos)", default=False, description="Mostra os faders do MPFB e o caminho antigo. O botão Gerar da ficha não lê esses faders"),
        "b_projection": _fader("Projeção cm", 0, 25), "b_base": _fader("Base cm", 0, 20), "b_upper": _fader("Alcance acima", 0, 2), "b_lower": _fader("Alcance abaixo", 0, 2), "b_power": _fader("Concentração", 0, 5),
        "sex": EnumProperty(name="Sexo", items=(("female", "Feminino", ""), ("male", "Masculino", "")), default="female"),
        "name": StringProperty(name="Nome", default=""),
        "silhouette": EnumProperty(name="Silhueta", items=_silhouettes),
        "biotype": EnumProperty(name="Biotipo", items=(("NONE", "(nenhum)", ""), *[(k, v, "") for k, v in sheet.BIOTYPE_LABELS])),
        "height_cm": FloatProperty(name="Altura (cm)", min=0, max=230), "body_fat": FloatProperty(name="Gordura %", min=0, max=60),
        "underbust": _fader("Sub-busto (cm)", 0, 170), "bust": _fader("Busto (cm)", 0, 170),
        "cup": EnumProperty(name="Copa", items=[("NONE", "(calculada)", "")] + [(c, c, "") for c in "ABCDEFGH"], update=_changed),
        "gluteus": EnumProperty(name="Glúteo", items=(("NONE", "(nenhuma)", ""), ("quadrado", "Quadrado", ""), ("redondo", "Redondo", ""), ("coracao", "Coração", ""), ("em_v", "Em V", ""))),
        "breast": EnumProperty(name="Seio", items=(("NONE", "(nenhuma)", ""), ("redondos", "Redondos", ""), ("gota", "Gota", ""), ("conicos", "Cônicos", ""), ("tuberosos", "Tuberosos", "")), update=_changed),
        "espacados": _fader("Espaçados", 0, 1), "pendentes": _fader("Pendentes", 0, 1), "assimetrico_R": _fader("Assimetria (direito)", 0, 1.5),
        "pelvis_width": FloatProperty(name="Largura da pelve (cm)", min=0, max=50), "thigh_share": FloatProperty(name="Fêmur na perna", min=0, max=0.9), "humerus_share": FloatProperty(name="Úmero no braço", min=0, max=0.9),
    }
    for k, label in sheet.BIOTYPE_LABELS:
        props[f"other_{k}"] = FloatProperty(name=label, min=0, max=0.35)
    for k, label in sheet.DISTANCE_LABELS:
        props[f"d_{k}"] = FloatProperty(name=label, min=0, max=200)
    return type("HM_CharacterProps", (bpy.types.PropertyGroup,), {"__annotations__": props})


class HM_OT_save_character(bpy.types.Operator):
    bl_idname = "hm_editor.save_character"
    bl_label = "Salvar personagem"
    filepath: StringProperty(subtype="FILE_PATH")

    def invoke(self, context, event):
        self.filepath = f"{context.scene.hm_character.name or 'personagem'}.json"
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        c = sheet.character_from_values(values(context.scene.hm_character))
        wrong = _module().problems(c)
        if wrong:
            self.report({"ERROR"}, "; ".join(wrong))
            return {"CANCELLED"}
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(c, f, indent=1, ensure_ascii=False)
        _cache["saved"] = self.filepath
        self.report({"INFO"}, f"Salvo em {self.filepath}")
        return {"FINISHED"}


class HM_OT_close_choices(bpy.types.Operator):
    bl_idname = "hm_editor.close_choices"
    bl_label = "Fechar escolhas"
    bl_description = "Confere a ficha, cria o corpo na cena, guarda uma cópia com nome e abre os ajustes finos"

    @classmethod
    def poll(cls, context):
        return _stage(context) == "choices"

    def execute(self, context):
        p = context.scene.hm_character
        try:
            make_human(context)
            preview(context)
            _review_copy(sheet.character_from_values(values(p)), sheet_safe(p.name or p.sex), time.strftime("%H%M%S"), "_fechada")
        except (ValueError, OSError) as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        p.stage = sheet.next_stage(p.stage, "close")
        return {"FINISHED"}


class HM_OT_reopen_choices(bpy.types.Operator):
    bl_idname = "hm_editor.reopen_choices"
    bl_label = "Reabrir escolhas"
    bl_description = "Volta às escolhas. Os ajustes finos ficam, e têm prioridade sobre as formas"

    @classmethod
    def poll(cls, context):
        return _stage(context) == "fine"

    def execute(self, context):
        p = context.scene.hm_character
        p.stage = sheet.next_stage(p.stage, "reopen")
        return {"FINISHED"}


class HM_OT_reset_fine(bpy.types.Operator):
    bl_idname = "hm_editor.reset_fine"
    bl_label = "Zerar ajustes finos"
    bl_description = "Zera os faders do seio, a mistura de biotipos e os parâmetros dos ossos"

    def execute(self, context):
        p = context.scene.hm_character
        for k in sheet.FINE_FIELDS:
            setattr(p, k, 0.0)
        return {"FINISHED"}


class HM_OT_make_human(bpy.types.Operator):
    bl_idname = "hm_editor.make_character_human"
    bl_label = "Atualizar o corpo na cena"
    bl_description = "Refaz o corpo com as medidas da ficha; os faders do seio mudam esse corpo ao vivo"

    @classmethod
    def poll(cls, context):
        return _stage(context) == "fine"

    def execute(self, context):
        try:
            make_human(context)
            preview(context)
        except (ValueError, OSError) as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}
        return {"FINISHED"}


class HM_OT_generate(bpy.types.Operator):
    bl_idname = "hm_editor.generate_character"
    bl_label = "Gerar o corpo completo"
    bl_description = "Roda fast_review.py: ossos, músculos, gordura, caminhada e o arquivo. Leva cerca de 10 minutos e o Blender continua livre"

    @classmethod
    def poll(cls, context):
        return _stage(context) == "fine"

    def execute(self, context):
        p = context.scene.hm_character
        character = sheet.character_from_values(values(p))
        wrong = _module().problems(character)
        if wrong:
            self.report({"ERROR"}, "; ".join(wrong))
            return {"CANCELLED"}
        cfg, day = builder.config(), datetime.date.today().isoformat()
        stamp = time.strftime("%H%M%S")
        name = sheet_safe(p.name or p.sex)
        path = _review_copy(character, name, stamp)
        nickname = f"ficha_{name}_{stamp}"
        log = open(os.path.join(tempfile.gettempdir(), f"{nickname}.log"), "w", encoding="utf-8")
        process = subprocess.Popen(["wsl.exe", "-d", cfg["distro"], "--cd", cfg["repo"], "-e", "python3", "human-model/fast_review.py", nickname, "--body", p.sex, "--character", f"{p.sex}={builder.wsl_path(path, cfg)}"],
                                   stdout=log, stderr=subprocess.STDOUT, creationflags=builder.NO_WINDOW)
        run_dir = os.path.join(REVIEW, day, "fast_review", nickname, p.sex)
        _cache["run"] = {"json": os.path.join(run_dir, "run.json"), "blend": os.path.join(run_dir, "body_walk.blend"), "process": process, "finished": False}
        _cache["message"] = "Começando"
        bpy.app.timers.register(_run_timer, first_interval=3.0)
        return {"FINISHED"}


class HM_OT_open_result(bpy.types.Operator):
    bl_idname = "hm_editor.open_generated"
    bl_label = "Abrir o resultado"

    def execute(self, context):
        run = _cache["run"]
        if run is None or not os.path.exists(run["blend"]):
            self.report({"ERROR"}, "Ainda não há resultado")
            return {"CANCELLED"}
        path = run["blend"]
        bpy.app.timers.register(lambda: bpy.ops.wm.open_mainfile(filepath=path) and None, first_interval=0.1)
        return {"FINISHED"}


class HM_OT_check_character(bpy.types.Operator):
    bl_idname = "hm_editor.check_character"
    bl_label = "Conferir o personagem"
    bl_description = "Calcula os ossos uma vez e confere o corpo em repouso: ossos sob a pele, proporções e porcentagem de gordura. Só avisa, não bloqueia"

    def execute(self, context):
        path = _cache.get("saved")
        if not path or not os.path.exists(path):
            self.report({"ERROR"}, "Salve o personagem primeiro")
            return {"CANCELLED"}
        cfg = builder.config()
        p = context.scene.hm_character
        nickname = f"ficha_{p.name or 'personagem'}_{time.strftime('%H%M%S')}"
        wsl_file = builder.wsl_path(path, cfg)
        log = open(os.path.join(tempfile.gettempdir(), f"{nickname}.log"), "w", encoding="utf-8")
        subprocess.Popen(["wsl.exe", "-d", cfg["distro"], "--cd", cfg["repo"], "-e", "python3", "human-model/fast_review.py", nickname, "--body", p.sex, "--character", f"{p.sex}={wsl_file}", "--to", "layers", "--check"],
                         stdout=log, stderr=subprocess.STDOUT, creationflags=builder.NO_WINDOW)
        self.report({"INFO"}, f"Conferindo: o relatório fica em review/<hoje>/fast_review/{nickname}/{p.sex}/check.md")
        return {"FINISHED"}


class HM_PT_breast(bpy.types.Panel):
    bl_idname = "HM_PT_breast"
    bl_label = "Seios (faders ao vivo)"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Human"
    bl_order = 0

    @classmethod
    def poll(cls, context):
        return not context.scene.hm_character.legacy and _stage(context) in ("fine", "generating")

    def draw(self, context):
        p = context.scene.hm_character
        layout = self.layout
        layout.enabled = _stage(context) == "fine"
        if p.sex != "female":
            layout.label(text="Só no corpo feminino")
            return
        layout.label(text="Projeção 0: calculada pela fita")
        for prop in ("b_projection", "b_base", "b_upper", "b_lower", "b_power", "espacados", "pendentes", "assimetrico_R"):
            layout.prop(p, prop, slider=True)
        if _cache["message"]:
            layout.label(text=_cache["message"])


def _draw_choices(layout, p):
    """Stage 1: what makes the character. In stage 2 the same fields, locked."""
    for prop in ("sex", "name", "silhouette", "biotype", "height_cm", "body_fat"):
        layout.prop(p, prop)
    box = layout.box()
    box.label(text="Medidas de modelagem (cm; 0 deixa em branco)")
    for k, _ in sheet.DISTANCE_LABELS:
        box.prop(p, f"d_{k}")
    box = layout.box()
    box.label(text="Formas")
    box.prop(p, "gluteus")
    if p.sex == "female":
        for prop in ("underbust", "bust", "cup", "breast"):
            box.prop(p, prop)


def _draw_fine(layout, p):
    """Stage 2's fields, besides the breast's faders in their own panel."""
    if p.biotype != "NONE":
        box = layout.box()
        box.label(text="As duas outras partes do biotipo")
        for k, _ in sheet.BIOTYPE_LABELS:
            if k != p.biotype:
                box.prop(p, f"other_{k}")
    box = layout.box()
    box.label(text="Ossos (0 usa a proporção)")
    for prop in ("pelvis_width", "thigh_share", "humerus_share"):
        box.prop(p, prop)


def _draw_resolved(layout, p):
    box = layout.box()
    box.label(text="Ficha resolvida")
    try:
        m = _module()
        character = sheet.character_from_values(values(p))
        wrong = m.problems(character)
        if wrong:
            for w in wrong:
                box.label(text=w, icon="ERROR")
        else:
            for label, value, source in sheet.rows(_resolved(character)):
                row = box.row()
                row.label(text=label)
                row.label(text=f"{value} ({source})")
    except OSError as e:
        box.label(text=f"Repositório indisponível: {e}", icon="ERROR")


class HM_PT_character(bpy.types.Panel):
    bl_idname = "HM_PT_character"
    bl_label = "Ficha do personagem"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Human"

    @classmethod
    def poll(cls, context):
        return not context.scene.hm_character.legacy and _stage(context) != "built"

    def draw(self, context):
        p = context.scene.hm_character
        layout = self.layout
        stage = _stage(context)
        if stage == "choices":
            layout.label(text="Etapa 1: escolhas", icon="PROPERTIES")
            _draw_choices(layout, p)
            moved = sheet.fine_moved({k: getattr(p, k) for k in sheet.FINE_FIELDS})
            if moved:
                box = layout.box()
                box.alert = True
                box.label(text=f"{len(moved)} ajustes finos têm prioridade sobre as formas", icon="ERROR")
                box.operator("hm_editor.reset_fine")
            _draw_resolved(layout, p)
            layout.operator("hm_editor.close_choices", icon="CHECKMARK")
            if _cache["message"]:
                layout.label(text=_cache["message"])
            return
        layout.label(text="Etapa 2: ajustes finos" if stage == "fine" else "Gerando o corpo", icon="MODIFIER" if stage == "fine" else "SORTTIME")
        header, body = layout.panel("hm_locked_choices", default_closed=True)
        header.label(text="Escolhas fechadas", icon="LOCKED")
        if body:
            column = body.column()
            column.enabled = False
            _draw_choices(column, p)
        column = layout.column()
        column.enabled = stage == "fine"
        _draw_fine(column, p)
        _draw_resolved(layout, p)
        if stage == "fine":
            layout.operator("hm_editor.make_character_human")
            layout.operator("hm_editor.generate_character", icon="PLAY")
        run = _cache["run"]
        if run is not None and run.get("finished") and os.path.exists(run["blend"]):
            layout.operator("hm_editor.open_generated")
        if _cache["message"]:
            layout.label(text=_cache["message"])
        if stage == "fine":
            layout.operator("hm_editor.save_character")
            layout.operator("hm_editor.check_character")
            layout.operator("hm_editor.reset_fine")
            layout.operator("hm_editor.reopen_choices", icon="LOOP_BACK")


_registered = []


def register():
    group = _group()
    _registered[:] = [group, HM_OT_save_character, HM_OT_close_choices, HM_OT_reopen_choices, HM_OT_reset_fine, HM_OT_make_human, HM_OT_generate, HM_OT_open_result, HM_OT_check_character, HM_PT_breast, HM_PT_character]
    for c in _registered:
        bpy.utils.register_class(c)
    bpy.types.Scene.hm_character = PointerProperty(type=group)


def unregister():
    for timer in (_preview_timer, _run_timer):
        if bpy.app.timers.is_registered(timer):
            bpy.app.timers.unregister(timer)
    del bpy.types.Scene.hm_character
    for c in reversed(_registered):
        bpy.utils.unregister_class(c)
    _registered.clear()

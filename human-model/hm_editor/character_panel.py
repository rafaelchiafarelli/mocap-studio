"""The character sheet panel in Blender: silhouette, biotype with its two other parts, height, body fat, the pattern-making distances, shapes and cup, each field of the resolved sheet shown with where it came from; saving the character file (initiative body-type-selection).
Portuguese labels: the trade's terms. Uses hmcore's character module from this add-on's repository."""
import json
import bpy
from bpy.props import EnumProperty, FloatProperty, PointerProperty, StringProperty
from . import builder, sheet


_cache = {"module": None, "resolved": {}}


def _module():
    if _cache["module"] is None:  # it is read through WSL's network path, too slow for every redraw
        _cache["module"] = sheet.character_module(builder.config())
    return _cache["module"]


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


def values(p):
    return {"sex": p.sex, "name": p.name, "silhouette": p.silhouette, "height_cm": p.height_cm, "body_fat_percent": p.body_fat, "underbust_cm": p.underbust, "bust_cm": p.bust, "cup": p.cup,
            "biotype": p.biotype, "others": {k: getattr(p, f"other_{k}") for k, _ in sheet.BIOTYPE_LABELS if k != p.biotype},
            "distances": {k: getattr(p, f"d_{k}") for k, _ in sheet.DISTANCE_LABELS}, "gluteus": p.gluteus, "breast": p.breast, "espacados": p.espacados, "pendentes": p.pendentes, "assimetrico_R": p.assimetrico_R,
            "bone_parameters": {"pelvis_width_cm": p.pelvis_width, "thigh_share_of_leg": p.thigh_share, "humerus_share_of_arm": p.humerus_share}}


def _group():
    props = {
        "sex": EnumProperty(name="Sexo", items=(("female", "Feminino", ""), ("male", "Masculino", "")), default="female"),
        "name": StringProperty(name="Nome", default=""),
        "silhouette": EnumProperty(name="Silhueta", items=_silhouettes),
        "biotype": EnumProperty(name="Biotipo", items=(("NONE", "(nenhum)", ""), *[(k, v, "") for k, v in sheet.BIOTYPE_LABELS])),
        "height_cm": FloatProperty(name="Altura (cm)", min=0, max=230), "body_fat": FloatProperty(name="Gordura %", min=0, max=60),
        "underbust": FloatProperty(name="Sub-busto (cm)", min=0, max=170), "bust": FloatProperty(name="Busto (cm)", min=0, max=170),
        "cup": EnumProperty(name="Copa", items=[("NONE", "(calculada)", "")] + [(c, c, "") for c in "ABCDEFGH"]),
        "gluteus": EnumProperty(name="Glúteo", items=(("NONE", "(nenhuma)", ""), ("quadrado", "Quadrado", ""), ("redondo", "Redondo", ""), ("coracao", "Coração", ""), ("em_v", "Em V", ""))),
        "breast": EnumProperty(name="Seio", items=(("NONE", "(nenhuma)", ""), ("redondos", "Redondos", ""), ("gota", "Gota", ""), ("conicos", "Cônicos", ""), ("tuberosos", "Tuberosos", ""))),
        "espacados": FloatProperty(name="Espaçados", min=0, max=1), "pendentes": FloatProperty(name="Pendentes", min=0, max=1), "assimetrico_R": FloatProperty(name="Assimetria (direito)", min=0, max=1.5),
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
        self.report({"INFO"}, f"Salvo em {self.filepath}")
        return {"FINISHED"}


class HM_PT_character(bpy.types.Panel):
    bl_idname = "HM_PT_character"
    bl_label = "Ficha do personagem"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Human"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        p = context.scene.hm_character
        layout = self.layout
        for prop in ("sex", "name", "silhouette", "biotype", "height_cm", "body_fat"):
            layout.prop(p, prop)
        if p.biotype != "NONE":
            box = layout.box()
            box.label(text="As duas outras partes do biotipo")
            for k, _ in sheet.BIOTYPE_LABELS:
                if k != p.biotype:
                    box.prop(p, f"other_{k}")
        box = layout.box()
        box.label(text="Medidas de modelagem (cm; 0 deixa em branco)")
        for k, _ in sheet.DISTANCE_LABELS:
            box.prop(p, f"d_{k}")
        box = layout.box()
        box.label(text="Formas")
        box.prop(p, "gluteus")
        if p.sex == "female":
            for prop in ("underbust", "bust", "cup", "breast", "espacados", "pendentes", "assimetrico_R"):
                box.prop(p, prop)
        box = layout.box()
        box.label(text="Ossos (0 usa a proporção)")
        for prop in ("pelvis_width", "thigh_share", "humerus_share"):
            box.prop(p, prop)
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
        layout.operator("hm_editor.save_character")


_registered = []


def register():
    group = _group()
    _registered[:] = [group, HM_OT_save_character, HM_PT_character]
    for c in _registered:
        bpy.utils.register_class(c)
    bpy.types.Scene.hm_character = PointerProperty(type=group)


def unregister():
    del bpy.types.Scene.hm_character
    for c in reversed(_registered):
        bpy.utils.unregister_class(c)
    _registered.clear()

"""Faders for the mouth: every change re-bakes the animation at once. Data lives in the text block 'mouth_data.json',
the animation on the control object (an empty with the mouth properties). bake() also runs from the command line (see cli_faders.py)."""
import json
import bpy
import numpy as np
from bpy.props import EnumProperty, FloatProperty, PointerProperty, StringProperty
from bpy_extras import anim_utils

VOWELS = "AEIOU"
GROUPS = ["rest", "M", "F", "S", "SH", "T", "L", "K", "A", "E", "I", "O", "U"]
_cache = {}


def control():
    return next((o for o in bpy.data.objects if o.type == "EMPTY" and "jawOpen" in o.keys()), None)


def data():
    t = bpy.data.texts.get("mouth_data.json")
    if t is None:
        return None
    key = t.as_pointer()
    if key not in _cache:
        _cache[key] = json.loads(t.as_string())
    return _cache[key]


def compute(d, p):
    """Returns {property: values per frame}. Each sound pulls the mouth towards its pose, weighted by a bell around its time."""
    fps, n = d["fps"], d["frames"]
    t = np.arange(n) / fps
    src = d["script"] if p.source == "SCRIPT" else d["recognizer"]
    items = []
    for ph_t, group, _ in sorted(src, key=lambda x: x[0]):
        if items and p.min_spacing_ms > 0 and ph_t - items[-1][0] < p.min_spacing_ms / 1000:
            continue
        items.append((ph_t + p.offset_ms / 1000, group))
    # Silence closes the mouth once sounds are further apart than the rest gap.
    gap = p.rest_gap_ms / 1000
    full = [(items[0][0] - gap, "rest")] if items else []
    for k, (ti, g) in enumerate(items):
        full.append((ti, g))
        nxt = items[k + 1][0] if k + 1 < len(items) else ti + 2 * gap + 1
        if nxt - ti > 2 * gap:
            full += [(ti + gap, "rest"), (nxt - gap, "rest")]
    times = np.array([x[0] for x in full])
    groups = [x[1] for x in full]
    dom = np.array([p.lip_dominance if g in ("M", "F") else (p.consonant_dominance if g not in VOWELS and g != "rest" else 1.0) for g in groups])
    s = max(p.spread_ms / 1000, 1e-3)
    w = dom[None, :] * np.exp(-0.5 * ((t[:, None] - times[None, :]) / s) ** 2) + 1e-9
    w /= w.sum(1, keepdims=True)
    props = sorted({k for pose in d["poses"].values() for k in pose})
    out = {}
    for k in props:
        vals = np.zeros(len(full))
        for i, g in enumerate(groups):
            kind = p.vowel_strength if g in VOWELS else p.consonant_strength
            vals[i] = d["poses"][g].get(k, 0.0) * getattr(p, "pose_" + g) * kind
        v = (w * vals[None, :]).sum(1)
        v *= p.jaw_gain if k == "jawOpen" else p.lip_gain
        out[k] = v
    tracked = np.array(d["tracked_jaw"])[:n]
    loud = np.array(d["loudness"])[:n]
    jaw = out["jawOpen"]
    jaw = jaw * (1 - p.loudness + p.loudness * loud)
    jaw = (1 - p.tracked_mix) * jaw + p.tracked_mix * tracked
    if p.tracked_close > 0:  # where the tracked lips are shut, shut the jaw too
        shut = np.clip(1 - tracked / 0.06, 0, 1)
        jaw = jaw * (1 - p.tracked_close * shut)
    out["jawOpen"] = jaw
    if p.smooth_ms > 0:
        sg = p.smooth_ms / 1000 * fps
        r = int(3 * sg + 1)
        kern = np.exp(-0.5 * (np.arange(-r, r + 1) / sg) ** 2); kern /= kern.sum()
        out = {k: np.convolve(np.pad(v, r, mode="edge"), kern, "valid") for k, v in out.items()}
    return {k: np.clip(v, 0, 1) for k, v in out.items()}


def bake(scene):
    d = data()
    ctrl = control()
    if d is None or ctrl is None:
        return
    res = compute(d, scene.mouth_faders)
    ad = ctrl.animation_data_create()
    a = ad.action
    if a is None:
        a = bpy.data.actions.new("mouth_baked"); ad.action = a
    if not a.slots:
        ad.action_slot = a.slots.new(id_type="OBJECT", name="mouth")
    slot = ad.action_slot or a.slots[0]
    bag = anim_utils.action_ensure_channelbag_for_slot(a, slot)
    n = d["frames"]
    frames = np.arange(1, n + 1, dtype=np.float32)
    for k, v in res.items():
        path = f'["{k}"]'
        fc = bag.fcurves.find(path) or bag.fcurves.new(path)
        if len(fc.keyframe_points) != n:
            fc.keyframe_points.clear(); fc.keyframe_points.add(n)
            fc.keyframe_points.foreach_set("interpolation", [bpy.types.Keyframe.bl_rna.properties["interpolation"].enum_items["LINEAR"].value] * n)
        co = np.empty(2 * n, dtype=np.float32); co[0::2] = frames; co[1::2] = v
        fc.keyframe_points.foreach_set("co", co)
        fc.update()
    scene.frame_set(scene.frame_current)


def changed(self, context):
    bake(context.scene)


def F(name, default, lo, hi, desc):
    return FloatProperty(name=name, default=default, min=lo, max=hi, description=desc, update=changed)


_fields = {
    "source": EnumProperty(name="Sons", items=[("RECOGNIZER", "Reconhecedor", "Os sons que o reconhecedor do Parrot ouviu"), ("SCRIPT", "Roteiro", "As palavras conhecidas, com o tempo do reconhecedor")], default="SCRIPT", update=changed),
    "offset_ms": F("Antecipação (ms)", -30, -200, 200, "Negativo: a boca chega antes do som"),
    "spread_ms": F("Coarticulação (ms)", 45, 10, 200, "Maior: sons vizinhos se misturam mais; menor: poses mais secas"),
    "lip_dominance": F("Domínio M e F", 3, 0.2, 10, "Quanto M, P, B, F e V se impõem sobre os vizinhos"),
    "consonant_dominance": F("Domínio outras consoantes", 0.7, 0.2, 10, "Quanto T, S, L e K se impõem"),
    "rest_gap_ms": F("Pausa até fechar (ms)", 200, 50, 800, "Silêncio maior que isto fecha a boca"),
    "min_spacing_ms": F("Espaço mínimo (ms)", 0, 0, 200, "Descarta sons mais próximos que isto"),
    "smooth_ms": F("Suavização (ms)", 15, 0, 100, "Suaviza a curva final"),
    "vowel_strength": F("Força das vogais", 1, 0, 2, ""),
    "consonant_strength": F("Força das consoantes", 1, 0, 2, ""),
    "jaw_gain": F("Ganho do queixo", 1, 0, 2, ""),
    "lip_gain": F("Ganho dos lábios", 1, 0, 2, ""),
    "loudness": F("Volume controla abertura", 0, 0, 1, "Falar mais baixo abre menos"),
    "tracked_mix": F("Abertura do vídeo", 0, 0, 1, "Mistura a abertura rastreada do vídeo no lugar da pose"),
    "tracked_close": F("Fechamento do vídeo", 0, 0, 1, "Fecha a boca onde o vídeo mostra lábios fechados"),
    "preset_path": StringProperty(name="Preset", subtype="FILE_PATH", default="//"),
}
for g in GROUPS:
    _fields["pose_" + g] = F(g, 1, 0, 2, "Força desta pose")
Params = type("MouthFaderParams", (bpy.types.PropertyGroup,), {"__annotations__": _fields})


def params_dict(p):
    return {k: (p.source if k == "source" else round(getattr(p, k), 4)) for k in _fields if k != "preset_path"}


def apply_dict(p, values):
    for k, v in values.items():
        if k in _fields and k != "preset_path":
            p[k] = v if k != "source" else {"RECOGNIZER": 0, "SCRIPT": 1}[v]


class SavePreset(bpy.types.Operator):
    bl_idname = "mouth_faders.save"; bl_label = "Salvar preset"
    def execute(self, context):
        p = context.scene.mouth_faders
        with open(bpy.path.abspath(p.preset_path), "w") as f:
            json.dump(params_dict(p), f, indent=1)
        return {"FINISHED"}


class LoadPreset(bpy.types.Operator):
    bl_idname = "mouth_faders.load"; bl_label = "Carregar preset"
    def execute(self, context):
        p = context.scene.mouth_faders
        apply_dict(p, json.load(open(bpy.path.abspath(p.preset_path))))
        bake(context.scene)
        return {"FINISHED"}


class ResetFaders(bpy.types.Operator):
    bl_idname = "mouth_faders.reset"; bl_label = "Zerar faders"
    def execute(self, context):
        p = context.scene.mouth_faders
        for k in _fields:
            if k != "preset_path":
                p.property_unset(k)
        bake(context.scene)
        return {"FINISHED"}


class MOUTH_PT_faders(bpy.types.Panel):
    bl_label = "Faders da boca"; bl_space_type = "VIEW_3D"; bl_region_type = "UI"; bl_category = "Boca"
    def draw(self, context):
        p = context.scene.mouth_faders; L = self.layout
        L.prop(p, "source", expand=True)
        def box(title, names):
            b = L.box(); b.label(text=title)
            for n in names:
                b.prop(p, n, slider=True)
        box("Tempo", ["offset_ms", "spread_ms", "lip_dominance", "consonant_dominance", "rest_gap_ms", "min_spacing_ms", "smooth_ms"])
        box("Força", ["vowel_strength", "consonant_strength", "jaw_gain", "lip_gain"])
        box("Do vídeo e do áudio", ["tracked_mix", "tracked_close", "loudness"])
        box("Poses", ["pose_" + g for g in GROUPS])
        b = L.box(); b.prop(p, "preset_path")
        r = b.row(); r.operator("mouth_faders.save"); r.operator("mouth_faders.load")
        b.operator("mouth_faders.reset")


CLASSES = (Params, SavePreset, LoadPreset, ResetFaders, MOUTH_PT_faders)


def register():
    for c in CLASSES:
        bpy.utils.register_class(c)
    bpy.types.Scene.mouth_faders = PointerProperty(type=Params)


def unregister():
    del bpy.types.Scene.mouth_faders
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)

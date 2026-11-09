"""The character sheet panel's pure part: from the panel's values to a character file, and from a resolved sheet to the rows shown. No bpy, so it can be tested. hmcore's character module is loaded from this add-on's repository (install.json)."""
import importlib.util, os

SOURCE_LABELS = {"current": "atual", "biotype": "biotipo", "body_fat": "gordura", "height": "altura", "silhouette": "silhueta", "typed": "digitado"}
BIOTYPE_LABELS = (("ectomorph", "Ectomorfo"), ("mesomorph", "Mesomorfo"), ("endomorph", "Endomorfo"))
DISTANCE_LABELS = (("busto", "1. Busto"), ("cintura", "2. Cintura"), ("quadril", "3. Quadril"), ("cintura_quadril", "4. Cintura/quadril"), ("comprimento_corpo", "5. Comprimento do corpo"),
                   ("cava", "6. Cava"), ("manga", "7. Manga"), ("punho", "8. Punho"), ("largura_costas", "9. Largura das costas"), ("saia", "10. Saia"), ("calca", "11. Calça"),
                   ("gancho_sentado", "12. Gancho sentado"), ("gancho", "13. Gancho"), ("joelho", "14. Joelho"), ("tornozelo", "15. Tornozelo"))
SHOWN = ("height", "bust", "underbust", "cup", "waist", "hip", "shoulder_width", "body_fat_percent", "muscle", "bone_thickness")
SHOWN_LABELS = {"height": "Altura", "bust": "Busto", "underbust": "Sub-busto", "cup": "Copa", "waist": "Cintura", "hip": "Quadril", "shoulder_width": "Largura de ombros", "body_fat_percent": "Gordura %", "muscle": "Músculo (fator)", "bone_thickness": "Espessura óssea (fator)"}
UNSET = (0, 0.0, "", None, "NONE")
BREAST_FADERS = ("projection_cm", "base_cm", "upper", "lower", "power")  # hmcore.character.BREAST_FADERS


def repo_path(cfg, *parts):
    """A path inside the repository this add-on was installed from, by its Windows path in WSL."""
    return os.path.join("\\\\wsl.localhost", cfg["distro"], *cfg["repo"].strip("/").split("/"), *parts)


def repo_module(cfg, name, file_of=None):
    """A module of hmcore/ from that repository, loaded from its file: the add-on is packed without it."""
    spec = importlib.util.spec_from_file_location(f"hm_{name}", file_of or repo_path(cfg, "human-model", "hmcore", f"{name}.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def character_module(cfg, file_of=None):
    return repo_module(cfg, "character", file_of)


def character_from_values(v):
    """A character file from the panel's values: what is left at 0 or blank stays unset."""
    c = {"sex": v["sex"]}
    for key in ("name", "silhouette", "height_cm", "body_fat_percent", "underbust_cm", "bust_cm", "cup"):
        if v.get(key) not in UNSET:
            c[key] = v[key]
    if v.get("biotype") not in UNSET:
        others = {k: v["others"][k] for k in v.get("others", {}) if v["others"][k] not in UNSET}
        c["biotype"] = {"type": v["biotype"], **({"others": others} if others else {})}
    distances = {k: x for k, x in v.get("distances", {}).items() if x not in UNSET}
    if distances:
        c["distances"] = distances
    parameters = {k: x for k, x in v.get("bone_parameters", {}).items() if x not in UNSET}
    if parameters:
        c["bone_parameters"] = parameters
    if v.get("gluteus") not in UNSET:
        c["gluteus"] = {"shape": v["gluteus"]}
    breast = {}
    if v.get("breast") not in UNSET:
        breast["shape"] = v["breast"]
    for key in ("espacados", "pendentes"):
        if v.get(key) not in UNSET:
            breast[key] = v[key]
    if v.get("assimetrico_R") not in UNSET:
        breast["assimetricos"] = {"L": 1.0, "R": v["assimetrico_R"]}
    for key in BREAST_FADERS:
        if v.get(key) not in UNSET:
            breast[key] = v[key]
    if breast:
        c["breast"] = breast
    return c


def stage_line(run):
    """What a run of fast_review.py is doing now, from its run.json: for the panel."""
    stages = run.get("stages", {})
    done = sum(s.get("status") in ("done", "reused") for s in stages.values())
    current = next((k for k, s in stages.items() if s.get("status") == "running"), None)
    if run.get("status") == "failed":
        return f"Falhou na etapa {run.get('failed_stage')}"
    if run.get("status") == "done":
        return "Pronto"
    return f"Etapa {done + 1} de 8: {current}" if current else "Começando"


def rows(resolved):
    """(label, value text, where it came from) for each shown field."""
    out = []
    for key in SHOWN:
        field = resolved["fields"].get(key)
        if field is None:
            continue
        value = field["value"]
        text = value if isinstance(value, str) else (f"{value:.1f}" if key not in ("muscle", "bone_thickness") else f"{value:.2f}")
        out.append((SHOWN_LABELS[key], text, SOURCE_LABELS[field["source"]]))
    return out

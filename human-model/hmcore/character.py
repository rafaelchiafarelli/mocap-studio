"""A character's sheet, the file its design is saved in (initiative body-type-selection): silhouette, biotype, height, body fat, pattern-making distances,
bone parameters, shapes and per-region physical values. No Blender and nothing outside the standard library, so fast_review.py and the editor can use it.
A character's file lives in the film root, never in the repository; the neutral ones in tests/fixtures and data/characters/test are the exception."""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
SEXES = ("female", "male")
BIOTYPES = ("ectomorph", "mesomorph", "endomorph")
MOST_OF_ONE_OTHER, MOST_OF_BOTH_OTHERS = 0.35, 0.65  # Rafael, 2026-11-08: the chosen type is always the largest
GLUTEUS_SHAPES = ("quadrado", "redondo", "coracao", "em_v")  # coração is also A, pêra invertida and trapezoidal: one shape
BREAST_SHAPES = ("redondos", "gota", "conicos", "tuberosos")  # exclusive
BREAST_ADJUSTMENTS = ("espacados", "assimetricos", "pendentes")  # independent, combined with any shape
BREAST_FADERS = ("projection_cm", "base_cm", "upper", "lower", "power")  # override the shape's outline, from the panel's faders
ZONE_NAMES = ("neck", "chest", "breast_L", "breast_R", "upper_back", "belly", "flanks", "lower_back", "hips", "buttocks_upper_center", "buttocks_upper_side", "buttocks_lower_center", "buttocks_lower_side",
              "thigh_front", "thigh_back", "thigh_inner", "thigh_outer", "knee", "calf_front", "calf_back",
              "upper_arm_front", "upper_arm_back", "forearm")  # hmcore.body.ZONES; a test keeps them in step, since that module needs numpy
REGION_VALUES = ("young_pa", "poisson", "density", "damping", "fat_mm")
# The 15 measures of Modelagem_Plana-referencia.pdf, in its order; the tape measure each one is (None: not a body measure the tape has)
DISTANCES = {"busto": "bust", "cintura": "waist", "quadril": "hip", "cintura_quadril": "hip_height", "comprimento_corpo": "back_length", "cava": None, "manga": "arm_length", "punho": "wrist",
             "largura_costas": "shoulder_width", "saia": None, "calca": None, "gancho_sentado": "rise", "gancho": None, "joelho": "knee", "tornozelo": "ankle"}
BONE_PARAMETERS = ("pelvis_width_cm", "thigh_share_of_leg", "humerus_share_of_arm")
FIELDS = ("sex", "name", "silhouette", "biotype", "height_cm", "body_fat_percent", "distances", "bone_parameters", "gluteus", "breast", "underbust_cm", "bust_cm", "cup", "regions")


def _json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def silhouette_ratios(data=DATA):
    return _json(os.path.join(data, "silhouette_ratios.json"))


def _number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _biotype_problems(b):
    if not isinstance(b, dict) or b.get("type") not in BIOTYPES:
        return [f"biotype.type must be one of {', '.join(BIOTYPES)}"]
    others = b.get("others", {})
    if not isinstance(others, dict) or not set(others) <= set(BIOTYPES) - {b["type"]}:
        return [f"biotype.others may name only the other two types of {b['type']}"]
    out = []
    for name, part in others.items():
        if not _number(part) or not 0 <= part <= MOST_OF_ONE_OTHER:
            out.append(f"biotype.others.{name} must be from 0 to {MOST_OF_ONE_OTHER}")
    if not out and sum(others.values()) > MOST_OF_BOTH_OTHERS + 1e-9:
        out.append(f"biotype.others can add up to {MOST_OF_BOTH_OTHERS} together")
    return out


def _breast_problems(b):
    if not isinstance(b, dict):
        return ["breast must be an object"]
    out = []
    if b.get("shape") is not None and b["shape"] not in BREAST_SHAPES:
        out.append(f"breast.shape must be one of {', '.join(BREAST_SHAPES)}")
    for k in set(b) - {"shape", "balloon_cc", "balloon_spacing", *BREAST_ADJUSTMENTS, *BREAST_FADERS}:
        out.append(f"breast.{k} isn't a shape or an adjustment")
    if "balloon_cc" in b and (not _number(b["balloon_cc"]) or b["balloon_cc"] <= 0):
        out.append("breast.balloon_cc must be a positive number")
    if "balloon_spacing" in b and (not _number(b["balloon_spacing"]) or b["balloon_spacing"] <= 0):
        out.append("breast.balloon_spacing must be a positive number")
    if "balloon_cc" in b and "projection_cm" in b:
        out.append("give breast.balloon_cc or breast.projection_cm, not both: the balloon's volume sets the projection")
    for k in BREAST_FADERS:
        if k in b and (not _number(b[k]) or b[k] <= 0):
            out.append(f"breast.{k} must be a positive number")
    for k in BREAST_ADJUSTMENTS:
        if k in b and not _number(b[k]) and not (k == "assimetricos" and isinstance(b[k], dict) and set(b[k]) <= {"L", "R"} and all(_number(v) for v in b[k].values())):
            out.append(f"breast.{k} must be a number" + (" or {L, R}" if k == "assimetricos" else ""))
    return out


def _ranged(c, key, lo, hi, out):
    if c.get(key) is not None and (not _number(c[key]) or not lo <= c[key] <= hi):
        out.append(f"{key} must be from {lo} to {hi}")


def problems(c, ratios=None):
    """Why this character can't be used, as sentences. Empty when it can. Anything left out is left unset."""
    ratios = silhouette_ratios() if ratios is None else ratios
    out = [f"{k} isn't a field of a character" for k in c if k not in FIELDS]
    sex = c.get("sex")
    if sex not in SEXES:
        return out + ["sex must be female or male"]
    if c.get("silhouette") is not None and c["silhouette"] not in ratios[sex]:
        out.append(f"silhouette must be one of {', '.join(ratios[sex])}")
    if c.get("biotype") is not None:
        out += _biotype_problems(c["biotype"])
    _ranged(c, "height_cm", 120, 230, out)
    _ranged(c, "body_fat_percent", 3, 60, out)
    for k, v in (c.get("distances") or {}).items():
        if k not in DISTANCES:
            out.append(f"distances.{k} isn't one of the 15 pattern-making measures")
        elif not _number(v) or v <= 0:
            out.append(f"distances.{k} must be a positive number of centimetres")
    for k, v in (c.get("bone_parameters") or {}).items():
        if k not in BONE_PARAMETERS:
            out.append(f"bone_parameters.{k} isn't a bone parameter")
        elif not _number(v) or v <= 0 or (k.endswith("_of_leg") or k.endswith("_of_arm")) and v >= 1:
            out.append(f"bone_parameters.{k} is out of range")
    glute = c.get("gluteus")
    if glute is not None and (not isinstance(glute, dict) or glute.get("shape") not in GLUTEUS_SHAPES):
        out.append(f"gluteus.shape must be one of {', '.join(GLUTEUS_SHAPES)}")
    if c.get("breast") is not None:
        out += _breast_problems(c["breast"])
    if sex == "male":
        out += [f"{k} applies to the female body only" for k in ("breast", "underbust_cm", "bust_cm", "cup") if c.get(k) is not None]
    for k in ("underbust_cm", "bust_cm"):
        _ranged(c, k, 50, 170, out)
    if c.get("cup") is not None and c.get("bust_cm") is not None:
        out.append("give the cup or the bust, not both: each sets the other")
    if c.get("cup") is not None and c["cup"] not in _json(os.path.join(DATA, "cup_table.json"))["letters"]:
        out.append("cup isn't a letter of data/cup_table.json")
    for zone, values in (c.get("regions") or {}).items():
        if zone not in ZONE_NAMES:
            out.append(f"regions.{zone} isn't a zone")
        elif not isinstance(values, dict) or not set(values) <= set(REGION_VALUES) or not all(_number(v) for v in values.values()):
            out.append(f"regions.{zone} may give only {', '.join(REGION_VALUES)}, as numbers")
    return out


def load(path, ratios=None):
    """A character file, checked. Raises ValueError with every problem."""
    c = _json(path)
    found = problems(c, ratios)
    if found:
        raise ValueError(f"{path}: " + "; ".join(found))
    return c


# How each tape measure grows with height: girths and widths by width_growth_per_height, lengths in step
WIDENING = ("bust", "underbust", "waist", "hip", "neck", "upper_arm", "wrist", "thigh", "knee", "calf", "ankle", "shoulder_width", "shoulder", "bust_span")
LIMB_LENGTHS = ("inseam", "arm_length", "knee_height")
SILHOUETTE_INSIDE = 0.005  # how far inside a range a ratio is moved, so it isn't on the edge


def base_measures(sex, data=DATA):
    """The neutral body's tape measures, cm, as measured in data/measure_sweep.json."""
    return dict(_json(os.path.join(data, "measure_sweep.json"))[sex]["base_cm"])


def biotype_mix(b, table):
    """The weighted mean of each biotype value, for a chosen type and its two other parts."""
    weights = {**{k: 0.0 for k in BIOTYPES}, **b.get("others", {})}
    weights[b["type"]] = 1.0 - sum(b.get("others", {}).values())
    return {key: sum(w * table[t][key] for t, w in weights.items()) for key in table[BIOTYPES[0]]}


def _field(value, source):
    return {"value": round(float(value), 4), "source": source}


def _ratio_towards(ratio, limits):
    """The nearest ratio inside [lo, hi], or the ratio itself if it's already there; either end can be open."""
    if limits is None:
        return ratio
    lo, hi = limits
    if lo is not None and ratio < lo:
        return lo + SILHOUETTE_INSIDE
    if hi is not None and ratio > hi:
        return hi - SILHOUETTE_INSIDE
    return ratio


def resolve(c, base_cm=None, biotypes=None, ratios=None, data=DATA, cups=None):
    """The full sheet: every field with its value and where it came from: current, biotype, body_fat, height, silhouette or typed.
    Each step only fills in the next one's starting values, and what is typed always wins."""
    sex = c["sex"]
    base_cm = base_measures(sex, data) if base_cm is None else base_cm
    biotypes = _json(os.path.join(data, "biotypes.json")) if biotypes is None else biotypes
    ratios = silhouette_ratios(data) if ratios is None else ratios
    sheet = {k: _field(v, "current") for k, v in base_cm.items()}
    sheet["body_fat_percent"] = _field(biotypes["current_body_fat_percent"][sex], "current")
    for k in ("bone_thickness", "limb_length", "muscle"):
        sheet[k] = _field(1.0, "current")

    def change(key, value, source):
        if abs(value - sheet[key]["value"]) > 1e-6:
            sheet[key] = _field(value, source)

    if c.get("biotype"):
        m = biotype_mix(c["biotype"], biotypes)
        for k in ("bone_thickness", "limb_length", "muscle"):
            change(k, m[k], "biotype")
        change("shoulder_width", sheet["shoulder_width"]["value"] * m["shoulders"], "biotype")
        change("waist", sheet["waist"]["value"] * m["waist"], "biotype")
        change("hip", sheet["hip"]["value"] * m["hips"], "biotype")
        for k in LIMB_LENGTHS:
            change(k, sheet[k]["value"] * m["limb_length"], "biotype")
        change("body_fat_percent", sheet["body_fat_percent"]["value"] + m["body_fat_delta"], "biotype")
    if c.get("body_fat_percent") is not None:
        change("body_fat_percent", c["body_fat_percent"], "typed")
    extra = (sheet["body_fat_percent"]["value"] - biotypes["current_body_fat_percent"][sex]) / 100
    for key, share in biotypes["fat_changes_girths"].items():
        change(key, sheet[key]["value"] * (1 + share * extra), "body_fat")
    if c.get("height_cm") is not None and c["height_cm"] != base_cm["height"]:
        k = c["height_cm"] / base_cm["height"]
        widening = k ** ratios["width_growth_per_height"]
        for key in base_cm:
            if key != "height":
                change(key, sheet[key]["value"] * (widening if key in WIDENING else k), "height")
    if c.get("height_cm") is not None:
        change("height", c["height_cm"], "typed")
    if c.get("silhouette"):
        limits = ratios[sex][c["silhouette"]]
        proxies = ratios["ansur_proxies"][sex]
        hip = sheet["hip"]["value"]
        change("waist", _ratio_towards(sheet["waist"]["value"] / hip, limits.get("waist_hip")) * hip, "silhouette")
        if "bust_hip" in limits:
            change("bust", _ratio_towards(sheet["bust"]["value"] / hip, limits.get("bust_hip")) * hip, "silhouette")
        breadth_to_hip = proxies["bideltoid_over_biacromial"] / proxies["hip_breadth_over_hip_girth"] / hip
        change("shoulder_width", _ratio_towards(sheet["shoulder_width"]["value"] * breadth_to_hip, limits.get("shoulder_hip")) / breadth_to_hip, "silhouette")
    for name, value in (c.get("distances") or {}).items():
        if DISTANCES[name] is not None:
            change(DISTANCES[name], value, "typed")
    if sex == "female":
        _apply_cup(c, sheet, change, _json(os.path.join(data, "cup_table.json")) if cups is None else cups)
    return {"sex": sex, "fields": sheet}


def cup_letter(difference, cups):
    """The letter for this bust minus underbust, at step_cm per letter; first and last letter past either end."""
    i = round((difference - cups["first_difference_cm"]) / cups["step_cm"])
    return cups["letters"][max(0, min(len(cups["letters"]) - 1, i))]


def bust_for_cup(underbust, letter, cups):
    return underbust + cups["first_difference_cm"] + cups["letters"].index(letter) * cups["step_cm"]


def _apply_cup(c, sheet, change, cups):
    """Setting the cup holds the thorax and raises the bust; setting the bust recalculates the cup; a changed underbust with the cup set moves the bust."""
    if c.get("underbust_cm") is not None:
        change("underbust", c["underbust_cm"], "typed")
    if c.get("bust_cm") is not None:
        change("bust", c["bust_cm"], "typed")
    if c.get("cup") is not None:
        change("bust", bust_for_cup(sheet["underbust"]["value"], c["cup"], cups), "typed")
        sheet["cup"] = {"value": c["cup"], "source": "typed"}
    else:
        sheet["cup"] = {"value": cup_letter(sheet["bust"]["value"] - sheet["underbust"]["value"], cups), "source": sheet["bust"]["source"]}

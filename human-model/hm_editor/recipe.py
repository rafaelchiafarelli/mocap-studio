"""The recipe file build_model.py reads (docs/running.md): making, checking and reading one back. No bpy, so it can be tested."""
import json, re

ASSETS = {"eyes": "eyes/high-poly/high-poly.mhclo", "teeth": "teeth/teeth_base/teeth_base.mhclo", "tongue": "tongue/tongue01/tongue01.mhclo"}
MACROS = ("gender", "age", "muscle", "weight", "height", "proportions", "cupsize", "firmness")
GENDER = {"male": 1.0, "female": 0.0}
ADULT_AGE = 0.5  # below it MPFB makes a child's body (docs/running.md)
FORBIDDEN_PREFIXES = ("penis-", "bulge-")  # no genitalia in either model (docs/status.md)


def new(name, sex):
    macros = {m: 0.5 for m in MACROS}
    macros["gender"] = GENDER[sex]
    macros["race"] = {"african": 0.33, "asian": 0.33, "caucasian": 0.34}
    return {"name": safe_name(name), "sex": sex, "macros": macros, "targets": {}, "assets": dict(ASSETS)}


def safe_name(name):
    """A name that's safe in file names and object names."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")


def problems(r):
    """Why this recipe can't be built, as sentences. Empty when it can."""
    out = []
    if not r.get("name") or r.get("name") != safe_name(r.get("name", "")):
        out.append("The name may use only letters, numbers, - and _")
    sex = r.get("sex")
    if sex not in GENDER:
        out.append("Sex must be male or female")
    macros = r.get("macros", {})
    for m in MACROS:
        if not isinstance(macros.get(m), (int, float)) or not 0 <= macros[m] <= 1:
            out.append(f"Macro {m} must be from 0 to 1")
    if sex in GENDER and macros.get("gender") != GENDER[sex]:
        out.append(f"Gender must be {GENDER[sex]} for {sex}: in-between values are untested")
    if isinstance(macros.get("age"), (int, float)) and macros["age"] < ADULT_AGE:
        out.append(f"Age must be at least {ADULT_AGE}: below it the body is a child's")
    race = macros.get("race", {})
    if sorted(race) != ["african", "asian", "caucasian"] or abs(sum(race.values()) - 1) > 0.01:
        out.append("Race must have african, asian and caucasian, summing to 1")
    for name, value in r.get("targets", {}).items():
        if not 0 <= value <= 1:
            out.append(f"Target {name} must be from 0 to 1")
        if name.startswith(FORBIDDEN_PREFIXES):
            out.append(f"Target {name} isn't allowed: no genitalia in either model")
    return out


def rebalance(race, name, value):
    """Sets one ancestry and scales the others so the three still sum to 1."""
    value = min(max(value, 0.0), 1.0)
    others = [k for k in race if k != name]
    rest = sum(race[k] for k in others)
    out = {name: value}
    for k in others:
        out[k] = (1 - value) * (race[k] / rest if rest > 1e-6 else 1 / len(others))
    return out


def identity_targets(keys, is_target):
    """The named sliders among (shape key name, value) pairs. Muscle and body shapes (F_, B_), macro details ($) and zero values aren't part of the recipe."""
    return {n: round(v, 4) for n, v in keys if n != "Basis" and not n.startswith(("F_", "B_", "$")) and round(v, 4) != 0 and is_target(n)}


def rounded_macros(macros):
    out = {k: round(v, 4) for k, v in macros.items() if k != "race"}
    out["race"] = {k: round(v, 4) for k, v in macros["race"].items()}
    return out


def dumps(r):
    return json.dumps(r, indent=1, ensure_ascii=False)

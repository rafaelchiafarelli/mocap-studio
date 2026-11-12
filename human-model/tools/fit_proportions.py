"""Finds a recipe whose body reaches a height, a waist/hip and a shoulder/hip, moving the waist, hip and shoulder sliders and the height macro; the belly (stomach-pregnant) only if belly= allows it, since it makes a pot belly.

    python3 human-model/tools/fit_proportions.py RECIPE.json OUT_RECIPE.json WORK_DIR [height_cm=170] [waist_hip=0.69] [shoulder_hip=1.35] [limit=0.5] [belly=0]

Runs in WSL (standard library only) and calls Blender through blender_run.py. Each round measures the real mesh with the editor's tape (blender/body_tape.py), so the tape's convex outline is what gets fitted; the slider sweeps in
data/measure_sweep.json only give the direction. Sliders stay within +-0.5, where MPFB's targets don't distort, the belly within 0.8; each round picks, among all their combinations, the one its measures predict nearest both ratios. shoulder_hip is the tape's definition (shoulder width against hip girth, through ANSUR II means), and it reads higher on MPFB than on photos, so a photo's value has to be applied as a change from the neutral body.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
TOLERANCE = 0.02  # on each ratio
HEIGHT_TOLERANCE_CM = 0.5
ROUNDS = 7
LIMIT = 0.5
proxies = {"bideltoid_over_biacromial": 1.233, "hip_breadth_over_hip_girth": 0.347}  # ANSUR II means for women
SLIDERS = {"waist": "measure-waist-circ-decr-incr", "hip": "measure-hips-circ-decr-incr", "shoulder_width": "measure-shoulder-dist-decr-incr"}
STOMACH = "stomach-pregnant-incr"  # one-way: the belly, for waists that the waist slider alone can't reach (oval, rectangle)
# cm per unit of slider on the neutral woman, each way, from data/measure_sweep.json (the stomach's first guess is corrected after each round)
GAIN = {"waist": (9.4, 9.4), "hip": (8.8, 17.8), "shoulder_width": (2.8, 5.0)}
STOMACH_LIMIT = 0.0  # off: the "pregnant" target raised the waist by pushing a belly forward, and every slim body came out pot-bellied (Rafael, 2026-11-12)
PENALTY = 0.002  # prefers smaller slider moves among equally good ones
STATURE = [(0.0, 123.5), (0.25, 141.6), (0.5, 159.1), (0.75, 193.4), (1.0, 229.2)]  # the woman's height per macro, data/macro_sweep.json


def tape(recipe: dict, work: Path, n: int) -> dict:
    path = work / f"ronda_{n}.json"
    out = work / f"ronda_{n}_fita.json"
    path.write_text(json.dumps(recipe, indent=1), encoding="utf-8")
    subprocess.run([sys.executable, str(HERE / "blender_run.py"), str(HERE / "blender" / "body_tape.py"), str(path.resolve()), str(out.resolve())], check=True, capture_output=True, text=True)
    return json.loads(out.read_text(encoding="utf-8"))


def macro_for(height_cm: float) -> float:
    for (x0, y0), (x1, y1) in zip(STATURE, STATURE[1:]):
        if height_cm <= y1:
            return x0 + (height_cm - y0) / (y1 - y0) * (x1 - x0)
    return STATURE[-1][0]


def clip(value, low, high):
    return max(low, min(high, value))


def main(args) -> int:
    if len(args) < 3:
        print(__doc__)
        return 2
    recipe = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    out, work = Path(args[1]), Path(args[2])
    goals = {"height_cm": 170.0, "waist_hip": 0.69, "shoulder_hip": 1.35}
    for item in args[3:]:
        key, value = item.split("=")
        goals[key] = float(value)
    work.mkdir(parents=True, exist_ok=True)
    sweep = json.loads((HERE / "data" / "measure_sweep.json").read_text(encoding="utf-8"))["female"]["sliders"]
    gain = {k: abs(sweep[name]["0.5"].get(k, 3.0)) / 0.5 for k, name in SLIDERS.items()}  # cm per unit of slider

    macro = macro_for(goals["height_cm"])
    values = {k: 0.0 for k in SLIDERS}
    stomach, stomach_gain = 0.0, 12.0
    history = []
    previous = None

    def effect(name, v):
        down, up = GAIN[name]
        return v * (up if v > 0 else down)

    steps = int(round(goals.get("limit", LIMIT) / 0.05))
    grid = [round(x * 0.05, 2) for x in range(-steps, steps + 1)]
    belly = [round(x * 0.05, 2) for x in range(0, int(round(goals.get("belly", STOMACH_LIMIT) / 0.05)) + 1)]
    for n in range(1, ROUNDS + 1):
        trial = json.loads(json.dumps(recipe))
        trial["name"] = out.stem
        trial["macros"]["height"] = macro
        targets = {**recipe.get("targets", {}), **{SLIDERS[k].replace("decr-incr", "incr" if v > 0 else "decr"): round(abs(v), 4) for k, v in values.items() if abs(v) > 1e-4}}  # MPFB's files are one-way, weights 0 to 1
        if stomach > 1e-4:
            targets[STOMACH] = round(stomach, 4)
        trial["targets"] = targets
        t = tape(trial, work, n)
        cm = {k: v["cm"] for k, v in t["measures"].items()}
        waist_hip = cm["waist"] / cm["hip"]
        shoulder_hip = cm["shoulder_width"] * proxies["bideltoid_over_biacromial"] / (cm["hip"] * proxies["hip_breadth_over_hip_girth"])
        history.append({"round": n, "height": cm["height"], "waist": cm["waist"], "hip": cm["hip"], "shoulder_width": cm["shoulder_width"], "waist_hip": waist_hip, "shoulder_hip": shoulder_hip, "sliders": dict(values), "stomach": stomach, "height_macro": macro})
        print(f"ronda {n}: altura {cm['height']:.1f}  cintura {cm['waist']:.1f}  quadril {cm['hip']:.1f}  ombro {cm['shoulder_width']:.1f}  c/q {waist_hip:.3f}  o/q {shoulder_hip:.3f}  barriga {stomach:.2f}")
        if previous is not None and abs(stomach - previous["stomach"]) > 0.02:
            # the belly's gain, from what the waist did beyond what the waist slider explains
            explained = effect("waist", values["waist"]) - effect("waist", previous["waist_slider"])
            stomach_gain = max(2.0, (cm["waist"] - previous["waist"] - explained) / (stomach - previous["stomach"]))
        if abs(cm["height"] - goals["height_cm"]) <= HEIGHT_TOLERANCE_CM and abs(waist_hip - goals["waist_hip"]) <= TOLERANCE and abs(shoulder_hip - goals["shoulder_hip"]) <= TOLERANCE:
            break
        previous = {"waist": cm["waist"], "stomach": stomach, "waist_slider": values["waist"]}
        macro = clip(macro + (goals["height_cm"] - cm["height"]) / 140.0, 0.0, 1.0)
        scale = cm["height"] / 159.1
        # every combination of the four, predicted from this round's real measures, and the one nearest both ratios kept
        best = None
        for w in grid:
            dw = (effect("waist", w) - effect("waist", values["waist"])) * scale
            for h in grid:
                H = cm["hip"] + (effect("hip", h) - effect("hip", values["hip"])) * scale
                for st in belly:
                    W = cm["waist"] + dw + (st - stomach) * stomach_gain * scale
                    e_wh = W / H - goals["waist_hip"]
                    for sh in grid:
                        S = cm["shoulder_width"] + (effect("shoulder_width", sh) - effect("shoulder_width", values["shoulder_width"])) * scale
                        e_sh = S * proxies["bideltoid_over_biacromial"] / (H * proxies["hip_breadth_over_hip_girth"]) - goals["shoulder_hip"]
                        cost = e_wh * e_wh + e_sh * e_sh + PENALTY * (w * w + h * h + sh * sh + st * st)
                        if best is None or cost < best[0]:
                            best = (cost, w, h, st, sh)
        _, values["waist"], values["hip"], stomach, values["shoulder_width"] = best
    best = history[-1]
    trial["name"] = out.stem
    out.write_text(json.dumps(trial, indent=1), encoding="utf-8")
    (work / "historico.json").write_text(json.dumps({"goals": goals, "rounds": history}, indent=1), encoding="utf-8")
    met = abs(best["waist_hip"] - goals["waist_hip"]) <= TOLERANCE and abs(best["shoulder_hip"] - goals["shoulder_hip"]) <= TOLERANCE
    print("atingiu as metas" if met else "não atingiu as metas dentro dos limites dos sliders", out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

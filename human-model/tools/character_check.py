"""One check on a character's body at rest, from a fast_review.py run with the character path: no bone through the skin, the proportions within the silhouette's ranges, the percentage reached. It warns and doesn't block. Pure, standard library; runs in WSL.
    python3 human-model/tools/character_check.py RUN_FOLDER NAME
Writes RUN_FOLDER/check.md."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from hmcore import character as ch  # noqa: E402


def _json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def ratios_of(measures, proxies):
    """The silhouette's three ratios from the tape's measures, in cm."""
    hip = measures["hip"]
    return {"waist_hip": measures["waist"] / hip, "bust_hip": measures["bust"] / hip,
            "shoulder_hip": measures["shoulder_width"] * proxies["bideltoid_over_biacromial"] / (hip * proxies["hip_breadth_over_hip_girth"])}


def warnings(character, measures, ratios_table, layers_report, skin_report):
    """A sentence per thing that isn't right; empty when all is well."""
    out = []
    if layers_report["bones_with_points_outside_skin"]:
        names = ", ".join(layers_report["bones_with_points_outside_skin"])
        out.append(f"Ossos passam pela pele em repouso: {names}.")
    if not skin_report["reached_within_0_5"]:
        out.append(f"Gordura {skin_report['percent']}%, pedido {skin_report['target_percent']}%: fora da tolerância.")
    if skin_report["triangles_turned_over"]:
        out.append(f"{skin_report['triangles_turned_over']} triângulos da pele viraram ao contrário.")
    if character.get("silhouette"):
        sex = character["sex"]
        limits = ratios_table[sex][character["silhouette"]]
        for key, value in ratios_of(measures, ratios_table["ansur_proxies"][sex]).items():
            bounds = limits.get(key)
            if bounds is None:
                continue
            lo, hi = bounds
            if (lo is not None and value < lo) or (hi is not None and value > hi):
                out.append(f"{key} {value:.3f} fora da faixa da silhueta {bounds}.")
    return out


def main(folder, name):
    run = _json(os.path.join(folder, "run.json"))
    stages = run["stages"]
    sheet = _json(stages["shape"]["output"]["sheet"])
    shape = _json(stages["shape"]["output"]["shape"])
    layers = _json(stages["layers"]["output"]["layers"][:-len(".npz")] + ".json")
    skin = _json(stages["outward"]["output"]["skin_report"])
    found = warnings(sheet["character"], shape["measures_cm"], ch.silhouette_ratios(), layers, skin)
    lines = [f"# Conferência de {name}", "", f"- Gordura: {skin['percent']}% (pedido {skin['target_percent']}%).", f"- Triângulos da pele virados: {skin['triangles_turned_over']}.",
             f"- Degrau nas junções (mm): {skin['ring_steps_mm']}.", f"- Ossos fora da pele em repouso: {len(layers['bones_with_points_outside_skin'])}.", ""]
    lines += [f"**Aviso:** {w}" for w in found] or ["Tudo certo."]
    with open(os.path.join(folder, "check.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main(*sys.argv[1:])

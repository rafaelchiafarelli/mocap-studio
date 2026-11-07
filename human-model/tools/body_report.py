"""The zero point: what the layered body is made of, measured (task muscle-physics/body-at-rest/2).
    hm.sh python human-model/tools/body_report.py LAYERS_DIR NAME TAPE.json OUT_DIR
LAYERS_DIR holds <NAME>.body_layers.npz and .json from tools/body_layers.py; TAPE.json is from blender/body_tape.py on the same recipe.
Writes OUT_DIR/10_section_<level>.png (crosswise, at each girth of the tape: seen from the feet, front at the top, the body's left on the right),
11_section_<cut>.png (lengthwise: the middle, and through the left leg; front on the left), 12_sections.png (all of them on one sheet),
and marco_zero.json and marco_zero.md (the table, in Portuguese for Rafael)."""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from hmcore import body

# Declared densities, kg/m3: tissue's usual values (general knowledge, not from a source read here). The cavity mixes the lungs' air with the organs
DENSITY = {"bone": 1500.0, "muscle": 1060.0, "fat": 900.0, "skin": 1100.0, "cavity": 900.0}
REAL_SKIN_MM = 1.5  # what real skin's thickness would be, against the voxels' band: the rest of the band counts as fat in the corrected share
COLORS = {-1: (235, 235, 235), body.BONE: (235, 225, 195), body.MUSCLE: (165, 40, 35), body.FAT: (245, 205, 85),
          body.SKIN: (215, 160, 135), body.CAVITY: (115, 145, 205)}
NAMES_PT = {"bone": "osso", "muscle": "músculo", "fat": "gordura", "skin": "pele (faixa)", "cavity": "cavidade (órgãos)"}
LEVELS = (("bust", "Busto"), ("underbust", "Abaixo do busto"), ("waist", "Cintura"), ("hip", "Quadril"), ("thigh", "Coxa"))
SCALE = 4  # pixels per voxel
# Blender's own Inter (SIL Open Font License), for the accents Pillow's built-in font lacks
FONT = "/mnt/g/mocap-studio-downloads/apps/blender/5.2.2/blender-5.2.2-windows-x64/5.2/datafiles/fonts/Inter.woff2"
# What an adult woman's body usually holds, as shares of mass. General knowledge, not from a source read here: a comparison, not a target
USUAL = {"fat": (0.25, 0.31), "muscle": (0.30, 0.36), "bone": (0.12, 0.15)}


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default(size=size)


def picture(labels2d, title, subtitle):
    """A slice as an image, with a 10 cm bar and a title."""
    h, w = labels2d.shape
    rgb = np.zeros((h, w, 3), np.uint8)
    for k, c in COLORS.items():
        rgb[labels2d == k] = c
    img = Image.fromarray(rgb).resize((w * SCALE, h * SCALE), Image.NEAREST)
    canvas = Image.new("RGB", (max(img.width + 40, 560), img.height + 110), (255, 255, 255))
    canvas.paste(img, (20, 70))
    d = ImageDraw.Draw(canvas)
    d.text((20, 10), title, fill=(0, 0, 0), font=font(24))
    d.text((20, 40), subtitle, fill=(80, 80, 80), font=font(16))
    bar = int(0.10 / 0.005 * SCALE)
    y = canvas.height - 25
    d.rectangle((20, y, 20 + bar, y + 6), fill=(0, 0, 0))
    d.text((25 + bar, y - 6), "10 cm", fill=(0, 0, 0), font=font(16))
    return canvas


def legend():
    img = Image.new("RGB", (300, 40 * len(body.LABELS) + 20), (255, 255, 255))
    d = ImageDraw.Draw(img)
    for i, (k, name) in enumerate(zip(range(len(body.LABELS)), body.LABELS)):
        d.rectangle((10, 15 + 40 * i, 40, 45 + 40 * i), fill=COLORS[k], outline=(0, 0, 0))
        d.text((55, 18 + 40 * i), NAMES_PT[name], fill=(0, 0, 0), font=font(20))
    return img


def sheet(images, columns=4):
    w = max(i.width for i in images)
    h = max(i.height for i in images)
    rows = -(-len(images) // columns)
    out = Image.new("RGB", (w * columns, h * rows), (255, 255, 255))
    for n, i in enumerate(images):
        out.paste(i, ((n % columns) * w, (n // columns) * h))
    return out


def main(layers_dir, name, tape_json, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    L = np.load(os.path.join(layers_dir, f"{name}.body_layers.npz"))
    built = json.load(open(os.path.join(layers_dir, f"{name}.body_layers.json")))
    tape = json.load(open(tape_json, encoding="utf-8"))
    shape, origin, h = L["shape"], L["origin"], float(L["h"])
    grid = L["labels_clean"].reshape(shape)

    pictures = []
    for key, label in LEVELS:
        z = tape["girth_z_m"][key]
        k = int(round((z - origin[2]) / h - 0.5))
        img = picture(grid[:, :, k].T, f"{label}: {tape['measures'][key]['cm']} cm", f"corte transversal a {z * 100:.1f} cm do chão")
        img.save(f"{out_dir}/10_section_{key}.png")
        pictures.append(img)
    skin = L["skin"][L["skin_ids"]]
    thigh = skin[(skin[:, 0] > 0.03) & (np.abs(skin[:, 2] - tape["girth_z_m"]["thigh"]) < 0.02)]
    for key, x, label in (("middle", 0.0, "Corte pelo meio do corpo"), ("left_leg", float(thigh[:, 0].mean()), "Corte pela perna esquerda")):
        i = int(round((x - origin[0]) / h - 0.5))
        img = picture(grid[i].T[::-1], label, f"longitudinal, a {x * 100:.1f} cm do meio; frente à esquerda")
        img.save(f"{out_dir}/11_section_{key}.png")
        pictures.append(img)
    pictures.append(legend())
    sheet(pictures).save(f"{out_dir}/12_sections.png")

    litres = built["litres"]
    mass = {k: litres[k] * DENSITY[k] / 1000 for k in body.LABELS}
    total = sum(mass.values())
    patch = L["patch"]
    v = L["skin"][patch]
    area = float(np.linalg.norm(np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]), axis=1).sum() / 2)
    band_mm = litres["skin"] / 1000 / area * 1000
    real_skin = area * REAL_SKIN_MM / 1000 * DENSITY["skin"]
    corrected_fat = mass["fat"] + (litres["skin"] / 1000 - area * REAL_SKIN_MM / 1000) * DENSITY["fat"]
    corrected_total = total - mass["skin"] + real_skin + (litres["skin"] / 1000 - area * REAL_SKIN_MM / 1000) * DENSITY["fat"]
    share = {k: mass[k] / total for k in body.LABELS}
    report = {"name": name, "densities_kg_m3": DENSITY, "litres": litres, "kg": {k: round(m, 2) for k, m in mass.items()}, "kg_total": round(total, 2),
              "share_of_mass": {k: round(s, 3) for k, s in share.items()},
              "skin_area_m2": round(area, 3), "skin_band_mean_mm": round(band_mm, 1),
              "fat_share_if_band_beyond_real_skin_is_fat": round(corrected_fat / corrected_total, 3), "real_skin_mm": REAL_SKIN_MM,
              "usual_adult_woman_share": USUAL, "fat_by_zone": built["fat"], "bones_with_points_outside_skin": built["bones_with_points_outside_skin"],
              "measures_cm": {k: v["cm"] for k, v in tape["measures"].items()}, "note": "Head, hands and feet are outside the layered body."}
    with open(f"{out_dir}/marco_zero.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=1, ensure_ascii=False)
    with open(f"{out_dir}/marco_zero.md", "w", encoding="utf-8") as f:
        f.write(markdown(report, tape))
    print(json.dumps({k: report[k] for k in ("kg", "kg_total", "share_of_mass", "skin_band_mean_mm", "fat_share_if_band_beyond_real_skin_is_fat")}, indent=1))


def markdown(r, tape):
    lines = [f"# Marco zero: {r['name']}", "", "Sem cabeça, mãos e pés. Densidades declaradas, não medidas.", "",
             "## Do que o corpo é feito", "", "| Tecido | Litros | kg | % da massa | Faixa usual numa mulher adulta |", "|---|---:|---:|---:|---|"]
    for k in body.LABELS:
        usual = r["usual_adult_woman_share"].get(k)
        lines.append(f"| {NAMES_PT[k]} | {r['litres'][k]} | {r['kg'][k]} | {r['share_of_mass'][k] * 100:.0f}% | "
                     f"{f'{usual[0] * 100:.0f}–{usual[1] * 100:.0f}%' if usual else '—'} |")
    lines += [f"| **total** | {sum(r['litres'].values()):.1f} | {r['kg_total']} | | |", "",
              f"A faixa de pele tem em média {r['skin_band_mean_mm']} mm, contra {r['real_skin_mm']} mm de pele real. "
              f"Contando o resto da faixa como gordura, a gordura é {r['fat_share_if_band_beyond_real_skin_is_fat'] * 100:.0f}% da massa.", "",
              "As faixas usuais são conhecimento geral, não de uma fonte lida aqui: servem de comparação, não de meta.", "",
              "## Gordura por zona (mm)", "", "| Zona | Declarada | Medida (mediana) | 10% a 90% |", "|---|---:|---:|---|"]
    for z, v in r["fat_by_zone"].items():
        lines.append(f"| {z} | {v['declared_mm']} | {v['median_mm']} | {v['p10_mm']} a {v['p90_mm']} |")
    lines += ["", "## Ossos que saem da pele, em repouso", "", "| Osso | Pontos fora | Mais fundo (mm) |", "|---|---:|---:|"]
    for b, v in r["bones_with_points_outside_skin"].items():
        lines.append(f"| {b} | {v['points_outside_skin']} | {v['deepest_mm']} |")
    lines += ["", "## Ficha de modelagem (cm)", "", "| Medida | cm |", "|---|---:|"]
    for k, v in tape["measures"].items():
        lines.append(f"| {v['label']} | {v['cm']} |")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main(*sys.argv[1:5])

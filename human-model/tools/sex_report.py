"""How male and female bodies differ, from data: python sex_report.py CT_STATS.json ANSUR_DIR. Prints a markdown table with effect sizes."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import measures


def row(label, m, f, unit, src):
    sm, sf = measures.summary(m), measures.summary(f)
    if sm["n"] < 5 or sf["n"] < 5:
        return f"| {label} | too few complete labels | | | | {src} |"
    pooled = np.sqrt((sm["sd"] ** 2 + sf["sd"] ** 2) / 2)
    d = (sm["mean"] - sf["mean"]) / pooled
    k = 1000 if unit == "mm" else (1000 if unit == "ml" else 1)
    return f"| {label} | {sm['mean']*k:.0f} ± {sm['sd']*k:.0f} {unit} ({sm['n']}) | {sf['mean']*k:.0f} ± {sf['sd']*k:.0f} {unit} ({sf['n']}) | {(sf['mean']/sm['mean']-1)*100:+.0f}% | {d:+.2f} | {src} |"


def main(ct_path, ansur_dir):
    ct = json.load(open(ct_path))
    a = {s: measures.ansur_rows(open(f"{ansur_dir}/ansur_ii_{n}.csv", encoding="latin1").read()) for s, n in (("m", "male"), ("f", "female"))}
    print("| Measure | Male (n) | Female (n) | Female vs male | Effect size d | Source |\n|---|---:|---:|---:|---:|---|")
    for label, col in (("Stature", "stature"), ("Biacromial breadth", "biacromialbreadth"), ("Bi-iliac breadth", "bicristalbreadth"), ("Hip breadth", "hipbreadth"), ("Bizygomatic breadth", "bizygomaticbreadth"), ("Head breadth", "headbreadth"), ("Head length", "headlength"), ("Sitting height", "sittingheight"), ("Hand length", "handlength"), ("Foot length", "footlength"), ("Forearm-hand length", "forearmhandlength")):
        print(row(label, [measures.ansur_value(r, col) for r in a["m"]], [measures.ansur_value(r, col) for r in a["f"]], "mm", "ANSUR II"))
    for label, key, unit in (("Bi-iliac width, bone", "pelvis_width", "mm"), ("Pelvis height, bone", "pelvis_height", "mm"), ("Pelvis depth, bone", "pelvis_depth", "mm"), ("Sacrum width", "sacrum_width", "mm"), ("Sacrum height", "sacrum_height", "mm"), ("Clavicle length", "clavicle_len", "mm"), ("Scapula length", "scapula_len", "mm"), ("Hip bone volume", "hip_vol", "ml"), ("L3 vertebra volume", "vertebrae_L3_vol", "ml"), ("T6 vertebra volume", "vertebrae_T6_vol", "ml"), ("Gluteus medius volume", "gluteus_medius_left_vol", "ml"), ("Iliopsoas volume", "iliopsoas_left_vol", "ml")):
        print(row(label, measures.complete_values(list(ct["m"].values()), key), measures.complete_values(list(ct["f"].values()), key), unit, "CT sample"))


if __name__ == "__main__":
    main(*sys.argv[1:])

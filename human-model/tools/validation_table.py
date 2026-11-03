"""Prints the measurement validation tables: python validation_table.py Z_ANATOMY.json CT_STATS.json ANSUR_DIR"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import measures


def main(za_path, ct_path, ansur_dir):
    za = json.load(open(za_path))
    ct = json.load(open(ct_path))
    ansur = {s: measures.ansur_rows(open(f"{ansur_dir}/ansur_ii_{n}.csv", encoding="latin1").read()) for s, n in (("m", "male"), ("f", "female"))}
    ext = lambda k, i: za[k]["max"][i] - za[k]["min"][i]
    top = max(za[k]["max"][2] for k in ("Parietal bone.l", "Parietal bone.r", "Frontal bone"))
    rows = [
        ("Stature, bone to bone (skin adds about 2 cm)", top - za["Calcaneus.l"]["min"][2], "stature", "ANSUR"),
        ("Biacromial breadth (scapula to scapula)", za["Scapula.l"]["max"][0] - za["Scapula.r"]["min"][0], "biacromialbreadth", "ANSUR"),
        ("Bi-iliac breadth", za["Hip bone.l"]["max"][0] - za["Hip bone.r"]["min"][0], "bicristalbreadth", "ANSUR"),
        ("Bizygomatic breadth (bone; skin adds about 1 cm)", za["Zygomatic bone.l"]["max"][0] - za["Zygomatic bone.r"]["min"][0], "bizygomaticbreadth", "ANSUR"),
    ]
    print("| Measurement | Z-Anatomy | Source mean ± SD (male) | n | z | Source |\n|---|---:|---:|---:|---:|---|")
    for label, value, col, src in rows:
        st = measures.summary([measures.ansur_value(r, col) for r in ansur["m"]])
        print(f"| {label} | {value*1000:.0f} mm | {st['mean']*1000:.0f} ± {st['sd']*1000:.0f} mm | {st['n']} | {measures.z_score(value, st):+.1f} | ANSUR II `{col}` |")
    lens = [
        ("Humerus length", za["Humerus.l"]["length"], ["humerus_len_left", "humerus_len_right"]),
        ("Bi-iliac width", za["Hip bone.l"]["max"][0] - za["Hip bone.r"]["min"][0], ["pelvis_width"]),
        ("Pelvis height", za["Hip bone.l"]["max"][2] - za["Hip bone.l"]["min"][2], ["pelvis_height"]),
        ("Sacrum width", ext("Sacrum", 0), ["sacrum_width"]),
        ("Clavicle length", za["Clavicle.l"]["length"], ["clavicle_len"]),
        ("Scapula length", za["Scapula.l"]["length"], ["scapula_len"]),
    ]
    for label, value, keys in lens:
        vals = [x for k in keys for x in measures.complete_values(list(ct["m"].values()), k)]
        st = measures.summary(vals)
        if st["n"] < 5:
            print(f"| {label} | {value*1000:.0f} mm | too few complete labels | {st['n']} | — | TotalSegmentator CT |")
            continue
        print(f"| {label} | {value*1000:.0f} mm | {st['mean']*1000:.0f} ± {st['sd']*1000:.0f} mm | {st['n']} | {measures.z_score(value, st):+.1f} | TotalSegmentator CT, uncut labels |")


if __name__ == "__main__":
    main(*sys.argv[1:])

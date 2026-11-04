"""Per-subject measurements from the pulled CT labels: python ct_stats.py DATA_DIR OUT.json"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import ctbones, measures, tsdata


def load(d, s, l):
    p = f"{d}/{s}/segmentations/{l}.nii.gz"
    return ctbones.load_label(p) if os.path.exists(p) else (None, None)


def subject(d, s):
    r = {}
    for side in ("left", "right"):
        m, a = load(d, s, f"humerus_{side}")
        if m is not None:
            r[f"humerus_len_{side}"] = measures.long_bone_length_m(m, a)
    hl, a = load(d, s, "hip_left")
    hr, _ = load(d, s, "hip_right")
    if hl is not None and hr is not None and hl.any() and hr.any():
        both = hl | hr
        if not ctbones.touches_scan_edge(both):
            e = measures.bbox_extent_m(both, a)
            r["pelvis_width"], r["pelvis_depth"], r["pelvis_height"] = float(e[0]), float(e[1]), float(e[2])
            r["hip_vol"] = measures.label_volume_l(hl, a)
    sa, a2 = load(d, s, "sacrum")
    if sa is not None and sa.any() and not ctbones.touches_scan_edge(sa):
        e = measures.bbox_extent_m(sa, a2)
        r["sacrum_width"], r["sacrum_height"] = float(e[0]), float(e[2])
    sk, a3 = load(d, s, "skull")
    if sk is not None and sk.any() and not ctbones.touches_scan_edge(sk):
        e = measures.bbox_extent_m(sk, a3)
        r["skull_width"], r["skull_depth"], r["skull_height"] = float(e[0]), float(e[1]), float(e[2])
        r["skull_vol"] = measures.label_volume_l(sk, a3)
    for l, key in (("scapula_left", "scapula"), ("clavicula_left", "clavicle")):
        m, a4 = load(d, s, l)
        if m is not None and m.any() and not ctbones.touches_scan_edge(m):
            r[f"{key}_len"] = measures.long_bone_length_m(m, a4)
    for l in ("vertebrae_L3", "vertebrae_T6", "gluteus_maximus_left", "gluteus_medius_left", "iliopsoas_left", "autochthon_left"):
        m, a5 = load(d, s, l)
        if m is not None and m.any() and not ctbones.touches_scan_edge(m):
            r[f"{l}_vol"] = measures.label_volume_l(m, a5)
    return r


def main(d, out):
    meta = {r["image_id"]: r for r in tsdata.read_meta(open(f"{d}/meta.csv", encoding="utf-8-sig").read())}
    chosen = json.load(open(f"{d}/sample.json"))
    rows = {"m": {}, "f": {}}
    for sex, ids in chosen.items():
        for s in ids:
            if os.path.isdir(f"{d}/{s}"):
                rows[sex][s] = {"age": meta[s]["age"], **subject(d, s)}
    json.dump(rows, open(out, "w"), indent=0)
    for sex in rows:
        print(sex, len(rows[sex]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])

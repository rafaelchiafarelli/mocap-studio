"""The TotalSegmentator CT dataset (CC BY 4.0): subject metadata, coverage from the zip index, and label volumes."""
import csv, gzip, io
URL = "https://zenodo.org/records/10047292/files/Totalsegmentator_dataset_v201.zip"
AXIAL = ["skull", "sacrum", "sternum", "costal_cartilages"]
AXIAL += [f"vertebrae_{n}" for n in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "L1", "L2", "L3", "L4", "L5"]]
AXIAL += [f"vertebrae_T{i}" for i in range(1, 13)]
PAIRED = ["humerus", "scapula", "clavicula", "hip", "femur"] + [f"rib_{{}}_{i}" for i in range(1, 13)]
MUSCLES = ["gluteus_maximus", "gluteus_medius", "gluteus_minimus", "iliopsoas", "autochthon"]
# A label that's empty or barely there compresses to almost nothing, so the index alone says what a scan covers.
MIN_BYTES = {"skull": 60000, "femur": 40000, "humerus": 15000, "hip": 25000, "sacrum": 8000}


def paired(stem):
    if "{}" in stem:
        return [stem.format("left"), stem.format("right")]
    return [f"{stem}_left", f"{stem}_right"]


def bone_labels():
    names = list(AXIAL)
    for stem in PAIRED:
        names += paired(stem)
    return names


def read_meta(text):
    """Rows of meta.csv as dicts. The file is semicolon-separated with a BOM."""
    rows = list(csv.DictReader(io.StringIO(text.lstrip("﻿")), delimiter=";"))
    for r in rows:
        r["age"] = float(r["age"]) if r["age"] else None
    return rows


def coverage(infolist):
    """{subject: {label: compressed bytes}} from a zip's member list."""
    out = {}
    for i in infolist:
        parts = i.filename.split("/")
        if len(parts) == 3 and parts[1] == "segmentations" and parts[2].endswith(".nii.gz"):
            out.setdefault(parts[0], {})[parts[2][:-7]] = i.compress_size
    return out


def whole_body_score(sizes):
    """How many required bones the scan holds in full, and the sum of bytes as a tie-break. 0 means a required part is cut."""
    for stem, need in MIN_BYTES.items():
        for name in ([stem] if stem in ("skull", "sacrum") else paired(stem)):
            if sizes.get(name, 0) < need:
                return 0
    return sum(sizes.get(n, 0) for n in bone_labels())


def pick_donors(meta, cov, sex, age=(25, 50), n=5):
    """The most complete scans of one sex, without recorded pathology. Coverage is only a filter: a person checks the result."""
    rows = [r for r in meta if r["gender"] == sex and r["age"] and age[0] <= r["age"] <= age[1] and r["pathology"] == "no_pathology"]
    scored = [(whole_body_score(cov.get(r["image_id"], {})), r["image_id"]) for r in rows]
    return [s for s in sorted(scored, reverse=True) if s[0] > 0][:n]

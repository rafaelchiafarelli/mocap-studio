"""Mean walking cycle per sex from Fukuchi 2018's time-normalized joint angles (CC BY 4.0)."""
import csv, io, zipfile
import numpy as np


def info_rows(text):
    return list(csv.DictReader(io.StringIO(text)))


def subjects_by_sex(rows, group="Young"):
    """{subject number: sex} of one age group, read from the static trial's row."""
    out = {}
    for r in rows:
        if r["AgeGroup"] == group and r["Gender"] in ("M", "F"):
            out[int(r["Subject"])] = r["Gender"]
    return out


def read_angles(text):
    lines = text.strip().splitlines()
    names = lines[0].split("\t")
    data = np.array([[float(x) if x not in ("", "NaN") else np.nan for x in l.split("\t")] for l in lines[1:]])
    return names, data


def mean_cycle(tables):
    """Per-column mean across subjects. Tables are time-normalized to 101 rows."""
    stack = np.stack(tables)
    return np.nanmean(stack, axis=0), np.nanstd(stack, axis=0)


def build(zip_path, info_text, trial="T05"):
    rows = info_rows(info_text)
    sex = subjects_by_sex(rows)
    z = zipfile.ZipFile(zip_path)
    groups = {"M": [], "F": []}
    names = None
    for subject, s in sorted(sex.items()):
        member = f"51subjs/WBDS{subject:02d}walk{trial}ang.txt"
        if member in z.namelist():
            names, data = read_angles(z.read(member).decode())
            if data.shape[0] == 101 and not np.isnan(data).mean() > 0.2:
                groups[s].append(data)
    out = {}
    for s, tables in groups.items():
        mean, sd = mean_cycle(tables)
        out[s] = {"n": len(tables), "columns": names, "mean": mean, "sd": sd}
    return out

"""Writes data/gait_walk.json from the Fukuchi archive: python make_gait_table.py FUKUCHI_DIR OUT.json. Both sexes, trial T05. Derived from CC BY 4.0 data; see ATTRIBUTION.md."""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import gait

KEEP = [c for side in "RL" for c in (f"{side}PelvisAngleX", f"{side}PelvisAngleY", f"{side}PelvisAngleZ", f"{side}HipAngleX", f"{side}HipAngleZ", f"{side}KneeAngleZ", f"{side}AnkleAngleZ")]
CYCLE_S = 1.1  # declared: the ascii files are normalized in time, so this sets pace only; checked through the speed it gives


def main(d, out):
    g = gait.build(f"{d}/WBDSascii.zip", open(f"{d}/WBDSinfo.csv", encoding="latin1").read())
    table = {}
    for s, name in (("M", "male"), ("F", "female")):
        cols = g[s]["columns"]
        idx = [cols.index(c) for c in KEEP]
        table[name] = {"n": g[s]["n"], "cycle_s": CYCLE_S, "columns": KEEP, "mean": np.round(g[s]["mean"][:, idx], 3).tolist(), "sd": np.round(g[s]["sd"][:, idx], 3).tolist()}
    json.dump(table, open(out, "w"))
    print({k: v["n"] for k, v in table.items()})


if __name__ == "__main__":
    main(*sys.argv[1:])

"""The muscle list of one individual: python build_muscles.py EXPORT.npz EXPORT.json BONES.npz OUT.json SEX"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import bonelib, muscle, skeleton

HERE = os.path.dirname(os.path.abspath(__file__))


def follow_rig_edits(rig, edits):
    """The joints as the bones moved them, so a muscle's ends land on its bones: each edited bone's head, and its parent's tail where they meet."""
    for name, head in edits.items():
        if rig[name]["head"] != head:
            parent = rig[name]["parent"]
            if parent in rig and rig[parent]["tail"] == rig[name]["head"]:
                rig[parent]["tail"] = head
            rig[name]["head"] = head


def main(npz, js, bones_npz, out, sex):
    ind = skeleton.load_individual(npz, js)
    b = np.load(bones_npz)
    meta = json.load(open(bones_npz + ".json"))
    bones = {n: {"verts": b[f"{n}__v"], "parent": m["parent"]} for n, m in meta["bones"].items()}
    table = json.load(open(os.path.join(HERE, "..", "data", "muscles.json")))
    edits = meta["anchors"]["rig_edits"]
    follow_rig_edits(ind["rig"], edits)
    ms = muscle.build_table(ind, bones, table)
    ms += muscle.rajagopal_muscles(ind, bones, f"{bonelib.RAJ}/Rajagopal2016.osim", {"L": edits["thigh.L"], "R": edits["thigh.R"]})
    json.dump(ms, open(out, "w"), indent=0)
    print("muscles", len(ms), {g: sum(1 for m in ms if m["group"] == g) for g in {m["group"] for m in ms}})


if __name__ == "__main__":
    main(*sys.argv[1:])

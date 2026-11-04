"""Adds jaw and joint tables to a fitted skeleton's metadata: python spec.py BONES.npz SEX"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import jaw, joints


def main(path, sex):
    meta = json.load(open(path + ".json"))
    a = meta["anchors"]
    condyle = (np.array(a["condyle_L"]) + np.array(a["condyle_R"])) / 2
    meta["jaw"] = jaw.table(condyle, a["lower_incisor"])
    meta["limits"] = joints.limits(sex)
    json.dump(meta, open(path + ".json", "w"), indent=0)
    print("jaw", round(np.degrees(meta["jaw"]["final_rad"]), 1), "deg, incisor back", round(jaw.incisor_back_motion(meta["jaw"], condyle, a["lower_incisor"]) * 1000, 1), "mm")


if __name__ == "__main__":
    main(*sys.argv[1:])

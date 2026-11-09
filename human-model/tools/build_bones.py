"""Builds the fitted skeleton of one individual: python build_bones.py SEX EXPORT.npz EXPORT.json OUT.npz [CACHE_DIR] [TARGETS.json]
TARGETS.json (hmcore.bone_targets) sizes the bones from measures instead of reading the skin."""
import json, os, pickle, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import bonelib, skeleton


def library(sex, cache):
    p = os.path.join(cache, f"ct_library_{sex}.pkl")
    if os.path.exists(p):
        return pickle.load(open(p, "rb"))
    lib = bonelib.ct_library(sex)
    hips = bonelib.femur_head_centres(sex)
    pickle.dump((lib, hips), open(p, "wb"))
    return lib, hips


def main(sex, npz, js, out, cache="/tmp", targets_json=None):
    ind = skeleton.load_individual(npz, js)
    lib, hips = library(sex, cache)
    legs, anchors = bonelib.bmf_library()
    bones, a = skeleton.build(ind, lib, legs, anchors, bonelib.rajagopal_arm("r"), bonelib.rajagopal_arm("l"), hips, targets=json.load(open(targets_json)) if targets_json else None)
    skeleton.save(out, bones, a)
    c = skeleton.containment(bones, ind)
    bad = {k: round(v, 2) for k, v in sorted(c.items(), key=lambda kv: -kv[1]) if v > 0.02}
    print("bones", len(bones), "vertices", sum(len(b["verts"]) for b in bones.values()))
    print("outside skin:", json.dumps(bad))
    json.dump(c, open(out + ".containment.json", "w"), indent=0)


if __name__ == "__main__":
    main(*sys.argv[1:])

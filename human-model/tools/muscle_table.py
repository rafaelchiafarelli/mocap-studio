"""How thick the muscle is per zone on a body in layers, from the bones and the trunk's hull to where the fat starts, for data/muscle_mm_<sex>.json.
    hm.sh python human-model/tools/muscle_table.py LAYERS.npz BONES.npz SEX OUT.json
Reads an existing body in layers; computes no body."""
import json, os, sys
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from hmcore import body, layers, outward

SPLIT = {"breast": body.BREAST_ZONES, "buttocks": body.GLUTEUS_ZONES}


def per_zone(depths, zones):
    """{zone: median mm} per zone with points, the old undivided zones written as their new parts."""
    out = {}
    for z in np.unique(zones):
        value = round(float(np.median(depths[zones == z])) * 1000, 1)
        for name in SPLIT.get(z, (z,)):
            out[name] = value
    return out


def main(layers_npz, bones_npz, sex, out):
    L, B = np.load(layers_npz), np.load(bones_npz)
    shape, origin, h = L["shape"], L["origin"].astype(float), float(L["h"])
    idx = np.indices(shape).reshape(3, -1).T
    centres = origin + (idx + 0.5) * h
    labels = L["labels_clean"]
    bones = {k[:-3]: B[k].astype(float) for k in B.files if k.endswith("__v")}
    core = outward.core_mask(centres, np.concatenate([bones[b] for b in body.TRUNK_BONES]), labels == body.BONE).reshape(shape)
    d = ndimage.distance_transform_edt(~core) * h
    ids, skin, thick = L["skin_ids"], L["skin"].astype(float), L["thickness"].astype(float)
    at = ((skin[ids] - origin) / h - 0.5).T
    depth = ndimage.map_coordinates(d, at, order=1) - thick[ids]
    table = per_zone(np.maximum(depth, 0.0), L["zone"][ids].astype(str))
    with open(out, "w") as f:
        json.dump({"_about": f"Muscle thickness per zone, mm, from the bones and the trunk's cavity to where the fat starts: the neutral {sex} body in layers (tools/muscle_table.py on {os.path.basename(layers_npz)}). A character's biotype scales it. Edit to change it.", "muscle_mm": table}, f, indent=1)
    print(sex, table)


if __name__ == "__main__":
    main(*sys.argv[1:])

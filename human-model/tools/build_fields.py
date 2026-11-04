"""Soft-tissue fields of one individual: python build_fields.py EXPORT.npz EXPORT.json BONES.npz MUSCLES.json OUT.npz"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import numpy as np
from hmcore import skeleton, softtissue, bodyskin


def main(npz, js, bones_npz, muscles_json, out):
    ind = skeleton.load_individual(npz, js)
    b = np.load(bones_npz)
    meta = json.load(open(bones_npz + ".json"))
    bones = {n: {"verts": b[f"{n}__v"], "parent": m["parent"]} for n, m in meta["bones"].items()}
    ms = json.load(open(muscles_json))
    region, fields = softtissue.build_fields(ind, bones, ms)
    arrays = {f"F_{k}": v.astype(np.float32) for k, v in fields.items()}
    arrays["ids"] = region.ids
    for name, (ids, disp) in bodyskin.shapes(ind, bones, ms, meta).items():
        arrays[f"B_{name}__ids"] = ids
        arrays[f"B_{name}__d"] = disp.astype(np.float32)
    np.savez_compressed(out, **arrays)
    rows = {k: round(softtissue.peak_mm(v), 1) for k, v in fields.items() if k.endswith("_L")}
    print("fields", len(fields), json.dumps(rows))


if __name__ == "__main__":
    main(*sys.argv[1:])

"""What the neutral bodies' bones measure as built today, from a build folder, in metres: pelvis width, trunk length, the ribs' and shoulders' width and depth, the limbs' lengths, and the same as shares of the height.
    hm.sh python human-model/tools/bone_neutral.py BUILD_DIR NAME [OUT.json]
Read to set data/bone_proportions.json and for the comparison table in docs/skeleton.md."""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def measure(bones, rig, skin):
    """bones: {name: vertices}. rig: {name: {head, tail}}. skin: the build's skin vertices."""
    head = lambda n: np.asarray(rig[n]["head"], float)
    tail = lambda n: np.asarray(rig[n]["tail"], float)
    H = float(skin[:, 2].max() - skin[:, 2].min())
    hips = (bones["hip_L"], bones["hip_R"])
    hips_all = np.vstack(hips)
    ribs = np.vstack([v for k, v in bones.items() if k.startswith("rib_")])
    scap = {s: bones[f"scapula_{s}"] for s in "LR"}
    hip_joint = (head("thigh.L") + head("thigh.R")) / 2
    d = {"height_m": H,
         "pelvis_width_m": float(np.ptp(hips_all[:, 0])),
         "trunk_length_m": float(bones["vertebra_C1"].mean(axis=0)[2] - hip_joint[2]),
         "biacromial_m": float(scap["L"][:, 0].max() - scap["R"][:, 0].min()),
         "ribcage_width_m": float(np.ptp(ribs[:, 0])), "ribcage_depth_m": float(np.ptp(ribs[:, 1])),
         "thigh_m": float(np.linalg.norm(tail("thigh.L") - head("thigh.L"))), "shin_m": float(np.linalg.norm(tail("shin.L") - head("shin.L"))),
         "humerus_m": float(np.linalg.norm(tail("upper_arm.L") - head("upper_arm.L"))), "forearm_m": float(np.linalg.norm(tail("forearm.L") - head("forearm.L"))),
         "humerus_width_m": float(np.ptp(bones["humerus_L"][:, 0])), "femur_width_m": float(np.ptp(bones["femur_L"][:, 0]))}
    return d


def main(build_dir, name, out=None):
    B = np.load(f"{build_dir}/{name}.bones.npz")
    bones = {k[:-3]: B[k].astype(float) for k in B.files if k.endswith("__v")}
    e = np.load(f"{build_dir}/{name}.export.npz")
    meta = json.load(open(f"{build_dir}/{name}.export.json"))
    d = measure(bones, meta["bones"], e["verts"][:13380].astype(float))
    print(json.dumps(d, indent=1))
    if out:
        json.dump(d, open(out, "w"), indent=1)


if __name__ == "__main__":
    main(*sys.argv[1:])

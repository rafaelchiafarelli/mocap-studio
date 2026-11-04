"""The bone library of one sex, in the model's frame, before fitting to an individual: CT labels for the trunk, skull and upper arm; BMF for the legs and feet; Rajagopal for forearm and hand."""
import os
import numpy as np
from hmcore import ctbones, sources

ROOT = "/mnt/g/mocap-studio-downloads/models"
TS = f"{ROOT}/totalsegmentator-ct-v2.0.1"
BMF = f"{ROOT}/bmf-toolkit/src/data/model_Original.mat"
RAJ = f"{ROOT}/rajagopal-2016"
# Donors: the most complete scans with intact long bones among the sexes' candidates. Age and pathology are in meta.csv.
DONORS = {"male": "s1045", "female": "s0933"}
CT_LABELS = [f"vertebrae_{n}" for n in ["C1", "C2", "C3", "C4", "C5", "C6", "C7"] + [f"T{i}" for i in range(1, 13)] + ["L1", "L2", "L3", "L4", "L5"]]
CT_LABELS += ["sacrum", "sternum", "costal_cartilages", "hip_left", "hip_right", "scapula_left", "scapula_right", "clavicula_left", "clavicula_right", "humerus_left", "humerus_right"]
CT_LABELS += [f"rib_{s}_{i}" for s in ("left", "right") for i in range(1, 13)]



def ct_bone(sex, label):
    mask, affine = ctbones.load_label(f"{TS}/{DONORS[sex]}/segmentations/{label}.nii.gz")
    if not mask.any():
        raise ValueError(f"{DONORS[sex]} has no {label}")
    # The cartilages are several separate pieces; every other label is one bone with stray voxels.
    return ctbones.mask_to_mesh(mask if label == "costal_cartilages" else ctbones.largest_component(mask), affine)


def femur_head_centres(sex):
    """Femoral head centres from the CT femurs, which are cut below the hip but keep the head. A scan isn't centred on x=0, so medial means towards the midpoint of the two femurs."""
    tops = {}
    for side in ("left", "right"):
        mask, affine = ctbones.load_label(f"{TS}/{DONORS[sex]}/segmentations/femur_{side}.nii.gz")
        v, _ = ctbones.mask_to_mesh(ctbones.largest_component(mask), affine, sigma=0.5)
        tops[side] = v[v[:, 2] > v[:, 2].max() - 0.035]
    mid = (tops["left"][:, 0].mean() + tops["right"][:, 0].mean()) / 2
    out = {}
    for side, top in tops.items():
        out[side] = top[np.argsort(np.abs(top[:, 0] - mid))[: max(50, len(top) // 3)]].mean(axis=0)
    return out


def ct_library(sex):
    lib = {}
    for label in CT_LABELS:
        lib[label] = ct_bone(sex, label)
    mask, affine = ctbones.load_label(f"{TS}/{DONORS[sex]}/segmentations/skull.nii.gz")
    cranium, jaw = ctbones.split_mandible(mask)
    if jaw is None:
        raise ValueError(f"{DONORS[sex]}: mandible not found")
    lib["cranium"] = ctbones.mask_to_mesh(ctbones.largest_component(cranium), affine)
    lib["mandible"] = ctbones.mask_to_mesh(ctbones.largest_component(jaw), affine)
    return lib


def bmf_library():
    """Lower limb, one set for both sexes, as joints and meshes in the model's frame."""
    bones = sources.bmf_bones(BMF)
    out, anchors = {}, {}
    for name, b in bones.items():
        out[name] = (sources.bmf_to_model(b["verts"]).astype(np.float32), b["faces"].astype(np.int32))
    for side, long in (("L", "left"), ("R", "right")):
        pelvis = sources.bmf_to_model(bones[f"Pelvis{side}"]["verts"])
        femur = sources.bmf_to_model(bones[f"Femur{side}"]["verts"])
        anchors[f"hip_{side}"] = pelvis[bones[f"Pelvis{side}"]["socket"]].mean(axis=0)
        anchors[f"knee_{side}"] = femur[bones[f"Femur{side}"]["condyles"]].mean(axis=0)
        anchors[f"ankle_{side}"] = sources.bmf_to_model(bones[f"Talus{side}"]["verts"]).mean(axis=0)
    return out, anchors


def rajagopal_arm(side):
    """Forearm and hand of one side, in the model's frame, assembled through the model's joints. side is 'r' or 'l'."""
    joints = sources.osim_joints(f"{RAJ}/Rajagopal2016.osim")
    bodies, _ = sources.osim_bodies(f"{RAJ}/Rajagopal2016.osim")
    origin = {f"ulna_{side}": np.zeros(3)}
    origin[f"radius_{side}"] = np.array(joints[f"radius_{side}"][1])
    origin[f"hand_{side}"] = origin[f"radius_{side}"] + np.array(joints[f"hand_{side}"][1])
    out = {}
    for body in (f"ulna_{side}", f"radius_{side}", f"hand_{side}"):
        for mesh in bodies[body]:
            v, f = sources.read_vtp(f"{RAJ}/Geometry/{mesh}")
            out[mesh.split(".")[0]] = (sources.opensim_to_model(v + origin[body]).astype(np.float32), f)
    wrist = sources.opensim_to_model(origin[f"hand_{side}"][None])[0]
    return out, np.zeros(3), wrist

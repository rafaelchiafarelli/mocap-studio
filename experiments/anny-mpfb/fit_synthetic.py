"""Test 3: can the fit recover a known MPFB body from silhouettes and 2D joints?
    experiments/anny-mpfb/run.sh python experiments/anny-mpfb/fit_synthetic.py OUT_DIR [seed=0] [views=0,90,180] [poses=2] [steps=600]
A random body (macros in 0.15..0.85, a few body targets up to +-0.6) is posed with random limb rotations and seen from each view
(yaw) in each pose; its masks and joints are the input. The fit starts from MPFB's default body at rest and doesn't know the poses.
Reports the error of the recovered body at rest, against the truth at rest, with and without the local targets."""
import json, os, sys, time
import numpy as np
import torch
sys.path.insert(0, "experiments/anny-mpfb")
import mpfb_anny
import fit as F

args = dict(a.split("=", 1) for a in sys.argv[2:])
out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)
seed = int(args.get("seed", 0))
views = [float(v) for v in args.get("views", "0,90,180").split(",")]
n_poses = int(args.get("poses", 2))
steps = int(args.get("steps", 600))
rng = np.random.default_rng(seed)
mpfb_anny.CUTOFF = 0.0
dev = "cuda"
m = mpfb_anny.model(dtype=torch.float32, device=dev)
labels = list(m.local_change_labels)
missing = [j for j in F.JOINTS if j not in list(m.bone_labels)]
if missing:
    raise SystemExit(f"bones not in the rig: {missing}; some: {[b for b in m.bone_labels if 'arm' in b or 'neck' in b or 'head' in b][:30]}")

# The truth
body_words = ("measure-", "hip-", "torso-", "upperarm-", "lowerarm-", "upperleg", "lowerleg", "buttocks-", "stomach-", "breast-", "neck-")
body_locals = [i for i, l in enumerate(labels) if l.startswith(body_words) and "pregnant" not in l]
truth_mac = {k: float(rng.uniform(0.15, 0.85)) for k in m.phenotype_labels}
SHARED = args.get("shared", "0") == "1"  # the views of one pose share it in the fit, as calibrated cameras would
FEMALE = args.get("female", "0") == "1"
if FEMALE:  # an adult woman: gender 0 and age 0.5..0.75 (MPFB's 25 to about 55 years), known to the fit
    truth_mac["gender"] = 0.0
    truth_mac["age"] = float(rng.uniform(0.5, 0.75))
for r in mpfb_anny.RACES:
    truth_mac[r] = 1 / 3
truth_loc = torch.zeros(len(labels), device=dev)
for i in rng.choice(body_locals, size=8, replace=False):
    truth_loc[i] = float(rng.uniform(-0.6, 0.6))
truth = F.Shape(m, 1, macros=torch.tensor([truth_mac[k] for k in m.phenotype_labels], device=dev), locals_=truth_loc)

# Poses: random limb rotations, plus the rest pose first
limb = [list(m.bone_labels).index(b) for b in ("upperleg01.L", "upperleg01.R", "lowerleg01.L", "lowerleg01.R", "upperarm01.L", "upperarm01.R", "lowerarm01.L", "lowerarm01.R")]
poses = [torch.zeros(m.bone_count, 3, device=dev)]
for p in range(n_poses - 1):
    r = torch.zeros(m.bone_count, 3, device=dev)
    r[limb] = torch.tensor(rng.normal(0, 0.25, (len(limb), 3)), dtype=torch.float32, device=dev)
    poses.append(r)

cam = F.Camera(f=7000.0, dist=10.0)
faces = [f for f in m.faces.tolist() if max(f) < F.N_BODY]
frames, frame_info = [], []
jidx = F.joint_index(m)
with torch.no_grad():
    for pi, rot in enumerate(poses):
        t1 = F.Shape(m, 1, macros=truth.effective().detach(), locals_=truth.locals_.data)
        t1.rot.data[0] = rot
        v, h = t1()
        for yaw in views:
            y = torch.tensor([yaw], device=dev)
            uv = cam.project(v[:, :F.N_BODY], y, t1.shift)
            juv = cam.project(h[:, jidx], y, t1.shift)
            mask = F.masks_from_vertices(uv.cpu().numpy(), faces, (cam.w, cam.h))[0]
            frames.append({"yaw": yaw, "mask": mask, "joints": juv[0].cpu().numpy(), **({"pose": pi} if SHARED else {})})
            frame_info.append({"pose": pi, "yaw": yaw, "mask_px": int(mask.sum())})
    rest_truth = truth()[0][0, :F.N_BODY]


def score(shape):
    with torch.no_grad():
        s = F.Shape(m, 1, macros=shape.effective().detach(), locals_=shape.locals_.data)
        v = s()[0][0, :F.N_BODY]
        d = v - rest_truth
        d = d - d.mean(0)
        e = d.norm(dim=1)
        z = rest_truth[:, 2]
        trunk = (z > z.min() + 0.45 * (z.max() - z.min())) & (z < z.min() + 0.8 * (z.max() - z.min())) & (rest_truth[:, 0].abs() < 0.2)
        return {"trunk_mean_mm": round(float(e[trunk].mean()) * 1000, 2), "mean_mm": round(float(e.mean()) * 1000, 2), "p95_mm": round(float(e.quantile(0.95)) * 1000, 2), "max_mm": round(float(e.max()) * 1000, 2),
                "height_err_mm": round(float(np.ptp(v[:, 2].cpu().numpy()) - np.ptp(rest_truth[:, 2].cpu().numpy())) * 1000, 2)}


report = {"seed": seed, "views": views, "poses": n_poses, "frames": frame_info, "truth": truth.recipe()}
start = F.Shape(m, 1)
report["start_error"] = score(start)
print("start", report["start_error"])
body_mask = F.body_local_mask(m)
report["body_locals"] = int(body_mask.sum())
for name, fl, lm in (("macros_only", False, None), ("macros_and_locals", True, None), ("macros_and_body_locals", True, body_mask)):
    t = time.time()
    s = F.fit(m, cam, frames, steps=steps, fit_locals=fl, local_mask=lm, fixed={"gender": 0.0, "age": truth_mac["age"]} if FEMALE else None, log=lambda r: print(name, r))
    report[name] = {"seconds": round(time.time() - t, 1), "error": score(s), "recipe": s.recipe(), "history": s.history,
                    "macro_error": {k: round(float(s.effective()[i]) - truth_mac[k], 3) for i, k in enumerate(m.phenotype_labels)}}
    print(name, report[name]["seconds"], "s", report[name]["error"])
json.dump(report, open(os.path.join(out_dir, f"synthetic_seed{seed}.json"), "w"), indent=1)

"""Fits an MPFB body to one runway model's frames (extract_frames.py's output).
    experiments/anny-mpfb/run.sh python experiments/anny-mpfb/fit_video.py FRAMES_DIR OUT_DIR [stature=1.75] [steps=800] [f=8000] [age=0.5]
A woman (gender 0, age held), body targets only, one pose per frame (one camera), depth per frame free and the size held by the
stature. The outline above the shoulders (hair) and below the ankles (heels) isn't used; the mask still holds the body inside it.
MediaPipe's landmarks are matched to the rig's joints. Writes OUT_DIR/fit.json (recipe, history, per-frame camera and pose) and
OUT_DIR/posed.npz (each frame's posed body in the camera's axes, for the overlays)."""
import json, os, sys, time
from PIL import Image
import numpy as np
import torch
sys.path.insert(0, "experiments/anny-mpfb")
import mpfb_anny
import fit as F

frames_dir, out_dir = sys.argv[1], sys.argv[2]
opts = dict(a.split("=", 1) for a in sys.argv[3:])
STATURE = float(opts.get("stature", 1.75))
STEPS = int(opts.get("steps", 800))
FOCAL = float(opts.get("f", 8000))
AGE = float(opts.get("age", 0.5))
HEELS_M = 0.08  # the shoe's lift, for the first guess of the distance only
os.makedirs(out_dir, exist_ok=True)

# rig joint -> MediaPipe landmark; neck and head have none
MP = {"upperleg01.L": "hip.L", "upperleg01.R": "hip.R", "lowerleg01.L": "knee.L", "lowerleg01.R": "knee.R", "foot.L": "ankle.L", "foot.R": "ankle.R",
      "upperarm01.L": "shoulder.L", "upperarm01.R": "shoulder.R", "lowerarm01.L": "elbow.L", "lowerarm01.R": "elbow.R", "wrist.L": "wrist.L", "wrist.R": "wrist.R"}
meta = json.load(open(os.path.join(frames_dir, "frames.json")))["kept"]
frames = []
for k in meta:
    mask = np.array(Image.open(os.path.join(frames_dir, "frames", k["stem"] + ".mask.png")).convert("L")) > 0
    j = k["joints"]
    joints = np.array([[j[MP[b]][0], j[MP[b]][1]] if b in MP else [np.nan, np.nan] for b in F.JOINTS], dtype=np.float32)
    top = max(j["shoulder.L"][1], j["shoulder.R"][1]) + 0.03 * k["bbox"][3]
    bottom = min(j["ankle.L"][1], j["ankle.R"][1])
    o = F.outline(mask, n=1200).numpy()
    o = o[(o[:, 1] > top) & (o[:, 1] < bottom)]
    frames.append({"yaw": 0.0 if k["view"] == "front" else 180.0, "mask": mask, "joints": joints, "outline": o})

dev = "cuda"
mpfb_anny.CUTOFF = 0.0
m = mpfb_anny.model(dtype=torch.float32, device=dev)
cam = F.Camera(f=FOCAL, dist=0.0, size=tuple(meta[0]["size"]))

# First guess of each frame's translation: the default body's centre on the mask's box, at the distance its height gives
with torch.no_grad():
    v0 = F.Shape(m, 1)()[0][0, :F.N_BODY].cpu().numpy()
cx, cz, h0 = (v0[:, 0].max() + v0[:, 0].min()) / 2, (v0[:, 2].max() + v0[:, 2].min()) / 2, np.ptp(v0[:, 2])
init = []
W, H = meta[0]["size"]
for k in meta:
    x, y, w, h = k["bbox"]
    d = FOCAL * (STATURE + HEELS_M) / h
    uc, vc = x + w / 2, y + h / 2
    sx = (uc - W / 2) * d / FOCAL - cx
    if k["view"] == "back":
        sx = (uc - W / 2) * d / FOCAL + cx  # the yaw of 180 mirrors x
    sz = -(vc - H / 2) * d / FOCAL - cz
    init.append([sx, d, sz])

t0 = time.time()
shape = F.fit(m, cam, frames, steps=STEPS, fit_locals=True, local_mask=F.body_local_mask(m), fixed={"gender": 0.0, "age": AGE},
              hold_depth=False, stature=STATURE, init_shift=init, log=print)
secs = time.time() - t0

with torch.no_grad():
    verts, heads = shape()
    yaw = torch.tensor([f["yaw"] for f in frames], device=dev)
    uv = cam.project(verts[:, :F.N_BODY], yaw, shape.shift).cpu().numpy()
    juv = cam.project(heads[:, F.joint_index(m)], yaw, shape.shift).cpu().numpy()
    # posed bodies in the camera's axes (yaw and translation applied), for Blender
    a = torch.deg2rad(yaw)
    c, s_ = torch.cos(a)[:, None], torch.sin(a)[:, None]
    X, Y, Z = verts[..., 0], verts[..., 1], verts[..., 2]
    sh = shape.shift
    cam_verts = torch.stack([c * X - s_ * Y + sh[:, None, 0], s_ * X + c * Y + sh[:, None, 1], Z + sh[:, None, 2]], -1).cpu().numpy()
    rest = shape.last_rest[0, :F.N_BODY].cpu().numpy()

per_frame = []
for b, k in enumerate(meta):
    mask = frames[b]["mask"]
    inside = F.sample(F.distance_outside(mask), torch.from_numpy(uv[b])).numpy()
    jerr = np.linalg.norm(juv[b] - frames[b]["joints"], axis=1)
    per_frame.append({"stem": k["stem"], "view": k["view"], "depth_m": round(float(shape.shift[b, 1]), 3),
                      "outside_mask_px_mean": round(float(inside.mean()), 2), "joint_px_mean": round(float(np.nanmean(jerr)), 1)})
recipe = shape.recipe()
recipe.update({"name": "modelo10_ajuste", "sex": "female"})
result = {"seconds": round(secs, 1), "stature_m": STATURE, "focal_px": FOCAL, "fitted_stature_m": round(float(np.ptp(rest[:, 2])), 4),
          "recipe": recipe, "history": shape.history, "frames": per_frame}
json.dump(result, open(os.path.join(out_dir, "fit.json"), "w"), indent=1)
np.savez_compressed(os.path.join(out_dir, "posed.npz"), cam_verts=cam_verts, uv=uv, juv=juv, rest=rest, faces=np.array(m.faces.tolist()),
                    stems=np.array([k["stem"] for k in meta]))
print("done", secs, "s; stature", result["fitted_stature_m"])

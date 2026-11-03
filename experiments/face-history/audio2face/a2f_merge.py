"""Merge: mouth from Audio2Face with lip contact taken from its geometry; blink and brows from the video's blendshapes.
Args: model dir, geometry.npy, weights.json (from a2f_solve), video clean JSON, output JSON, actor, config."""
import json, sys
import numpy as np
model, geo, wj, vj, out, actor, cfg = sys.argv[1:7] + [json.loads(sys.argv[7])]
pred = np.load(geo); skin = pred[:, :72006].reshape(len(pred), -1, 3)
d = np.load(f"{model}/model_data_{actor}.npz")
neutral = d["neutral_skin"]; lip = d["lip_open_pose_delta"]
pos = neutral[None] + skin
# Lip vertices: the ones the model's own lip-open pose moves most, near the centre line, split into upper and lower.
# Each lip comes from NVIDIA's own rig: the centre vertices its upper-lip-up and lower-lip-down poses move most.
rig = np.load(f"{model}/bs_skin_{actor}.npz")
up = rig["mouthUpperUpLeft"] + rig["mouthUpperUpRight"]; dn = rig["mouthLowerDownLeft"] + rig["mouthLowerDownRight"]
cx = float(np.median(neutral[np.argsort(-np.linalg.norm(up, axis=1))[:200], 0]))
near = np.abs(neutral[:, 0] - cx) < cfg["centre_cm"]
upper = np.flatnonzero(near)[np.argsort(-up[near, 1])[:cfg["edge_verts"]]]
lower = np.flatnonzero(near)[np.argsort(dn[near, 1])[:cfg["edge_verts"]]]
ng = float(neutral[upper, 1].mean() - neutral[lower, 1].mean())
print("lip verts upper", len(upper), "lower", len(lower), "neutral gap cm", round(ng, 3), "up move", round(float(up[upper, 1].mean()), 2), "down move", round(float(dn[lower, 1].mean()), 2), "x centre", round(cx, 2), "bbox y", neutral[:, 1].min().round(1), neutral[:, 1].max().round(1))
gap = pos[:, upper, 1].mean(1) - pos[:, lower, 1].mean(1)
assert np.isfinite(gap).all()
closed = np.percentile(gap, cfg["closed_percentile"])
mm = np.clip(gap - closed, 0, None) * 10 * cfg["mesh_scale"]
print("model lip gap mm p10 %.1f p50 %.1f p90 %.1f max %.1f; frames at contact(<0.5mm) %d of %d" % (*np.percentile(mm, [10, 50, 90, 100]), (mm < 0.5).sum(), len(mm)))
take = json.load(open(wj)); ch = {k: np.array(v) for k, v in take["channels"].items()}
# Replace jaw-driven opening with the measured gap, so the lips touch when the model's lips touch.
jaw_before = ch["jawOpen"].copy()
ch["jawOpen"] = np.clip(mm / cfg["mm_at_full_jaw"], 0, 1)
for n in ("mouthClose",): ch[n] = np.zeros(len(mm))
for n in ("mouthUpperUpLeft", "mouthUpperUpRight", "mouthLowerDownLeft", "mouthLowerDownRight"):
    ch[n] = ch[n] * cfg["lip_lift_gain"]
contact = np.clip(1 - mm / cfg["contact_mm"], 0, 1)
for sd in ("Left", "Right"):
    ch["mouthPress" + sd] = np.clip(ch["mouthPress" + sd] * cfg["press_gain"] + contact * cfg["press_on_contact"], 0, 1)
ch["mouthRollLower"] = np.clip(ch["mouthRollLower"] * cfg["roll_gain"], 0, 1); ch["mouthRollUpper"] = np.clip(ch["mouthRollUpper"] * cfg["roll_gain"], 0, 1)
# Video owns blink and brows: audio does not know when a person blinks.
v = json.load(open(vj)); n_v = v["frames"]; vfps = v["fps_num"] / v["fps_den"]
tv = np.arange(n_v) / vfps; ta = np.arange(len(mm)) / 60
for n in [k for k in v["channels"] if k.startswith(("eyeBlink", "brow", "eyeSquint"))]:
    ch[n] = np.interp(ta, tv, np.array(v["channels"][n]))
lo, hi = cfg["blink_from"], cfg["blink_to"]  # tired or lowered lids read as part-blinks: only strong readings count
for sd in ("Left", "Right"):
    t = np.clip((ch["eyeBlink" + sd] - lo) / (hi - lo), 0, 1)
    ch["eyeBlink" + sd] = t * t * (3 - 2 * t)
    ch["eyeSquint" + sd] = ch["eyeSquint" + sd] * cfg["squint_gain"]
    ch["eyeWide" + sd] = np.clip(cfg["lid_open"] * (1 - ch["eyeBlink" + sd]), 0, 1)
take["channels"] = {k: [round(float(x), 4) for x in a] for k, a in ch.items()}; take["merge"] = cfg
json.dump(take, open(out, "w"))
print("jaw before mean %.2f after mean %.2f max %.2f" % (jaw_before.mean(), ch["jawOpen"].mean(), ch["jawOpen"].max()), "blink max", round(float(ch["eyeBlinkLeft"].max()), 2), "press mean", round(float(ch["mouthPressLeft"].mean()), 2))

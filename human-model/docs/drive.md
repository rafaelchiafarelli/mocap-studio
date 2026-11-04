# Driving the model from recordings

## Face: what's been tried

On the approved fader take, one character and one recording, three variants. Video: `comparacao_faders_hibrido_musculos.mp4` in the review folder.

| Variant | How |
|---|---|
| **Faders** | The approved result |
| **Faders plus muscles** | The faders stay; muscles add cheek lift and folds with the smile, and forehead lines with the brows |
| **Muscles only** | Solved from tracked points; jaw, gaze, tongue and blink stay as they were |

**Your verdict:** none yet. "Within this sample the pure muscle is clearly the worst." The actress's mouth twists a little in the original, the hybrid twists too, and the faders twist it a little more. You want to investigate further.

## Face: how activations are solved

`hmcore/activation.py`. 31 of the tracker's landmarks are matched to skin vertices through rig bones. Each frame:

1. Head motion is removed, by aligning stable points (eye corners, nose bridge) to rest.
2. The jaw's expected motion is subtracted.
3. Solve for activations: match the points' movement, with each activation between 0 and 1, and an **effort penalty** that prefers less total activation.

| Effort | Active muscles | Total activation | Residual | Frame-to-frame change |
|---:|---:|---:|---:|---:|
| 0 | 24.6 | 16.7 | 0.73 | 0.83 |
| **1e-5, chosen** | 10.7 | 6.6 | 0.79 | 0.45 |
| 1e-4 | 2.1 | 1.4 | 0.99 | 0.07 |
| 1e-3 | 0.1 | 0.08 | 1.00 | 0 |

So least effort calms the solve, but a residual of 0.79 means the muscles reach only part of what the tracker saw. Two limits add up: the fields don't span real facial motion, and 2D points have tracker noise.

## Face: running a take

From a file made by `add_fields.py` ([running.md](running.md#using-an-existing-character-file)):

```sh
# read the take's shapes and their values per frame
python3 human-model/blender_run.py --blend $B.muscle.blend human-model/blender/dump_take.py BODY_OBJECT $B.take.npz

# solve activations
human-model/hm.sh python human-model/tools/solve_take.py $B.fields.npz $B.take.npz $B.export.npz $B.export.json mouth_data.json tracker.csv $B.activ.npz 0.0583 $B.report.json

# key a variant: faders, hybrid or muscle
python3 human-model/blender_run.py --blend $B.muscle.blend human-model/blender/key_take.py BODY_OBJECT $B.activ.npz hybrid $B.hybrid.blend

# render it
python3 human-model/blender_run.py --blend $B.hybrid.blend human-model/blender/render_take.py OUT_DIR
```

`mouth_data.json` and `tracker.csv` come from `experiments/face-mouth/`; `0.0583` is the character's eye distance in metres. Hybrid gains are in `tools/solve_take.py`.

The comparison character keeps its own jaw shape and tongue keys. Connecting it to `hm_jaw` and the tongue controls is still to do.

## Tongue

`hmcore/tongue.py`. The tracker can't see the tongue, so it follows the known words' sounds. Each of the 13 mouth groups has a pose of the 4 tongue controls, with attack and release. Values are declared from where each sound is articulated. The curves are computed, but no render has shown them on the model.

## Body

```sh
human-model/hm.sh python human-model/tools/body_motion.py BODY_3D.npy BODY_3D.csv motion.json quality.json 30
python3 human-model/blender_run.py --blend MODEL.blend human-model/blender/body_drive.py motion.json OUT.blend
```

`mediapipe_body_3d_xyz.npy` and `.csv` come from a FreeMoCap output folder. Bones take the actor's **directions**, so the character keeps its proportions. The root is scaled by leg length.

Not carried: twist, hands, fingers, spine bending. No filter is applied, so the input can be judged as it is.

**Tested on FreeMoCap's 60-frame sample,** not on your recordings:

| Measure | Result |
|---|---|
| Rigid bones changing length | Thigh 4–6%, shin 8–11%, foot 13–16%, upper arm 6–7%, forearm 11% |
| Median jitter | Hip 8.8, ankle 12.8, nose 13.0, wrist 29.0 mm |

`quality.json` gives the same numbers for any recording, a quick way to look at your own. **What's wrong with your body results is still an open question.**

## Compressing the fields

Whether stored data can stand in for the fields (`tools/fit_fields.py`), measured on the take:

| Components | Mean error | Worst error | Stored |
|---:|---:|---:|---:|
| 5 | 0.78 mm | 13.1 mm | 0.5 MB |
| 15 | 0.28 mm | 4.1 mm | 1.5 MB |
| 30 | 0.11 mm | 2.8 mm | 3.0 MB |
| 44, all | 0 | 0 | 4.4 MB |

Not worth doing: 44 keys cost little, and compression visibly moves a lip or lid.

Code: `hmcore/activation.py`, `hmcore/tongue.py`, `hmcore/retarget.py`, `hmcore/retire.py`, `tools/solve_take.py`, `tools/body_motion.py`, `blender/dump_take.py`, `blender/key_take.py`, `blender/render_take.py`, `blender/body_drive.py`, `tests/test_drive.py`.

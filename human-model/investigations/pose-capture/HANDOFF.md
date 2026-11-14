# Handoff: pose capture onto an MPFB body, then physics

Written 2026-11-14, at the end of the session that built the animation body and face (branch `animation-face`). For the session that starts this investigation, and for Rafael.

## Why this test

Rafael (2026-11-14): the biggest problem was never the body's shape. It was the physics, the way the body moves. Both earlier paths (muscles and tissue layers, then the animation body with pendulum arms and skin waves) moved forward a little but "more steps sideways": the motion never looked human.

The shape is a solved problem in his view. Silhouette, biotype and measures are presets of MPFB parameters and their correlates (hourglass with ectomorph puts the buttock at about 1.3 times the hip, mesomorph at 1.4 to 1.5, with shoulders, back and torso following). Breast, areola and nipple have MPFB controls for nearly everything.

So the test is investigative. Put real, captured human motion on his MPFB body first, then add physics, and see whether the physics makes it more or less human. Judged by eye, by Rafael, in simple videos.

## Goal

1. Capture the motion of the reference models "fazendo pose" (posing) from the videos we have.
2. Put it on `G:\mocap-studio-downloads\review\2026-11-14\mpfb_ampulheta_mesomorfo.blend`.
3. Then add the body's physics.
4. A video of each step, so the steps can be compared.

## Inputs

**The body:** `G:\mocap-studio-downloads\review\2026-11-14\mpfb_ampulheta_mesomorfo.blend`, made by Rafael. Beside it, `mpfb_original_parametros_padrao.blend` (MPFB defaults) and `abrir_mpfb_original.bat`.

Checked 2026-11-14:
- One object, `Human`, a mesh with 19,158 vertices (MakeHuman's 13,380 body vertices first, then helpers), a Mask modifier and 36 shape keys.
- **No armature.** A rig has to be added before any motion can drive it.
- Scene at 24 fps, frames 1 to 250.
- Open it with the portable Blender on G: (`human-model/blender_run.py`), since the MPFB add-on is installed only there (memory: `blender-portable-launch`).

**The clips:** 148 runway stretches cut from `G:\mocap-studio-downloads\tiktok_videos\` (`2.mp4`, `3.mp4`, `4.mp4`, `5.mp4`, `Evolution_video_no_watermark_1.mp4`). They are in `G:\mocap-studio-downloads\review\2026-11-10\passarela_trechos\clips\`. Rafael's table is `G:\mocap-studio-downloads\tiktok_videos\modelos.csv`; in it he wrote "pose" in the notes column of ten clips:

| Clip | Source | Seconds | View | Model |
|---|---|---|---|---|
| `0003_2_00026.mp4` | 2.mp4 | 26.9–29.1 | front, coming | 1 |
| `0005_2_00052.mp4` | 2.mp4 | 52.9–55.1 | 3/4 | 2 |
| `0007_2_00078.mp4` | 2.mp4 | 78.1–81.7 | front | 4 |
| `0018_2_00214.mp4` | 2.mp4 | 214.6–217.1 | front, coming | 6 |
| `0027_2_00346.mp4` | 2.mp4 | 346.8–351.6 | front | 7 |
| `0037_3_00033.mp4` | 3.mp4 | 33.7–35.9 | front, coming | 10 |
| `0055_3_00314.mp4` | 3.mp4 | 314.0–316.6 | front, coming | 20 |
| `0059_3_00384.mp4` | 3.mp4 | 384.2–386.6 | front | 22 |
| `0083_5_00110.mp4` | 5.mp4 | 110.9–117.3 | front | 27 |
| `0100_5_00305.mp4` | 5.mp4 | 305.3–316.0 | front | 29 |

The clips are 2 to 11 seconds, one camera each, the camera often following the model. Rafael's earlier rule for these videos: they are reference only, never used in the product, so copyright isn't a concern for the test (2026-11-10). Ask him which clip to start with; the longest (`0100`, `0083`) give the most motion.

## Constraints that still hold

- **Licenses must allow commercial use, even for tests** (memory `licenses-commercial-only`). This rules out SMPL and every pose estimator whose output or weights depend on it (SMPL-X, WHAM, 4D-Humans/HMR2, and the like), which are non-commercial. MediaPipe Pose (Apache-2.0) is the safe baseline already in use here.
- **Nobody can sculpt;** everything is built with tools.
- **No genitalia.**
- **Keep every intermediate result,** each with a clear name, in `G:\mocap-studio-downloads\review\<date>\` (memories `keep-intermediate-results`, `review-files-on-g-drive`).
- **Commit and push regularly** on a task branch merged `--no-ff` (the session's habit; Rafael asked for it so nothing is lost).
- **Simple physical models over stacks of rules;** contact over avoidance (memories `physical-models-over-patches`, `contact-over-avoidance`).
- **Ask before planning body work beyond this test** (memory `body-results-also-bad`); agree soft-tissue options with Rafael before building them (memory `soft-tissue-direction`).

## What already exists and may help

**Pose from video**
- `human-model/tools/check_reference.py` runs MediaPipe Pose on clips in Docker (`human-model/hm.sh --ref`, image `Dockerfile.reference`). It judges clips, but its pose reading can be reused.
- `human-model/tools/body_motion.py` (capture to bone directions, with a quality report) and `human-model/blender/body_drive.py` (keys capture onto a rig by bone direction) come from the earlier human model, made for the studio's multi-camera capture. Read them before writing new retargeting.
- The project's own pipeline (multi-camera markerless capture, stages P1 to P5, see the root `CLAUDE.md` and the `mocap-workflow` skill) is multi-camera. These clips are single-camera, so depth comes only from the estimator.
- MediaPipe's 3D "world" landmarks are coarse: no spine detail, 33 points. Expect the pelvis and spine to need care.
- The face tools (`experiments/face-dense/`, BootsTAPIR) show that dense tracking on these GPUs needs windows of time: 597 frames at 512 px used 28.6 GB on the 16 GB card.

**A rig on an MPFB body**
- `human-model/blender/clean_body.py` builds an MPFB human from a recipe with the Rigify metarig `rigify.human` (rig `HM_rig`, body `HM_body`).
- It also merges the orphan `DEF-*` weights into real bones; without that, vertices stay behind and tear the mesh (`clean_body.py`, `merge_orphan_weights`).
- It may be simpler to read Rafael's file into a recipe (`human-model/blender/recipe_from_file.py`) and rebuild it with `clean_body.py` than to add a rig to his file by hand. Check that the result matches his body.

**Physics built in the last session** (all in `human-model/`, documented in `docs/animation-body.md`)
- `hmcore/skin_waves.py`, `tools/skin_waves.py`, `blender/skin_dump.py`, `blender/wave_bake.py`:
  - per-vertex mass-spring sway along the normal, driven by each vertex's own acceleration, joined to its neighbours, with a heel-strike pulse (`hmcore/foot_impact.py`);
  - regions and values in `data/skin_waves.json`;
  - baked as shape keys with a `wave_amount` fader.
  - **This works on any motion, captured included.** It is the most direct "physics on top" to try.
- `blender/fold_lines.py`, `fold_apply.py`, `fold_fine.py`: folds as shape keys driven by the pose.
- `blender/arm_pendulum.py`: arms as damped triple pendulums with collision. With captured arms it would replace the capture, so probably not wanted here. Its collision against the trunk may still be useful.
- The earlier path's GPU soft-body work (`hmcore/xpbd.py`, `tools/body_walk.py`, `docs/muscle-physics.md`) is heavier, and Rafael found it unusable on 2026-11-10.

## Suggested first steps (to agree with Rafael)

1. Pick one pose clip with him.
2. Get MediaPipe Pose world landmarks per frame and check them on an overlay video.
3. Give his body a rig that deforms it cleanly, and render it at rest to compare with his file.
4. Retarget the landmarks to bone directions and key them. Render the captured motion plain, with no physics: this is the reference.
5. Add the skin waves on top, then compare the two side by side with the clip.

## State left behind

- **Branch:** `animation-face`, pushed. Everything from the last session is merged there; `main` doesn't have it yet.
- **Memories:**
  - `motion-is-the-problem`: this test's reasoning;
  - `animation-face-state`: where the animation body and face stand;
  - `faces-actor-remap-direction`: Rafael preferred the faders to Audio2Face on 2026-11-13.
- **Rafael's decisions still pending from the face work:**
  - the "F by contact" pose for the fader reference;
  - a torso fat layer for the oval and rectangle silhouettes.

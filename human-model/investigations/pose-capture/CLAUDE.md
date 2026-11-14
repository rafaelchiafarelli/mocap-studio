# pose-capture — captured posing motion on Rafael's MPFB body, then physics

**Role:** investigation, not product code. Starts from [HANDOFF.md](HANDOFF.md). Each step writes a numbered file to `G:\mocap-studio-downloads\review\2026-11-14\pose_capture\`; nothing there is overwritten or deleted.

**Entry points:** step 1 `hm.sh --ref python human-model/investigations/pose-capture/capture_pose.py CLIP OUT.npz OVERLAY.mp4`; step 2 `blender_run.py --blend BODY.blend .../rig_body.py OUT.blend CHECK_DIR`; step 3 `blender_run.py --blend 02_corpo_com_rig.blend .../drive_capture.py LANDMARKS.npz OUT.blend REPORT.json [SIGMA]`, then `blender/simple_video.py` for frames; two cameras: `two_cameras.sh A.mp4 B.mp4 OUT_DIR [--height 1.70] [--focal-mm 26] [--offset S] [--fixed-focal]`; its synthetic check `hm.sh --ref python human-model/investigations/pose-capture/test_two_cameras.py`.

**Inputs → Outputs:** clip `0100_5_00305.mp4` (chosen by Rafael, 2026-11-14) → `01_mediapipe_0100.npz` (landmarks) and `01_captura_mediapipe_0100.mp4` (overlay, H.264 via host ffmpeg); Rafael's `mpfb_ampulheta_mesomorfo.blend` → `02_corpo_com_rig.blend` and `02_verificacao_rig/`; → `03_movimento_capturado_0100.blend` (keyed at 60 fps), `03_relatorio_retarget.json`, `03_quadros_frente/` and `03_comparacao_clipe_vs_corpo_sem_fisica.mp4`. Each `.blend` has an `abrir_<name>.bat` that opens it in the portable Blender 5.2.2.

## Files

- `HANDOFF.md`: why this test, inputs, constraints, suggested steps.
- `capture_pose.py`: step 1, MediaPipe Pose ('full' model) on every frame; landmarks and an overlay with front and side 3D views.
- `rig_body.py`: step 2, MPFB's Rigify metarig added to Rafael's `Human` in place (no rebuild from a recipe, so his 36 shape keys stay), orphan `DEF-*` weights merged as in `blender/clean_body.py`, stills at rest and in a test pose.
- `two_cameras.py`: joins two videos into one 3D capture with no board (Rafael's choice, 2026-11-14, after MediaPipe's single view failed: the model flew, leaned forward, and heels threw the feet off): clap sync by sound, cameras from the body's landmarks plus rigid limb bones, left/right swaps per group resolved by reprojection and continuity, upright on the floor, scaled by height. Writes `two_cameras.npz` (its `world` reads like a single camera's in `drive_capture.py`), `two_cameras.json` and an overlay.
- `two_cameras.sh`: the host side: `ffprobe` start times, `ffmpeg` sound, `capture_pose.py` per video, `two_cameras.py`, H.264 copies.
- `test_two_cameras.py`: synthetic check: clip 0100's 3D made rigid, seen by two virtual phones with noise, a known clap and leg swaps.
- `drive_capture.py`: step 3, landmarks smoothed (gaussian, 2 frames) and keyed as bone directions: pelvis, chest and head frames shared along the spine, limbs by shortest swing with knee and elbow twisted into the captured bend plane, sole and hand oriented, the lower foot held still on the floor; checks left and right on every frame; records the capture's metric scale for a 1.70 m woman.

## Key facts / gotchas

- The 'heavy' model (complexity 2) is downloaded by MediaPipe at run time into site-packages, which the image's user can't write: `capture_pose.py` uses 'full' (`COMPLEXITY`).
- Clip 0100: front pose from frame 1 to ~250, a turn around ~320, then the back. MediaPipe keeps left and right right in the back (its trunk turns to face away), but its depth is poor there: the hip line shrinks from 0.23 m to ~0.11 m.
- Axes: MediaPipe (x right, y down, z away) → Blender (x, z, -y), a proper rotation, so left stays left; `drive_capture.py` checks it per frame (`side_check_failures`, empty on clip 0100).
- `pb.matrix` writes leave rounding scale on the bone; `drive_capture.py` resets `pb.scale` each frame, or it grows (the first run's left toe climbed 1.5 m; that `.blend` was overwritten by the fixed run).
- The woman wears high heels and the body is barefoot, so captured feet point down.
- The captured woman's height is taken as 1.70 m (Rafael, 2026-11-14); Rafael's body is 1.59 m. Retargeting by direction doesn't depend on either.
- Two views of points alone can't tell the focal length (a wrong one reprojects as well); `two_cameras.py` fits it with the limb bones held rigid. Synthetic median 3D error for 1.5 / 5 / 10 px of 2D noise: 6 / 20 / 43 mm (`calibrate` docstring). MediaPipe's own 2D noise is what limits the result.
- Phone videos: variable frame rate (so `capture_pose.py` stores each frame's time), a rotation flag (size taken from a decoded frame), and audio and video streams that don't start together (`meta.json` from `ffprobe`). The clips in `passarela_trechos/clips/` have no sound.
- Smoke test 2026-11-14 with clip 0100 against itself shifted 0.3 s: sync found -0.300 s; with music and no clap the confidence was 1.28, under the 1.5 that prints a warning.

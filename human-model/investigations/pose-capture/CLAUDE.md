# pose-capture — captured posing motion on Rafael's MPFB body, then physics

**Role:** investigation, not product code. Starts from [HANDOFF.md](HANDOFF.md). Each step writes a numbered file to `G:\mocap-studio-downloads\review\2026-11-14\pose_capture\`; nothing there is overwritten or deleted.

**Entry points:** step 1 `hm.sh --ref python human-model/investigations/pose-capture/capture_pose.py CLIP OUT.npz OVERLAY.mp4`; step 2 `blender_run.py --blend BODY.blend .../rig_body.py OUT.blend CHECK_DIR`; step 3 `blender_run.py --blend 02_corpo_com_rig.blend .../drive_capture.py LANDMARKS.npz OUT.blend REPORT.json [SIGMA]`, then `blender/simple_video.py` for frames.

**Inputs → Outputs:** clip `0100_5_00305.mp4` (chosen by Rafael, 2026-11-14) → `01_mediapipe_0100.npz` (landmarks) and `01_captura_mediapipe_0100.mp4` (overlay, H.264 via host ffmpeg); Rafael's `mpfb_ampulheta_mesomorfo.blend` → `02_corpo_com_rig.blend` and `02_verificacao_rig/`; → `03_movimento_capturado_0100.blend` (keyed at 60 fps), `03_relatorio_retarget.json`, `03_quadros_frente/` and `03_comparacao_clipe_vs_corpo_sem_fisica.mp4`. Each `.blend` has an `abrir_<name>.bat` that opens it in the portable Blender 5.2.2.

## Files

- `HANDOFF.md`: why this test, inputs, constraints, suggested steps.
- `capture_pose.py`: step 1, MediaPipe Pose ('full' model) on every frame; landmarks and an overlay with front and side 3D views.
- `rig_body.py`: step 2, MPFB's Rigify metarig added to Rafael's `Human` in place (no rebuild from a recipe, so his 36 shape keys stay), orphan `DEF-*` weights merged as in `blender/clean_body.py`, stills at rest and in a test pose.
- `drive_capture.py`: step 3, landmarks smoothed (gaussian, 2 frames) and keyed as bone directions: pelvis, chest and head frames shared along the spine, limbs by shortest swing with knee and elbow twisted into the captured bend plane, sole and hand oriented, the lower foot held still on the floor; checks left and right on every frame; records the capture's metric scale for a 1.70 m woman.

## Key facts / gotchas

- The 'heavy' model (complexity 2) is downloaded by MediaPipe at run time into site-packages, which the image's user can't write: `capture_pose.py` uses 'full' (`COMPLEXITY`).
- Clip 0100: front pose from frame 1 to ~250, a turn around ~320, then the back. MediaPipe keeps left and right right in the back (its trunk turns to face away), but its depth is poor there: the hip line shrinks from 0.23 m to ~0.11 m.
- Axes: MediaPipe (x right, y down, z away) → Blender (x, z, -y), a proper rotation, so left stays left; `drive_capture.py` checks it per frame (`side_check_failures`, empty on clip 0100).
- `pb.matrix` writes leave rounding scale on the bone; `drive_capture.py` resets `pb.scale` each frame, or it grows (the first run's left toe climbed 1.5 m; that `.blend` was overwritten by the fixed run).
- The woman wears high heels and the body is barefoot, so captured feet point down.
- The captured woman's height is taken as 1.70 m (Rafael, 2026-11-14); Rafael's body is 1.59 m. Retargeting by direction doesn't depend on either.

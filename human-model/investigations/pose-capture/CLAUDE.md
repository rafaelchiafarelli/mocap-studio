# pose-capture — captured posing motion on Rafael's MPFB body, then physics

**Role:** investigation, not product code. Starts from [HANDOFF.md](HANDOFF.md). Each step writes a numbered file to `G:\mocap-studio-downloads\review\2026-11-14\pose_capture\`; nothing there is overwritten or deleted.

**Entry points:** `hm.sh --ref python human-model/investigations/pose-capture/capture_pose.py CLIP OUT.npz OVERLAY.mp4`.

**Inputs → Outputs:** clip `0100_5_00305.mp4` (chosen by Rafael, 2026-11-14) → `01_mediapipe_0100.npz` (landmarks) and `01_captura_mediapipe_0100.mp4` (overlay, H.264 via host ffmpeg).

## Files

- `HANDOFF.md`: why this test, inputs, constraints, suggested steps.
- `capture_pose.py`: step 1, MediaPipe Pose ('full' model) on every frame; landmarks and an overlay with front and side 3D views.

## Key facts / gotchas

- The 'heavy' model (complexity 2) is downloaded by MediaPipe at run time into site-packages, which the image's user can't write: `capture_pose.py` uses 'full' (`COMPLEXITY`).
- Clip 0100: front pose from frame 1 to ~250, a turn around ~320, then the back; in the turn and the back, MediaPipe swaps left and right.

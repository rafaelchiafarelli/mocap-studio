# face-dense — dense skin tracking moved onto the animation face

**Role:** the archived `experiments/face-history/dense_face/` test, adapted to the animation-body woman and the baseline recording (initiative `animation-face`, 2026-11-13). An experiment, not pipeline code.

**Entry points:** run in order from the repository root, with `scratch/dense_face/.venv` (PyTorch, MediaPipe, OpenCV) and `scratch/dense_face/third_party/tapnet`, both only in Rafael's clone:

    python find_crop.py <video> <face_landmarker.task> 50                       # prints x0 y0 size and the query frame
    python stage1_track.py <tapnet> <video> <bootstapir.pt> <face_landmarker.task> out/stage1.npz q x0 y0 size [grid px]
    python stage1_pose.py <video> <face_landmarker.task> out/stage1.npz out/lm3d.npy
    blender_run.py --blend <face>.blend stage3_neutral.py out/stage3
    python stage3_solve.py out/stage1.npz out/stage3 <face_landmarker.task>
    blender_run.py --blend <face>.blend stage3_apply.py out/stage3/face.pc2 out/stage3/channels.json <voice.wav> out/face.blend

**Inputs → Outputs:** a recording and a face `.blend` → a vertex cache (PC2) on `HM_body`, with eye, lash, teeth and tongue channels.

## Files

- `find_crop.py`: the face's square crop over the whole video and a shut-mouth query frame before speech.
- `stage1_track.py`: BootsTAPIR on MediaPipe's 478 landmarks plus a grid; all points in one call, so the video's features are computed once.
- `stage1_pose.py`: MediaPipe's 3D landmarks per frame, to take the head's motion out.
- `stage3_neutral.py`, `stage3_solve.py`, `stage3_apply.py`: the character's neutral render and landmarks, the transfer onto its mesh cut along the mouth, and the cache on the face file.
- `stage1_report.py`: the tracked points drawn over the video.

## Key facts / gotchas

- The whole video sits on the GPU: 597 frames at 512 px peaked at 28.6 GB on the 16 GB card, spilling to system memory (2 s per frame at a 6 px grid, 4.4 s at 4 px). Longer takes need windows of time.
- The round trip check starts from the last frame; on the baseline the head is turned there, so it reads 60 px of error while the tracks agree with MediaPipe within 2 px elsewhere.
- With a shut-mouth query frame, the upper and lower lip points start on the same seam and the tracker follows one lip, so the mouth barely opens on the character. Query the lips on an open-mouth frame.

## Touchpoints

`experiments/face-history/` (the original), `experiments/face-mouth/` (the faders to beat), `initiatives/animation-face/`.

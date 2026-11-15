# anny-mpfb — an MPFB body from video, investigation (path A)

**Role:** investigation (Rafael, 2026-11-14): fit MPFB sliders to silhouettes and 2D joints of a real woman in video, with Anny (NAVER, Apache-2.0; MakeHuman assets CC0) as a differentiable MPFB. Committed 2026-11-15 at Rafael's request; results on G: in `models/anny-mpfb/`.

**Entry points:** `run.sh python experiments/anny-mpfb/<script>.py ...` (Docker, GPU; image `mocap-anny-mpfb`, hashed `requirements.txt` from `requirements.in`). `mpfb_reference.py` runs in Blender through `human-model/blender_run.py`.

## Files

- `mpfb_anny.py`: Anny with MPFB 2.0.18's own macro formula in place of Anny's (`mpfb_blendshape_weights`); `-decr` targets are Anny's `-incr` negative.
- `mpfb_reference.py`: MPFB meshes for 11 macro/target cases, from Blender (test 1's truth).
- `compare.py`: test 1 with Anny's own formula (differs: gender inverted, age with a newborn anchor, two-anchor height and proportions, races normalised, breasts scaled by female).
- `compare_mpfb.py`: test 1 with `mpfb_anny`: equal to MPFB within 0.02 mm in all cases, after a translation (Anny places the body differently).
- `bench.py`: test 2, speed and VRAM with gradients on the RTX 4080 SUPER: 32 frames 116 ms per step, 0.32 GB.
- `fit.py`: the fit: macros, locals (optionally body only), pose per instant (shared by views of one instant), translation with depth held; silhouette terms from vertices (no rasterizer); `GAPS` skips MPFB's flat mid range of height and proportions.
- `extract_frames.py`: one runway model's frames, MediaPipe Pose masks and landmarks (`human-model/hm.sh --ref`; complexity 1, the heavy model isn't in the wheel).
- `fit_video.py`: the fit on those frames: woman, age held, stature held (1.75 m unless given), depth per frame free, outline above the shoulders (hair) and below the ankles (heels) dropped.
- `review_blend.py`: test 3's truths and fits as MPFB humans in one `.blend`.
- `review_video_blend.py`: a video fit as an MPFB human, plus a camera per frame with the frame behind and the posed body as wire; checks the MPFB rebuild against the fit (2.75 mm mean, 4.8 max on model 10: MPFB's 0.01 cutoff).
- `fit_synthetic.py`: test 3, a random known body seen in masks and joints; reports the recovered rest body's error.

## Findings so far (test 3, 3 views x 2 poses, f=7000 px at 10 m, 1 px about 1.4 mm)

- Silhouettes are matched to 1-4 px, but very different sliders match them: per-frame free poses (one per image) let the body lean towards the camera; depth must be held or the size is free.
- Height and proportions start in MPFB's flat mid range and never moved until `GAPS`.
- With views sharing the pose, depth held, women known (gender 0, age held), body locals only: mean error 7, 17 and 10 mm on seeds 2, 1 and 0; seed 1's height still 3 cm off. The fit isn't reliable yet.
- Real runway clips have one camera per instant, so the shared pose isn't available there: expect worse than these numbers.

## Model 10 (video 3, 2026-11-14)

- 23 of 332 sampled frames kept (7 front, 16 back); the nearer front frames have the feet at the picture's edge.
- `ajuste_1`: 137 s, 1 px inside the mask, 2 px from its outline, joints 0.8 px. Suspect: cupsize 1.88 and firmness -0.66 with no side view, and left/right limbs fitted apart (asymmetric).

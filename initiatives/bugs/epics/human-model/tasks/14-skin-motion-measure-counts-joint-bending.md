# The skin's motion per zone counts joint bending as jiggle

- **Symptom:** `skin_motion_peak_by_zone_mm` reads 6 to 87 mm in the lower body's walk, highest at the thighs, knees, belly and buttocks. Most of it is the skin following a bending joint, not tissue swinging.
- **Where:** `human-model/tools/body_walk.py`: each skin vertex is measured in its nearest bone's frame, and near a joint that isn't the bone it hangs from.
- **Reproduce:** `body_walk.json` of any run.
- **Impact:** the number can't be used to tune the tissue's damping; the videos must be judged by eye.
- **Status:** Fixed (2026-11-08) — fixes/0000e8/walk-videos-and-tissue-measure. The measure is now the skin's motion less the current model's, whose skin only follows the bones. Peaks fell from about 65 mm to 30 to 50; the knee still reads 50, which may be how the current model's own knee bends (not checked).

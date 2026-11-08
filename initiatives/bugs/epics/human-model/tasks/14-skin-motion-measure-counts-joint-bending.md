# The skin's motion per zone counts joint bending as jiggle

- **Symptom:** `skin_motion_peak_by_zone_mm` reads 6 to 87 mm in the lower body's walk, highest at the thighs, knees, belly and buttocks. Most of it is the skin following a bending joint, not tissue swinging.
- **Where:** `human-model/tools/body_walk.py`: each skin vertex is measured in its nearest bone's frame, and near a joint that isn't the bone it hangs from.
- **Reproduce:** `body_walk.json` of any run.
- **Impact:** the number can't be used to tune the tissue's damping; the videos must be judged by eye.
- **Status:** Open. Likely fix: measure against the skin's motion with the tissue rigid (the same frame without simulation), so only what the tissue adds remains.

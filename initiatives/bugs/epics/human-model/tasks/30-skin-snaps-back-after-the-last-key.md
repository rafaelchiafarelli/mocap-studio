# 30. The walked skin snaps back to the start after its last frame

**Symptom:** the body leaves the animation and returns to the start of the walk while the bones stay at the end. Rafael saw it at frame 162. Headless on `t2_neutro`, the woman's skin holds through frame 168 and snaps at 169.
**Where:** `human-model/blender/body_walk_bake.py`, `animated`: the last shape key is keyed back to 0 one frame after its own, leaving only the Basis, which is the first frame. Bones keep their last key. `human-model/blender/shared_file.py` leaves the timeline at Blender's 250.
**How to reproduce:** play `review\fast_review_todas.blend` past the end of the walk.
**Impact:** the end of every walk in the shared file. The frame Rafael saw (162) and the one measured (169) differ, unexplained.
**Status:** Fixed (2026-11-09) — task body-type-selection/muscle-bodies/1

# The walk jumps at every step

- **Symptom:** Rafael (2026-11-03): "the animation is jumpy... there is some error somewhere that made the model jump".
- **Where:** `human-model/blender/walk.py`, root solve. The root takes its height and forward motion from whichever foot point is lowest, with no smoothing.
- **Measured:** twice per cycle, height steps up to 27 mm in one frame (median 8) and forward motion up to 72 mm in one frame (median 45), just after each stance foot changes. Total bounce is 6.6 cm. The joint curves aren't the cause: they close at the cycle's wrap with no step.
- **Reproduce:** read `HM_rig`'s location per frame in a file from `walk.py`, or watch `caminhar_masculino_ossos_e_pele.mp4`.
- **Impact:** walking can't get a verdict until this is gone.
- **Status:** Open. That the hand-over causes it is likely, not proven. Likely fix: a continuous contact height and a smoothed root.

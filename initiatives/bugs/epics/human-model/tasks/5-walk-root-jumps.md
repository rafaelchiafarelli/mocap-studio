# The walk jumps at every step

- **Symptom:** Rafael (2026-11-03): "the animation is jumpy... there is some error somewhere that made the model jump".
- **Where:** `human-model/blender/walk.py`, root solve. The root takes its height and forward motion from whichever foot point is lowest, with no smoothing.
- **Measured:** twice per cycle, height steps up to 27 mm in one frame (median 8) and forward motion up to 72 mm in one frame (median 45), just after each stance foot changes. Total bounce is 6.6 cm. The joint curves aren't the cause: they close at the cycle's wrap with no step.
- **Reproduce:** read `HM_rig`'s location per frame in a file from `walk.py`, or watch `caminhar_masculino_ossos_e_pele.mp4`.
- **Impact:** walking can't get a verdict until this is gone.
- **Cause (2026-11-07):** the data's hip angle is measured against a pelvis tilted about 10° forward, and the rig's pelvis is level, so the thigh flexed 10° too far; with rigid toes as well, the two feet never touched the floor together and the body dropped at each hand-over.
- **Status:** Fixed (2026-11-07) — task `muscle-physics/body-walk/2-plant-feet`: the tilt taken off, toes rolling, a soft contact and each stance foot planted. Height steps at most 8 mm a frame, the planted foot slides 0.3 mm at most (`G:\mocap-studio-downloads\review\2026-11-07\walk_root\`).

# The walk jumps at every step

- **Symptom:** Rafael (2026-11-03): "the animation is jumpy... there is some error somewhere that made the model jump".
- **Where:** `human-model/blender/walk.py`, root solve. The root takes its height and forward motion from whichever foot point is lowest, with no smoothing.
- **Measured:** twice per cycle, height steps up to 27 mm in one frame (median 8) and forward motion up to 72 mm in one frame (median 45), just after each stance foot changes. Total bounce is 6.6 cm. The joint curves aren't the cause: they close at the cycle's wrap with no step.
- **Reproduce:** read `HM_rig`'s location per frame in a file from `walk.py`, or watch `caminhar_masculino_ossos_e_pele.mp4`.
- **Impact:** walking can't get a verdict until this is gone.
- **Measured cause (2026-11-07):** rigid toes lift the body at push-off, and with the measured angles on this body the two feet never touch the floor together, so the body drops when the trailing foot lifts. A soft contact and a smoothed root don't fix it: see task `muscle-physics/body-walk/2-plant-feet`.
- **Status:** Open. Fixed by planting the feet with IK, task [`muscle-physics/body-walk/2`](../../../../muscle-physics/epics/body-walk/tasks/2-plant-feet.md).

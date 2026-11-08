# Walking stride is short

- **Symptom:** stride 1.02 m at a 1.1 s cycle gives 0.93 m/s, while the data's trial averages 1.24 m/s.
- **Where:** `human-model/blender/walk.py`, root solve. The cause isn't proven; hip rotation and the foot roll aren't in the applied angles.
- **Reproduce:** the `stride` line that `walk.py` prints.
- **Impact:** looks like a slower walk than measured.
- **2026-11-07:** with the pelvis's tilt taken off the hip angle and the toes rolling (task `muscle-physics/body-walk/2`), the woman's stride went from 0.90 to 1.14 m (1.04 m/s).
- **Status:** Open.

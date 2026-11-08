# 2. Plant the feet: the walk without the jump

**Asked by Rafael, 2026-11-07** ("IK nos pés"), to fix bug `human-model/5`: the walk jumps at every step, which spoils judging the tissue.

## What's known

Measured on 2026-11-07 (`G:\mocap-studio-downloads\review\2026-11-07\walk_root\`, every run kept with its `.blend` and `_root.json`):

- **The cause isn't the root's hand-over between feet alone.** A soft contact (the lowest foot points share it) cut the planted foot's slide from 12 to 3.9 mm a frame, but the root's height still steps 24 mm in one frame.
- **Rigid toes lift the body.** The data has no toe angle, so at push-off the trailing foot stood on its toes' tips and lifted the root 5 cm at every hand-over. Bending the toes until they lie as they do standing removed that, and the stride went from 0.90 to 1.03 m (the data's trial: 1.24 m, bug `human-model/4`).
- **What's left: the two feet never touch the floor together.** With the measured angles on this body's proportions, the leading heel is still about 4 cm up when the trailing foot leaves the floor, so the body drops 30 mm in one frame.
- **Smoothing the root over the cycle trades one fault for another:** with 4 harmonics the step falls to 13 mm, but the feet float up to 11 mm and slide up to 16 mm.

The soft contact, the toe roll and the smoothing are in `walk_root\walk_experiment_soft-contact_toe-roll_smoothing.patch` (against `human-model/blender/walk.py` on `dev`); the toe roll and the soft contact are meant to be kept.

## Contract

**In:** `human-model/data/gait_walk.json` (the measured joint angles) and a built `<name>.blend`.

**Out:** `human-model/blender/walk.py` writes the same walk file as today (the rig keyed per frame, `hm_walk` with stride, speed and bounce), now with:
- the toes rolling at push-off and the soft contact (from the patch);
- each foot held on the floor while it bears weight, by inverse kinematics on the leg; the measured angles stay the target everywhere else, and the change from them is reported per joint (largest and mean, in degrees);
- both feet on the floor in double support.

**Measured, and reported as measured** (the check in the patch's run, kept as a script): the root's largest height and forward step per frame, the planted foot's slide per frame, the lowest point's height above and below the floor, stride and speed against the data's, and the bounce.

**Done when:** no height step above 10 mm in a frame, the planted foot slides under 2 mm a frame and neither floats nor sinks more than 3 mm, and Rafael's verdict on a video of the walk. The whole body walk is then rerun on it (`body_walk.py`), and the motion per zone compared with `v2_bones-settled`.

## Declared, to be agreed with Rafael on the result

The toes' most bend at push-off: 55° (the measured peak at the ball of the foot is about 50°). The soft contact's width: 4 mm.

## Dependencies

Blender's IK constraint (in the Blender already in use). Bug `human-model/3` (joint limits aren't enforced): the IK has to stay within `hm_limit_deg`, read from the bone properties. No other pre-work: the data and the woman's build exist.

## Out of scope

Hip rotation in the transverse plane beyond the data's pelvis angles, and the man's walk (after the woman's, as agreed).

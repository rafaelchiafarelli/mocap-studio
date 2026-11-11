# 3. The clean body walks

The baseline every later layer is judged against.

## Contract

**In:** the clean body; `blender/walk.py`'s measured cycle.

**Out:**
- The clean body walking from `data/gait_walk.json`, feet planted, in a `.blend` that plays without simulating.
- A new `.blend` per attempt, under a name that says what it holds, in `G:\mocap-studio-downloads\review\<date>\`.

## Agreed and declared

- Check whether `walk.py` runs on the plain MPFB rig: it was written for `HM_rig`. If not, stop and flag it.

## Dependencies

Task `2-proportions-from-targets`.

## Pre-work

None.

## 2. Volume behaviour

- **Type:** code.
- **Depends on:** `muscles/1`
- **Contract:**
  - In: Muscle bodies
  - Requires: Shortening bulges, stretching thins
  - Delivers: Stretch To with `VOLUME_XZX`, `blender/volume_check.py`
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `tests/test_muscle.py`, `blender/volume_check.py`

## Result (2026-11-03)

In five poses for both sexes, every muscle's volume ratio stays within 0.1% of rest, against +34% and -19% in the proof of concept. This is by construction, because Blender's constraint preserves it, and the check confirms the file does what it should. **What it doesn't test:** muscles passing through bone or each other. A muscle's path is straight between points, so it can cut through a joint.

## 1. Muscle builder

- **Type:** code.
- **Depends on:** `skeleton`
- **Contract:**
  - In: `data/muscles.json` (declared from anatomy descriptions); Rajagopal's 80 leg muscles; the fitted skeleton
  - Requires: Origin, insertion and volume per muscle; both sexes from one table
  - Delivers: `hmcore/muscle.py`, `tools/build_muscles.py`, `blender/hmmuscles.py`
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `tests/test_muscle.py`

## Result (2026-11-03)

198 muscles: 80 leg (Rajagopal path points), 50 trunk and arm, 42 face, 18 jaw, 8 tongue. All are spindles: about 7 thousand vertices in total, against about 1 million in Z-Anatomy. **Loss of detail, stated:** no fibers, no fascia, no flat sheet shape, so wide muscles such as trapezius, latissimus and the obliques are single spindles. The trunk looks sparse. Coordinates of trunk, arm, face and jaw are declared from anatomy text, not measured.

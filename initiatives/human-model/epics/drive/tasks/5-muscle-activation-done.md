## 5. Muscle activation

- **Type:** experiment.
- **Depends on:** `muscles/4`
- **Contract:**
  - In: OpenSeeFace landmarks, the take's ARKit shapes
  - Requires: Test the least-effort idea
  - Delivers: `hmcore/activation.py`, `tools/solve_take.py`
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `tests/test_drive.py`

## Result (2026-11-03)

**Least effort works as a regularizer, not as an answer.** 31 landmarks, 44 muscles, 598 frames:

| Effort | Active muscles | Total activation | Residual | Frame-to-frame change |
|---:|---:|---:|---:|---:|
| 0 | 24.6 | 16.7 | 0.73 | 0.83 |
| 1e-5 (chosen) | 10.7 | 6.6 | 0.79 | 0.45 |
| 1e-4 | 2.1 | 1.4 | 0.99 | 0.07 |
| 1e-3 | 0.1 | 0.08 | 1.00 | 0 |

A residual of 0.79 means the muscles reach only part of what the tracker saw. **Fitting ARKit shapes with muscle fields also fails:** residual 0.62 to 1.0 with bounds, 0.49 to 0.86 even without, so none of the 23 active shapes passed the 0.6 limit to be replaced. This answers the plan's first open question for now: a linear muscle basis with these fields doesn't span real facial motion. The fields are too local, and declared.

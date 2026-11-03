## 2. Fit from data

- **Type:** measure.
- **Depends on:** `retirement/1`
- **Contract:**
  - In: 44 fields, the take's activations
  - Requires: Measure before adopting; no model on the RTX 4080 was needed
  - Delivers: `hmcore/retire.py`, `tools/fit_fields.py`
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `tests/test_drive.py`

## Result (2026-11-03)

A linear basis, on CPU. No GPU needed.

| Components | Take RMS | Take max | Stored |
|---:|---:|---:|---:|
| 5 | 0.78 mm | 13.1 mm | 0.5 MB |
| 15 | 0.28 mm | 4.1 mm | 1.5 MB |
| 30 | 0.11 mm | 2.8 mm | 3.0 MB |
| 44 (all) | 0 | 0 | 4.4 MB |

The maximum stays high until nearly all components are in, so a lip or a lid would visibly move. **Recommendation: don't compress:** 44 keys cost little. No learned model was fitted, because there's no training data better than this basis.

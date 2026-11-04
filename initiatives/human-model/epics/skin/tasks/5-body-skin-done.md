## 5. Body skin

- **Type:** code.
- **Depends on:** `muscles/7`
- **Contract:**
  - In: Muscle list
  - Requires: —
  - Delivers: `hmcore/bodyskin.py`: breath, biceps, triceps, deltoid shapes
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

Breath moves chest and belly from one control. Biceps, triceps and deltoid bellies swell from joint angle, through `ROTATION_DIFF` drivers. **The bumps are declared shapes, not computed from the muscle body,** and the elbow and shoulder shapes weren't checked in a render. Abdomen compression when bending and elbow-crease collapse aren't done: the skin still deforms by MPFB's weights there.

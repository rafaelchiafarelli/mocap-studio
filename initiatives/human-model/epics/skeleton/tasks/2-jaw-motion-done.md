## 2. Jaw motion

- **Type:** code.
- **Depends on:** `skeleton/1`, `references/4`
- **Contract:**
  - In: Condyles and lower incisor from the fit
  - Requires: Rotation, then rotation with sliding; Travers 2000 targets
  - Delivers: `hmcore/jaw.py`, driven from `HM_controls["jaw_open"]`; hyoid and head follow
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `tests/test_jaw_joints.py`

## Result (2026-11-03)

Reaches the 46.6 mm opening with 11.9 mm slide. Rotation 32° male, 38.5° female; the incisor ends 23 mm behind where it started, against 36 mm in the proof of concept. Female rotation is as high as the proof of concept's, because the female jaw is shorter and the target isn't scaled by size. **Declared, no source:** pure rotation ending at 20 mm, eminence angle 35°, hyoid follow, 4° of head extension.

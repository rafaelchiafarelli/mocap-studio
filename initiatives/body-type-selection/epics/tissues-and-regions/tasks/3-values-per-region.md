# 3. Physical values per region

Every physical quantity per region (Rafael, 2026-11-08).

## Contract

**In:** tasks 1 and 2.

**Out:**
- `data/body_tissue.json` keeps one default per tissue and takes overrides by tissue and zone, for stiffness, Poisson's ratio, density and damping.
- Damping becomes per tetrahedron's node in `hmcore/xpbd.py`.
- Values change smoothly between zones, as the fat thickness does. With no overrides the motion is the same as today's: tested.

## Dependencies

Task 2.

## Pre-work

None.

**Status:** Done (2026-11-08).

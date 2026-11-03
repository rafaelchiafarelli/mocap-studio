## 3. Spine, ribs and breathing

- **Type:** code.
- **Depends on:** `skeleton/1`
- **Contract:**
  - In: CT vertebrae, ribs, sternum, cartilages
  - Requires: Each rib its own joint
  - Delivers: 24 rib bones, sternum bone, `breath` control, `blender/breath_check.py`
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `blender/breath_check.py`

## Result (2026-11-03)

Every vertebra is placed from the back's skin. Ribs rotate on their own bones, pump handle above and bucket handle below, at 9° for a deep breath (declared). Measured chest expansion at a full breath: 4.0 cm male, 5.0 cm female. **Limit:** cartilages move with the sternum as one rigid piece, so they don't bend; no spine bending rule is enforced.

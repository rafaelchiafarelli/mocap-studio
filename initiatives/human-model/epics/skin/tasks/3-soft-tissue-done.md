## 3. Soft tissue

- **Type:** code.
- **Depends on:** `muscles/4`, `references/4`
- **Contract:**
  - In: Retaining ligaments from the literature
  - Requires: —
  - Delivers: Anchors in `hmcore/softtissue.py`: zygomatic, mandibular, masseteric, orbital; bulge from conserved volume
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** `tests/test_softtissue.py`

## Result (2026-11-03)

Ligaments are soft anchors, and their positions are declared near the rig's landmarks rather than placed by the cadaver study's distances. **Fascia and separate fat compartments aren't modeled:** the bulge is a surface rule that acts like fat. The nasolabial fold comes out of these anchors, without being modeled directly.

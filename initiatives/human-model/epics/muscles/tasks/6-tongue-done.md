## 6. Tongue

- **Type:** code.
- **Depends on:** `muscles/1`
- **Contract:**
  - In: MPFB tongue asset and the rig's three tongue bones
  - Requires: Own controls
  - Delivers: Controls `tongue_tip_raise`, `tongue_body_raise`, `tongue_back_raise`, `tongue_protrude`; 4 extrinsic muscle bodies
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

**Research:** intrinsic longitudinal, transverse and vertical muscles shape it; genioglossus, hyoglossus, styloglossus and palatoglossus move it. Intrinsic muscles aren't modeled: the tongue bends with three bones, so it can't groove or narrow. The tongue is a muscular hydrostat, and this is the biggest simplification in the head.

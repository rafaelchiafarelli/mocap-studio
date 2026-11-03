## 2. Tissue experiment

- **Type:** experiment.
- **Depends on:** —
- **Contract:**
  - In: Tissue 0.3.76 (GPL-3.0+), a skin patch
  - Requires: —
  - Delivers: `blender/tissue_experiment.py`; a recommendation
- **Pre-work:** Add-on in `apps/tissue/0.3.76/`
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

**Inconclusive.** It installs and enables on Blender 5.2.2 and exposes `tissue_tessellate`, but the operator returned CANCELLED in headless mode, on a patch that came out at only 8 faces. It wasn't tried in the interface, and no pattern was rendered. **Recommendation:** don't use Tissue for micro relief: it repeats geometry per face, and pores on a skin of about 13 thousand faces would cost millions. Normal or displacement maps do this job. A note for Rafael: it's now installed in the portable Blender.

## 1. Head bones

- **Type:** code.
- **Depends on:** `references/1`
- **Contract:**
  - In: TotalSegmentator donors s1045 (male, 62, no pathology) and s0933 (female, 55, recorded bleeding, polytrauma scan), BMF, Rajagopal, MPFB skin and rig
  - Requires: Every bone rigid apart from scale; license rule
  - Delivers: `hmcore/skeleton.py` fits the whole library, including cranium, mandible, hyoid, larynx; teeth, tongue and eyes are MPFB's CC0 assets
- **Pre-work:** CT labels fetched by byte range; BMF and Rajagopal on G:
- **Out of scope:** —
- **Tests:** `tests/test_fit.py`, `tests/test_measures.py`

## Result (2026-11-03)

Both skulls fit without manual repair. The dataset's `skull` label holds the mandible, so `ctbones.split_mandible` separates them by watershed. The cranium's tilt is solved so its socket reaches the rig's jaw hinge. **Limits:** 1.5 mm CT: thin facial bones are lumpy, no separate teeth in the bone. Hyoid and larynx are parametric shapes because no allowed mesh was found. The donor's jaw is levelled and centred, so its natural asymmetry is lost.

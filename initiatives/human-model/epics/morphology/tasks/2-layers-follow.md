## 2. Layers follow

- **Type:** code.
- **Depends on:** `skeleton`, `muscles`, `skin`
- **Contract:**
  - In: Six test people
  - Requires: —
  - Delivers: The same build for any recipe
- **Pre-work:** —
- **Out of scope:** —
- **Tests:** —

## Result (2026-11-03)

Bones, muscles and fields are all recomputed from the individual's skin and rig, so they follow by construction.

**Check, three of each sex, no manual repair:** all six build. In 14 poses each, the only overlaps are between bones meeting at the joint being posed. Muscle volume held within 0.1%. **Fault:** about 47% of the sacrum's sampled vertices fall outside the skin in the male builds, and 33 to 38% of the fibula in some. Mean across all bones, 19 to 24%, mostly the small bones of hands and feet, whose skin is thin and whose check is noisy. The fibula figure and these means weren't investigated further. See bug `human-model/2`. Images: `seis_individuos_pele.png`, `seis_individuos_ossos_musculos.png`.

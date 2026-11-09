# 27. New path: scapulae come through the skin at rest

**Symptom:** on the new path (`fast_review.py --character`), the woman's right scapula comes 10.7 mm through the skin at rest (392 points), the left 3.3 mm, the clavicle 1.3 and the tibiae 3 to 4; the man's scapula 1 mm. Today's path has none at rest.
**Where:** `human-model/tools/outward_skin.py`, search `SKIN_OVER_LAYERS`; the scapula placed from the targets, without `settle_superficial`, in `human-model/hmcore/skeleton.py`.
**How to reproduce:** `<run>/<sex>/layers/*.body_layers.json`, `bones_with_points_outside_skin`, of `t2_neutro` (2026-11-09).
**Impact:** the acceptance gate of `body-type-selection` asks for no bone through the skin at rest.
On `t5_*` (2026-11-09), by muscle bodies: neutral woman 2,222 bone points out, up to 14.6 mm (scapulae); neutral man 351, up to 7.6 mm. Others from 21 to 2,633.
**Status:** Open

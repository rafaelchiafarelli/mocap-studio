# muscle-physics — epics

1. `single-muscle`: done (2026-11-05).
2. `thigh`: done (2026-11-07). Rafael: "a coxa está definida"; his values are the defaults in `human-model/data/thigh_tissue.json`.
3. `body-at-rest`: done (2026-11-07). The whole woman in layers, standing still: the zero point for body shapes. Rafael: "ok".
4. `inside-out-skin`: done (2026-11-07). The skin pushed out over the bones; 24 of 28 covered, 4 misplaced bones left alone.
5. `leg-walk`: done (2026-11-07). The woman's lower body walking; bug 9 doesn't happen. Rafael: the parameters still need tuning, but moving on matters more now.
6. `body-walk`: the whole woman walking. Task `1-whole-body-walk` (done 2026-11-07; on settled bones, Rafael: "Parece bom"). Task `2-plant-feet` (done 2026-11-08): the pelvis's tilt taken off the hip, toes rolling, feet planted; the walk stops jumping (bug `human-model/5`). Rafael: "Ficou ok, bem melhor agora". Gate: Rafael's verdict on the videos, given for both.

**Agreed next** (Rafael, 2026-11-07): the leg and hip walking, where bug `human-model/9` shows; then the whole body walking. The man after the woman.

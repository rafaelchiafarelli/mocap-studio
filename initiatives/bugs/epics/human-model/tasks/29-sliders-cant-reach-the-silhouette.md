# 29. The sliders can't reach some silhouettes

**Symptom:** the first shape stops at the sliders' limit (0.8): the oval woman's waist is 14.6 cm short of the target, the man's 11.0, the rectangle woman's 8.3, the short endomorph's 4.7. The fat keeps the shape they did reach.
**Where:** `human-model/hm_editor/human.py`, `SLIDER_LIMIT`, used by `human-model/blender/character_shape.py`.
**How to reproduce:** `<run>/<sex>/shape.json`, `asked_cm` against `reached_cm`, of `t2_oval` (2026-11-09).
**Impact:** those silhouettes are less marked than asked.
**Status:** Open

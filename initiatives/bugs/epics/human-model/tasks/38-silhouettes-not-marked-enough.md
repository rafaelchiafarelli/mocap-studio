# 38. New path: the silhouettes differ too little

**Symptom:** "the difference has to be more marked" (Rafael, 2026-11-09, on `t5_*`). Bug 29 is part of it: the sliders stop short of the waists asked for.
**Where:** `human-model/data/silhouette_ratios.json` (targets applied only when a ratio is out of range), `human-model/hmcore/character.py` `_ratio_towards`, `human-model/hm_editor/human.py` `SLIDER_LIMIT`.
**Impact:** the eight bodies look too alike.
**Status:** Open

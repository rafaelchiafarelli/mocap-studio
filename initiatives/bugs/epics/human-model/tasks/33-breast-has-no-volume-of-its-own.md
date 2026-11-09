# 33. New path: the breast has no volume of its own

**Symptom:** the breasts look unmodelled, as if their volume stayed inside the rib cage.
**Where:** `human-model/tools/outward_skin.py`: the skin at the breast stays on the first shape (apex y -0.159 to -0.158 on the neutral woman). `data/muscle_mm_female.json`, `breast_L`: 31.6 mm. Through the apex, front to back: skin band 1 cm, fat 1 cm, gland 1.5 cm, muscle 2.5 cm, then the cavity. The cup only scales a thin fat layer.
**Impact:** no cup or breast shape produces a breast.
On `t5_neutro` (2026-11-09), the volume built from the cup: through the apex, skin 1 cm, fat 1 cm, gland 5 cm. Rafael hasn't judged it yet.
**Status:** Open

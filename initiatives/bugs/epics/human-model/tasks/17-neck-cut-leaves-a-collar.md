# The neck's cut leaves a ragged collar under the chin

- **Symptom:** the layered body keeps a strip of skin from the jaw's underside, a ragged collar at the neck's cut.
- **Where:** `human-model/hmcore/body.py`, `cut_skin`: the neck's plane is at the head's base, and the chin's underside lies below it.
- **Reproduce:** `08_body_layers_zones.png` in `G:\mocap-studio-downloads\review\2026-11-07\body_v4_belly-beside-spine\`.
- **Impact:** cosmetic now; the face will need a clean join when it's simulated with the body.
- **Status:** Fixed (2026-11-07) — fixes/0000d3/neck-cut-collar. `body.cut_skin` drops the vertices the rig moves mostly with `spine.006` and the bones under it, so the cut follows MPFB's own border under the jaw. The neck's top is now 1,423 mm in front and 1,442 behind (the plane left the chin's underside up to 1,444 and 78 mm forward). Before and after: `G:\mocap-studio-downloads\review\2026-11-07\body_v7_neck-cut-by-weights\13_pescoco_antes_depois.png`.

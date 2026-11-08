# The neck's cut leaves a ragged collar under the chin

- **Symptom:** the layered body keeps a strip of skin from the jaw's underside, a ragged collar at the neck's cut.
- **Where:** `human-model/hmcore/body.py`, `cut_skin`: the neck's plane is at the head's base, and the chin's underside lies below it.
- **Reproduce:** `08_body_layers_zones.png` in `G:\mocap-studio-downloads\review\2026-11-07\body_v4_belly-beside-spine\`.
- **Impact:** cosmetic now; the face will need a clean join when it's simulated with the body.
- **Status:** Open. Likely fix: cut along MPFB's own head and neck border instead of a plane.

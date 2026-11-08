# Four bones sit too far out to cover: right scapula, left clavicle, both fibulae

- **Symptom:** after the skin is pushed out over the bones (`tools/skin_over_bone.py`), four bones would still need more than the 15 mm most push, so they're left alone and stay through the skin: right scapula (31 mm needed; the left one needed 11.6), left clavicle (15.2; the right one 10.4), fibulae (15.3 each, near the ankle). They're the only bones through the skin in the walking lower and whole body (`body_walk/v1_whole-body`: up to 29.9 mm, the scapula).
- **Where:** `human-model/hmcore/skeleton.py`, each bone's placement. The left and right sides differ far more than a body does, so the fit, not the skin, is off.
- **Reproduce:** `bones_misplaced_left_alone` in `<name>.skin_fit.json` (`G:\mocap-studio-downloads\review\2026-11-07\skin_v4_along-skin-normal\`), or `bone_through_skin.ours_bones` in `body_walk.json`.
- **Impact:** the scapula makes a hump-free but pierced back; the layered body can't cover these four.
- **Status:** Open. Likely fix: place them from the skin as the vertebrae are, mirrored from the better side. Related: bugs 2 and 10.

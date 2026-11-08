# The heavy, short man's pelvis stays through the skin, and his fibulae can't settle

- **Symptom:** on the test person `male_heavy_short`, the first body away from neutral built with the 2026-11-08 fixes: the pelvis moves 32.5 mm forward and tilts -7.8°, and still lacks 11.7 mm of tissue. The sacrum ends with 0 mm (6 wanted), and the left hip bone is left alone as misplaced by the skin push. The fibulae are 12.2 mm short after settling.
- **Where:** `human-model/hmcore/skeleton.py`, search `pelvis_names`: the pelvis's move is limited to 40 mm forward and 10° of tilt. Why this body needs more isn't known.
- **Reproduce:** `anchors.pelvis_move` and `anchors.settled` in `models\hm-build\male_heavy_short_2026-11-08_current-code\male_heavy_short.bones.npz.json`; `review\2026-11-08\skin_male_heavy_short_v1\`.
- **Impact:** bodies away from neutral build, but may keep bones through the skin (initiative `body-type-selection`).
- **Status:** Open.

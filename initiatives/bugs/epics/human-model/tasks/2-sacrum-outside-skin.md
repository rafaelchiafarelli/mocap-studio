# Sacrum partly outside the skin in male builds

- **Symptom:** about 47% of the sacrum's sampled vertices fall outside the skin in the male test people; up to 37% of the fibula in some builds.
- **Where:** `human-model/hmcore/skeleton.py`, pelvis map: its depth isn't checked against the back's skin.
- **Reproduce:** `<name>.bones.npz.containment.json` of a male build.
- **Impact:** hidden in renders, because only skin renders with skin on. It would show if the bones were displayed through the skin, and it means the pelvis sits too far back.
- **Also on the woman (2026-11-07):** 5.1 mm out at rest, and after the skin is pushed over the bones it still reaches the skin (0 mm of tissue) in the cleft between the buttocks (`docs/muscle-physics.md`, experiment 5).
- **Cause (2026-11-08):** scaled from the hips alone, the pelvis sat 2 to 3 cm behind the spine: the sacrum stood 20 to 24 mm behind L5.
- **Status:** Fixed (2026-11-08) — fixes/0000d7/sacrum-outside-skin. The pelvis moves forward, and may tilt about the sockets, until 6 mm of tissue covers sacrum and crests; the hip joints go with it. Woman: 20 mm forward, sacrum 1.9 mm at worst (0.7% of its points under 6 mm, was 4.8 mm out); man: 33 mm and 9°, sacrum 4.5 mm (was 22 mm out, 38% of it); L5 to sacrum 6 mm in both. Every attempt: `models\hm-build\{female,male}_bug2_*`.

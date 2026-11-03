# Sacrum partly outside the skin in male builds

- **Symptom:** about 47% of the sacrum's sampled vertices fall outside the skin in the male test people; 34 to 38% of the fibula in some builds.
- **Where:** `human-model/hmcore/skeleton.py`, pelvis map: its depth isn't checked against the back's skin.
- **Reproduce:** `<name>.bones.npz.containment.json` of a male build.
- **Impact:** hidden in renders, because only skin renders with skin on. It would show if the bones were displayed through the skin, and it means the pelvis sits too far back.
- **Status:** Open. Likely fix: move the pelvis forward from the back's skin, as the vertebrae do.

# Superficial bones come through the skin at rest: larynx, tibiae, patellae, hip bones, sacrum

- **Symptom:** on the neutral woman standing still, bones lie outside the skin where they are close under it in a person. Deepest point outside, per bone: right scapula 27.1 mm (left 7.6 mm), larynx 11.4, left clavicle 11.2 (right 6.4), fibulae 11.3, tibiae 9.9, patellae 8.7, right hip bone 7.1 (left 4.4), sacrum 5.1, a few thoracic spinous processes under 4.
- **Where:** `human-model/hmcore/skeleton.py`: each bone is placed rigidly and scaled, then MPFB's skin is laid over nothing; no step keeps a minimum of tissue over a bone. The right scapula's misfit is far larger than the left's, so its own placement is also off.
- **Reproduce:** `hm.sh --gpu python human-model/tools/body_layers.py <build dir> female OUT`, then `bones_with_points_outside_skin` in `OUT/female.body_layers.json`. Measured on 2026-11-07 in `G:\mocap-studio-downloads\review\2026-11-07\body_v2_cuts-apart\`. Bones past the neck, wrist and ankle cuts are counted apart.
- **Impact:** the layered body can't put skin over them; walking only adds to it (bug 9). Includes bug 2's sacrum, here on a woman too.
- **2026-11-07:** the scapulae, clavicles and fibulae are now placed with 4 mm of tissue, or within 3 mm of it (bug 12, fixed); the others above are still as listed.
- **Status:** Open. Building the skin from the inside out, with a least tissue depth over each bone, is the planned way round it.

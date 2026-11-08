# Bones come through the skin at the thigh and upper arm when walking

- **Symptom:** skin vertices whose nearest bone point lies outside the skin, at rest and at worst over a walk: thigh 2 to 97 (female), 0 to 106 (male); upper arm 5 to 75 (female), 11 to 103 (male). Rafael suspected it from the rig: "parece que a pele vai grudar nos ossos".
- **Where:** `human-model/blender/assemble.py`: bones are rigid on the rig, and skin follows MPFB's weights alone, with nothing keeping it off them.
- **Reproduce:** `walk_clearance.py` on a file from `walk.py`. A number, not yet seen in a render; the check is noisy where skin is thin, such as head and fingers, and it doesn't cover the hip.
- **Impact:** with the missing soft tissue, part of why the body looks stiff.
- **Status:** Fixed (2026-11-07) — fixes/0000d4/bones-through-skin-walking, by the layered body, which replaces skin that follows the rig's weights alone. The whole woman walking in layers, on bones settled under the skin (bug 12), has no bone through the skin in any frame (`G:\mocap-studio-downloads\review\2026-11-07\body_walk\v2_bones-settled\`). Rafael chose to close it so (2026-11-07). The built `.blend` still deforms its skin by weights alone until it uses the simulated skin.

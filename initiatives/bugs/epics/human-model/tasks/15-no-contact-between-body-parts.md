# Body parts pass through each other: no contact in the simulation

- **Symptom:** in the walking simulations the thighs can pass into each other, and the arms into the trunk; nothing stops them, and it isn't measured.
- **Where:** `human-model/hmcore/xpbd.py`: the solve has a floor, but no collision between parts of the tissue.
- **Reproduce:** `body_walk_v1_compare.mp4` in `G:\mocap-studio-downloads\review\2026-11-07\body_walk\v1_whole-body\`, inner thighs at mid stance.
- **Impact:** visible on bodies with full thighs, and wherever arms swing close to the body.
- **Status:** Open. Likely fix: skin against skin contact on the GPU (Warp's mesh queries), as a constraint in each substep.

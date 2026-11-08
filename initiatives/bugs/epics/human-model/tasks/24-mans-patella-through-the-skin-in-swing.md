# The man's patella and tibia top come through the skin in each swing

- **Symptom:** in the man's walk the patellae come up to 4.5 mm through the skin at 62° of knee bend, in 7 frames of each swing (`body_walk_frames.csv`), and a few points of the tibia's top with them. At rest the patella has 4.8 mm of tissue. The woman's, with 3.3 mm at rest and the same motion, stays covered (1.3 mm at the least).
- **Where:** the patella turns exactly half the knee's bend in both (31° of 61 to 62°), so `human-model/blender/assemble.py`'s `PATELLA_SHARE` isn't the difference. Not found yet. The rig's knee joint is 4.6 cm behind the patella's front on the man and 2.4 on the woman, so the same turn carries his patella further; a hypothesis, not tested.
- **Reproduce:** winding number of `patella_L`, moved by `transforms` of `review\2026-11-08\body_walk_male_v1\body_walk.npz`, against that frame's skin.
- **Impact:** visible in deep knee bends, as bug 19 was on the woman.
- **Status:** Open.

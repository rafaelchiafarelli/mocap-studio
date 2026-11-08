# The patella follows the shin rigidly and touches the skin in swing

- **Symptom:** in the whole body walk on planted feet, the patellae come up to 1.8 mm through the skin in 4 frames of each leg's swing, when the knee bends about 60° (`body_walk_frames.csv`, frames 6–9 for the left, 19–22 for the right, every cycle). No other bone does.
- **Where:** `human-model/hmcore/skeleton.py`: the patella is parented to `shin.<side>` and turns with it; in a person it slides in the femur's groove, about halfway between the two.
- **Reproduce:** `bone_through_skin` in `body_walk.json`, `G:\mocap-studio-downloads\review\2026-11-07\body_walk\v3_feet-planted\` (found 2026-11-07, task `muscle-physics/body-walk/2`). The earlier walk, with the thigh 10° too far forward, didn't show it.
- **Impact:** small now (its declared tissue is 3 mm); it grows with deeper knee bends, such as sitting or climbing stairs.
- **Status:** Fixed (2026-11-08) — fixes/0000db/patella-follows-the-shin. The patella turns by half the knee's bend (`hm_patella.<side>`); in the walk no bone comes through the skin

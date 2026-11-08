# Tetrahedra turn inside out at the knees and hips while walking

- **Symptom:** up to 2,365 of 2.4 million tetrahedra (0.1%) have a negative volume in a frame of the whole body's walk; 2,339 of 1.4 million (0.17%) in the lower body's. They're where tissue lies between two bones that bend toward each other.
- **Where:** `human-model/tools/body_walk.py`: each node follows its nearest bone, so the tissue at a joint is pulled by two rigid bodies at once, and the 5 mm voxels can't fold.
- **Reproduce:** `inverted_tetrahedra` per frame in `body_walk_frames.csv` (`G:\mocap-studio-downloads\review\2026-11-07\leg_walk\v2_region-bones-only\`, `body_walk\v1_whole-body\`).
- **Impact:** small now; it can make the solve unstable at deeper bends (sitting, squatting) and shows as creases that fold through themselves.
- **Status:** Open. Likely fix: finer tetrahedra at the joints, or blending a joint's nodes between its two bones.

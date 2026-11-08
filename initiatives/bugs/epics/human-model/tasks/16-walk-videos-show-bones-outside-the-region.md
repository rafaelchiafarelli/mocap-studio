# The walk's section video shows bones outside the simulated region

- **Symptom:** `body_walk_v1_inside.mp4` shows the cranium floating above the neck, and the hands' bones beside the cut wrists, though neither head nor hands are simulated.
- **Where:** `human-model/blender/body_walk_bake.py`: it animates every bone that holds some of the region's voxels, and the cranium and wrist bones hold the voxels at the cuts.
- **Reproduce:** the section video of any whole body run.
- **Impact:** cosmetic; it looks like a skull detached from the body.
- **Status:** Fixed (2026-11-08) — fixes/0000e8/walk-videos-and-tissue-measure. Bones mostly past the neck's or a wrist's cut are left out of the section; the feet stay, driven by the rig, with their skin (Rafael's choice).

# fast-review

**Goal:** one command that rebuilds the man and the woman and leaves them in one Blender file, with no rendering unless asked (Rafael, 2026-11-08). Today each change takes a chain of steps by hand, and most of the waiting is renders nobody asked for.

**Status:** to be planned. Rafael wants it first in the next session.

## What Rafael asked for

- **Models without rendering:** everything ends in Blender. Videos and stills only when requested.
- **In the Blender file:** the man and the woman, each with the outer body and the inner one (bones and layers), so that either can be switched off to look at the other.

## What exists to build on

- `human-model/blender/body_walk_pair.py` joins two walked bodies in one file: four collections, skin and section for each, a metre apart.
- `human-model/blender/body_walk_bake.py` makes the file only when its frames folder is `-`.
- `human-model/tools/hm_status.py` shows what is running.
- The chain, per body: `build_model.py RECIPE OUT --from bones`, `tools/skin_over_bone.py`, `tools/body_layers.py SKIN=`, `blender/walk.py gait_walk.json SEX OUT 4 2` (the last 2 are the steps of the slow stop), `blender/body_walk_dump.py`, `tools/body_walk.py ABOVE_HIP=10`, `blender/body_walk_bake.py`. The commands are in `human-model/docs/muscle-physics.md`.

## To work out when planning

- **Run the two bodies side by side.** The machine has room (28 threads, under a third of the GPU's memory in use); most of the time is the bones on the CPU and Blender. Each stage only needs the one before it, for its own body.
- **Skip what didn't change:** a change to the tissue values needs only the simulation and the file, not the bones.
- **Where results go,** with names that say what they are, since every attempt is kept.
- **Moving the section:** the inner view is a fixed half today. A plane to drag belongs to initiative `xray-view`.

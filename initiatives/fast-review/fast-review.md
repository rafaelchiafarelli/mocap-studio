# fast-review

**Goal:** one command that rebuilds the man and the woman and leaves them in one Blender file, with no rendering unless asked (Rafael, 2026-11-08). Today each change takes a chain of steps by hand, and most of the waiting is renders nobody asked for.

**Status:** built on branch `fast-review`, carried into `body-type-selection`, not merged into `features`: epics and tasks in [epics/](epics/README.md). The gate is Rafael opening the file.

## What Rafael asked for

- **Models without rendering:** everything ends in Blender. Videos and stills only when requested.
- **In the Blender file:** the man and the woman, each with the outer body and the inner one (bones and layers), so that either can be switched off to look at the other.

## What exists to build on

- `human-model/blender/body_walk_pair.py` joins two walked bodies in one file: four collections, skin and section for each, a metre apart.
- `human-model/blender/body_walk_bake.py` makes the file only when its frames folder is `-`.
- `human-model/tools/hm_status.py` shows what is running.
- The chain, per body: `build_model.py RECIPE OUT --from bones`, `tools/skin_over_bone.py`, `tools/body_layers.py SKIN=`, `blender/walk.py gait_walk.json SEX OUT 4 2` (the last 2 are the steps of the slow stop), `blender/body_walk_dump.py`, `tools/body_walk.py ABOVE_HIP=10`, `blender/body_walk_bake.py`. The commands are in `human-model/docs/muscle-physics.md`.

## What the simulation costs (measured 2026-11-08)

The table is in `human-model/docs/muscle-physics.md`, section "Where a walk's time goes". With the new defaults (5 mm, volumes every 10 frames), a simulation takes 3 to 3.5 minutes instead of 8.5.

The bone test is off by default, to generate faster, and is asked for on one body when a bump shows (`BONE_TEST=1`, Rafael, 2026-11-08). A "safe rule" that would replace it is left for later.

## Notes from planning

- **Run the two bodies side by side.** The machine has room (28 threads, and two simulations at once used about 400 MB of the GPU's memory). Bones take about 11 minutes per body and, in the redesign (`body-type-selection`), are calculated once, when the character's design is finished, so they aren't part of a usual round. Each stage only needs the one before it, for its own body.
- **Skip what didn't change:** a change to the tissue values needs only the simulation and the file, not the bones. Decided (Rafael, 2026-11-08): the command is told the stage to start from and the earlier run to reuse; it doesn't detect changes, and the run notes where each part came from.
- **Where results go,** with names that say what they are, since every attempt is kept. Rafael (2026-11-08) asked for every run in one Blender file, each with its nickname, given on the command line, as text floating over the model. Decided (2026-11-08): each run keeps its own file (855 MB) and the shared file links to them. Whether links play the walk, and how much memory they take, is to be tested with two runs first; if they don't work, the runs are copied in. The walk moves about 6 m along Y, so runs sit side by side along X.
- **The simulation's stages will change** if the body's construction is redesigned (`body-type-selection`), so the front of the chain must be replaceable.
- **Moving the section:** the inner view is a fixed half today. A plane to drag belongs to initiative `xray-view`.

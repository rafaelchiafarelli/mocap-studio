# 1. One command runs one body

Today each change is a chain of commands by hand (`initiatives/fast-review/fast-review.md`).

## Contract

**In:** a nickname, a sex, the recipe in `human-model/data/recipes/`, and `NAME=value` overrides.

**Out:**
- `human-model/fast_review.py NICKNAME --body female|male [NAME=value ...]`, run from WSL like `build_model.py`, with the stages in order: `build` (`build_model.py`), `tape` (`blender/body_tape.py`), `skin` (`tools/skin_over_bone.py`), `layers` (`tools/body_layers.py SKIN=`), `walk` (`blender/walk.py gait_walk.json SEX OUT 4 2`), `dump` (`blender/body_walk_dump.py`), `simulate` (`tools/body_walk.py ABOVE_HIP=10`), `file` (`blender/body_walk_bake.py` with `-` as the frames folder).
- Overrides go to the stage that knows them: `VOXEL` and `fat.*` to `layers`, `depth.*` to `skin`, the tissue values, `VOLUME_EVERY` and `BONE_TEST` to `simulate`. An override no stage knows stops the run before it starts.
- Results in `G:\mocap-studio-downloads\review\<today>\fast_review\<nickname>\<sex>\`; a nickname already used that day is refused, so nothing is overwritten.
- `run.json` in that folder: the commit, the recipe, the overrides, and each stage's seconds and output.
- `tools/hm_status.py` also shows these runs.
- Tests of the pure parts (stage order, routing of overrides, refusing a used nickname); one real run of the woman.

## Agreed and declared

- No rendering (Rafael, 2026-11-08).
- Python, not shell.
- The default settings come from `data/simulation.json`.

## Dependencies

None.

## Pre-work

None.

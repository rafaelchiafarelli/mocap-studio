# 4. Re-run the walking thigh with other values, in one command

**Asked by Rafael, 2026-11-07,** after seeing `thigh_walk_v5`: "mostra que tem futuro", but it looks like cartoon jelly, so the damping has to go up somewhere. He wants to change the values and run it again himself.

## Contract

**In:** a run name and `NAME=value` overrides of `tools/thigh_walk.py`'s constants.

**Out:**
- `human-model/thigh_run.sh NAME [NAME=value ...]`: simulate, bake, render and encode, into `G:\mocap-studio-downloads\review\<today>\thigh_walk\<NAME>\`, with both videos. Stops if the folder exists, so no run is overwritten.
- `tools/thigh_walk.py` defaults to 160 steps per frame, the converged value.
- `docs/muscle-physics.md`: what each value does, and Rafael's verdict on v5.

## Dependencies

Tasks 1 to 3. The thigh layers and the walk dump from 2026-11-07, on `G:`.

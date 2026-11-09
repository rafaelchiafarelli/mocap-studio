# 1. The walk holds at its end, and the file can be navigated

Bugs `human-model/30` and `31`, seen by Rafael in the first eight bodies.

## Contract

**In:** `blender/body_walk_bake.py`, `blender/shared_file.py`.

**Out:**
- The skin stays on its last frame past the end of the walk, as the bones do.
- The shared file's timeline ends where the runs end; runs fill the first free strip from X = 0; the saved views look at the first strip; the sections are off by default, as they hold most of the triangles.

## Dependencies

None.

## Pre-work

None.

**Status:** Done (2026-11-09); both are Blender behaviour, exercised by the run of task 5.

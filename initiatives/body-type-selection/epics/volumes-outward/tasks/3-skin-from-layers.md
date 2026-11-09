# 3. The skin as the result of the layers

The hybrid path: the current sliders give the first shape from the measures (`human.fit_measures`), and the layers set the skin's final position.

## Contract

**In:** the first shape, and task 2's outer surface.

**Out:**
- The same 13,380 skin points and the same rig, moved to lie on the layers' outer surface.
- Fit fixes that aren't needed any more are listed; none removed yet.

## Agreed and declared

- No sculpting (2026-11).

## Dependencies

Task 2.

## Pre-work

None.

## Stop and bring to Rafael if

- Points can't reach the surface without tearing or folding the mesh.

**Status:** Done (2026-11-08), unit-tested on pure parts; tools/outward_skin.py reports triangles turned over, the stop condition of this task, and hasn't run on a body yet, by Rafael's instruction. Fit fixes no longer needed are listed in human-model/docs/muscle-physics.md.

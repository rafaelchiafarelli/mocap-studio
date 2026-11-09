# 2. Both bodies, side by side, in one Blender file

The goal of the initiative: the man and the woman, outer and inner body, each switchable, in one file.

## Contract

**In:** task 1's single-body run.

**Out:**
- `fast_review.py NICKNAME` with no `--body` runs both, side by side.
- `blender/body_walk_pair.py` then writes `<nickname>\mulher_e_homem.blend`, with the skin and the section of each as switchable collections.
- If one body fails the other finishes, the pair file isn't made, and the command says which stage failed and where its log is.
- `run.json` at the run's top records both bodies and the total time.

## Agreed and declared

- Bones and Blender run in parallel too; each body only waits for its own previous stage.

## Dependencies

Task 1.

## Pre-work

None.

**Status:** Done (2026-11-08), unit-tested; not run on real bodies in this session, by Rafael's instruction.

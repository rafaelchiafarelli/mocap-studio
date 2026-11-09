# 3. Live preview of the gluteus

## Contract

**In:** `data/gluteus_shapes.json`, `data/body_fat_<sex>.json`, the body in the scene.

**Out:**
- The zone of each of the 13,380 skin vertices, once per sex, from a built neutral body (`hmcore/body.py` knows it; a scene body has no rig), as a data file. Same topology, so it serves every body.
- The gluteus on a shape key, as the breast: each zone's skin moves by the fat it gains or loses, `fat_mm x (factor - 1)`, smoothed across zones. Same table as the build.

## Agreed and declared

An approximation: the build grows the fat from the muscle. The file's result stays the truth.

## Dependencies

Task 2.

## Pre-work

A built neutral body of each sex, already on `G:`.

**Status:** Not started.

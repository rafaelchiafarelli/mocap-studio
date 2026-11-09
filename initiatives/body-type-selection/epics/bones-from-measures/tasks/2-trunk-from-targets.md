# 2. Spine, ribs and pelvis from the targets

`hmcore/skeleton.py` reads the skin to place the spine, the rib cage and the pelvis.

## Contract

**In:** task 1's targets and the CT bone library.

**Out:**
- `skeleton.build` takes targets for the trunk in place of reading the skin; the same `<name>.bones.npz`, so later stages don't change.
- Today's way stays available until epic `acceptance` passes.
- On the two neutral bodies: the bones' sizes and positions against today's.

## Dependencies

Task 1.

## Pre-work

None.

## Stop and bring to Rafael if

- The rig (the joints MPFB gives) can't follow bones placed this way: the hybrid path needs rethinking.

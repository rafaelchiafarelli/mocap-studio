# 2. The volume from muscles attached to the bones

Rafael's choice B (2026-11-09): muscles keep their connection to the bones as these grow or shrink. Replaces the per-zone shell.

## Contract

**In:** a build's `<name>.muscles.json` and bones, the sheet.

**Out:**
- `hmcore/muscle_bodies.py`: each muscle's spindle chain as a voxel solid, thin at the tendons, thick at the belly, on the bones' own attachments.
- Volumes as published (Rajagopal, MIT): nothing calibrates them to the body. What is left up to the first shape is fat, and the percentage is reported, not forced (Rafael, 2026-11-09).
- The skin stays on the first shape and moves out only where bones, muscles or the breast need it; the cavity no longer bridges the lumbar curve.
- The tissues of `body_layers.py` come from these solids.
- The biotype's muscle scales the volume.

## Dependencies

Task 1.

## Pre-work

None.

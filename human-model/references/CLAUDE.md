# references — read-only scripts on the reference file

**Role:** measure Z-Anatomy for comparison. Nothing here produces model data.

**Entry points:** inside Blender with the `.blend` as `--blend`.

**Inputs → Outputs:** Z-Anatomy's `.blend` → JSON.

## Files

- `inventory.py`: one row per object, with collections and vertex counts.
- `measure_reference.py`: bounding boxes and principal lengths of the kept bones.

## Key facts / gotchas

- Run with auto-run off, which `blender_run.py` does: the file ships a script.

## Touchpoints

[docs/sources-and-validation.md](../docs/sources-and-validation.md).

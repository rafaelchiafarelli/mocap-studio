# jaw-poc — jaw test on Z-Anatomy

**Role:** the scripts of the jaw proof of concept. An experiment, not pipeline code.

**Entry points:** each script runs inside Blender; see [README.md](README.md).

**Inputs → Outputs:** Z-Anatomy's `.blend` → a names list, a jaw scene with bindings, measurements.

## Files

- `v_names.py`: lists structures to JSON.
- `v_build.py`: links the listed objects and builds the jaw scene.
- `v_check.py`: measures the built scene.
- `README.md`: how to run them.

## Key facts / gotchas

- The object names are Z-Anatomy's, and the control object is `CONTROLE_BOCA`: `v_check.py:4`.

## Touchpoints

`initiatives/human-model/human-model.md`.

# scratch — old or unused code, waiting to be deleted

**Role:** what no longer earns a place beside the working code, moved here unchanged on 2026-11-08 so the rest reads better. Rafael deletes the folder when nothing in it is useful any more. Nothing outside this folder imports it.

**Entry points:** none. The scripts in `blender/` imported their neighbours in `human-model/blender/`, so to run one, move it back first.

**Inputs → Outputs:** none.

## Files

- `blender/smile_compare.py`: one comparison of the current smile against the muscle smile. No command or document used it.
- `blender/binding_compare.py`, `blender/scipy_free_nearest.py`: the one-off test of Surface Deform and Mesh Deform against the direct field. The second served only the first.
- `blender/tissue_experiment.py`: the one-off test of Blender's Tissue add-on on a skin patch.
- `blender/retire_trial.py`: the trial that removed the muscle bodies; its result is in `docs/status.md`.
- `jaw-poc/`: the jaw test on Z-Anatomy. Embryonic, and it may not be used in production: Z-Anatomy stays out of the model. Described in `docs/sources-and-validation.md`.
- `unused_functions.py`: `ctbones.principal_length`, `retarget.capture_to_model`, `softtissue.cotan` and `tsdata.pick_donors`, called by no code and no test.

## Touchpoints

`blender/CLAUDE.md`, `docs/running.md`.

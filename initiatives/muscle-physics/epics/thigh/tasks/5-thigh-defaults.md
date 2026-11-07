# 5. Rafael's tissue values as editable defaults

**Asked by Rafael, 2026-11-07,** after his run `rafa8` ("agora parece que está bom"): use its values as the defaults, not hard-coded, since he'll want to change them.

## Contract

**In:** `rafa8`'s values: `DAMPING=20 FAT_YOUNG=4000 MUSCLE_YOUNG=15000 SKIN_YOUNG=100000 FAT_DENSITY=750 MUSCLE_DENSITY=900 POISSON=0.45 SUBSTEPS=160`.

**Out:**
- `human-model/data/thigh_tissue.json`: those values, which `tools/thigh_walk.py` and so `thigh_run.sh` read. `NAME=value` still overrides one for a run; an unknown name stops the run.
- A run with no overrides gives `rafa8`'s numbers exactly.
- `docs/muscle-physics.md`: the defaults and where to change them.

## Dependencies

Task 4.

# tests — pytest for the human model

**Role:** tests of `hmcore` and of the pure parts of `hm_editor` and `tools`. Nothing here needs Blender.

**Entry points:** `hm.sh pytest human-model/tests`, then `hm.sh --gpu pytest human-model/tests` for the tests that need Warp.

**Inputs → Outputs:** the modules under test → pass or fail. No files on `G:`.

## Files

- `__init__.py`: marks the package.
- `test_body.py`: `hmcore/body.py` and the pure parts of `tools/body_report.py`.
- `test_bone_targets.py`: `hmcore/bone_targets.py`.
- `test_character.py`: `hmcore/character.py`; its neutral fixtures are in `fixtures/characters/`.
- `test_drive.py`: `hmcore/activation.py`, `retarget.py`, `tongue.py`, `morph.py` and `retire.py`.
- `test_editor.py`: the editor's catalog, recipe and tape.
- `test_fast_review.py`: the pure parts of `fast_review.py` and `tools/hm_status.py`'s list of runs.
- `test_fit.py`: `hmcore/fit.py`.
- `test_jaw_joints.py`: `hmcore/jaw.py` and `joints.py`.
- `test_layers.py`: `hmcore/layers.py`.
- `test_measures.py`: `hmcore/measures.py`, `ctbones.py` and `tsdata.py`.
- `test_muscle.py`: `hmcore/muscle.py`.
- `test_muscle_bodies.py`: `hmcore/muscle_bodies.py`.
- `test_outward.py`: `hmcore/outward.py`.
- `test_regions.py`: `hmcore/regions.py`.
- `test_shapes.py`: `hmcore/shapes.py`.
- `test_skinfit.py`: `hmcore/skinfit.py`.
- `test_softtissue.py`: `hmcore/softtissue.py`.
- `test_xpbd.py`: the GPU solver, and the pure parts of `tools/body_walk.py`. Skipped without Warp; uses Warp's CPU device.

## Key facts / gotchas

- `test_xpbd.py` skips in the plain image, so a passing `hm.sh pytest` alone doesn't cover the solver.

## Touchpoints

`hmcore/`, `hm_editor/`, `tools/`.

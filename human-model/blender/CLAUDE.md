# blender — scripts that run inside Blender

**Role:** everything that needs `bpy`. Run with `blender_run.py`, so auto-run stays off and drivers use simple expressions only.

**Entry points:** each script, with its arguments after `--`.

**Inputs → Outputs:** `hmcore` outputs → `.blend` files, measurements, renders.

## Files

- `hmblender.py`: shared helpers: meshes, drivers, render setup.
- `posing.py`: joint rotations in the rest pose's axes.
- `export_human.py`: MPFB human to arrays.
- `assemble.py`: builds the model file.
- `render_views.py`, `render_seq.py`: review stills and sequences.
- `motion_check.py`: joints at their limits, mesh overlap between bones.
- `breath_check.py`: rib cage at rest and at a full breath.
- `hmmuscles.py`: fields as shape keys, muscle bodies on their own armature.
- `volume_check.py`: muscle volume in test poses.
- `contraction_check.py`: frontalis and zygomaticus, measured.
- `export_blend.py`: exports a character that already exists as a `.blend`, in `export_human.py`'s format.
- `add_fields.py`: adds muscle fields to such a file.
- `smile_compare.py`: its current smile against the muscle smile.
- `binding_compare.py`, `scipy_free_nearest.py`: Surface Deform and Mesh Deform against the direct field.
- `tissue_experiment.py`: Tissue on a skin patch.
- `speed_measure.py`: frames per second by layer.
- `dump_take.py`, `key_take.py`, `render_take.py`: read a take's shapes, key a variant, render it.
- `body_drive.py`: keys capture onto the rig by bone direction.
- `retire_trial.py`: removes the muscle bodies and measures the skin.
- `feature_sheet.py`: renders what each morph target does.
- `macro_sweep.py`: measures the skin per macro slider.
- `recipe_from_file.py`: reads an MPFB human back into a recipe.
- `list_controls.py`: everything a built file offers.
- `editor_check.py`: checks the installed Human Model Editor without its interface.
- `tape_check.py`: measures people with the editor's tape, optionally with stills of its lines.
- `measure_sweep.py`: how far each slider moves each tape measure.
- `walk_clearance.py`: skin against bones while walking.
- `walk.py`: keys the walking cycle and solves the root from the stance foot.
- `muscle_sphere.py`: a liquid-filled sphere lifting a box, on our own solver: [docs/muscle-physics.md](../docs/muscle-physics.md).
- `muscle_sphere_cloth.py`: the same on Blender's Cloth, kept as the record of its limits. `muscle_sphere.py` imports its mesh helpers.
- `muscle_render.py`: renders either one to PNGs.

## Key facts / gotchas

- MakeHuman's body vertices come first and helpers after, so the first 13,380 indices mean the same on every MPFB character: `export_blend.py:8`.

- A changed control property reaches its drivers only after `update_tag` and a frame change: `breath_check.py:12`.
- Joint limits are stored as the `hm_limit_deg` bone property, not as Blender constraints: `assemble.py`, search `hm_limit_deg`.
- Muscles have their own armature: on the main rig, a bone following a skin vertex would be a dependency cycle: `hmmuscles.py:1`.
- Nothing depends on the muscle bodies: skin moves through shape keys and bones. See `retire_trial.py`.
- MPFB's Rigify metarig deforms the skin; the generated control rig isn't used. Its `DEF-*` weights have to be merged into metarig bones, or vertices stay behind: `assemble.py:34`.

## Touchpoints

`hmcore/`, `tools/`, `build_model.py`.

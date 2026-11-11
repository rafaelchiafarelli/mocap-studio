# blender — scripts that run inside Blender

**Role:** everything that needs `bpy`. Run with `blender_run.py`, so auto-run stays off and drivers use simple expressions only.

**Entry points:** each script, with its arguments after `--`.

**Inputs → Outputs:** `hmcore` outputs → `.blend` files, measurements, renders.

## Files

- `arm_clearance.py`: the hands' contact with the body while walking: a hand may sink 12 mm into the skin, which yields there (`tools/skin_waves.py`); only past that does the upper arm open, smoothed and keyed on the walk (`--blend`).
- `hand_points.py`: points with radii along forearms, hands and fingers, and the arms' share of each skin vertex, for that contact.
- `clean_body.py`: an MPFB2 human from a recipe alone, rig named `HM_rig`, helpers masked, skin subdivided on display, no inner layers (initiative `animation-body`).
- `posed_mesh.py`: reads the posed skin with helpers (Mask and Subsurf off), and measures where its triangles shrink against the rest mesh; shared by the range-of-motion and correction scripts.
- `range_of_motion.py`: keys the arms overhead, elbows and knees fully bent, trunk turning and bending, hips flexed and a squat, and reports per pose how much of the skin collapses (`--blend`).
- `pose_corrections.py`, `corrections_common.py`, `apply_corrections.py`: volume-preserving skinning fading out at the elbows, and Delta Mush tried per joint and kept only where it lowers the measured collapse (on the fitted woman, none was kept); `apply_corrections.py` puts the result on another file of the same body.
- `fold_lines.py`: finds each fold's line on the skin and the rig pose that drives it, and writes `data/folds.json` (`--blend`).
- `fold_apply.py`: the catalogue as shape keys following the pose, with a fader per fold and one for fat in `HM_controls`, plain-expression drivers (`--blend`).
- `fold_fine.py`: a thin crease per fold on the subdivided skin, from images in UV space and a Geometry Nodes modifier driven by each fold's shape key (`--blend`).
- `skin_dump.py`: the skin's motion per frame, the rig's weights and the feet's path, for `tools/skin_waves.py` (`--blend`).
- `wave_bake.py`: bakes the wave offsets into one shape key per frame, played by driver with a `wave_amount` fader (`--blend`).
- `simple_video.py`: plain viewport-style frames for a video from one view, the camera following the hips, optionally with the folds off (`--blend`; made at Rafael's request, 2026-11-11).
- `simple_stills.py`: plain viewport-style images of a body at rest or walking, from the front, back and side (`--blend`; the only images the animation body uses).
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
- `speed_measure.py`: frames per second by layer.
- `dump_take.py`, `key_take.py`, `render_take.py`: read a take's shapes, key a variant, render it.
- `body_drive.py`: keys capture onto the rig by bone direction.
- `feature_sheet.py`: renders what each morph target does.
- `macro_sweep.py`: measures the skin per macro slider.
- `recipe_from_file.py`: reads an MPFB human back into a recipe.
- `list_controls.py`: everything a built file offers.
- `editor_check.py`: checks the installed Human Model Editor without its interface.
- `tape_check.py`: measures people with the editor's tape, optionally with stills of its lines.
- `measure_sweep.py`: how far each slider moves each tape measure.
- `walk_clearance.py`: skin against bones while walking.
- `walk.py`: keys the walking cycle: the pelvis's tilt off the hip angle, toes rolling at push-off, the root from a soft contact, and each stance foot planted by correcting its leg; with `stop_steps`, more steps, shorter and slower each, end it standing.
- `walk_check.py`: a walk file's root steps, the planted foot's slide and its height against the floor.
- `muscle_sphere.py`: a liquid-filled sphere lifting a box, on our own solver: [docs/muscle-physics.md](../docs/muscle-physics.md).
- `muscle_sphere_cloth.py`: the same on Blender's Cloth, kept as the record of its limits. `muscle_sphere.py` imports its mesh helpers.
- `muscle_render.py`: renders either one to PNGs.
- `body_view.py`: the layered body as a `.blend`, with its skin painted by zone and front and side sections as stills.
- `skin_fit_view.py`: the skin before and after the push, painted by how far it moved, with front and back stills.
- `body_tape.py`: a recipe's pattern measures and each girth's height, from the installed editor's tape.
- `body_walk_dump.py`: every bone's transform from rest and the skin, every frame of a walk file.
- `body_walk_bake.py`: a walked body, lower or whole, as shape keys per frame, the current skin 80 cm behind it, its bones and the feet (bones and skin, following the rig) animated, and frames for two videos framed on the region. A frames folder of `-` makes the file only.
- `body_walk_pair.py`: two walked bodies in one file, without the current model's skin: skin and section of each, a metre apart.

## Key facts / gotchas

- MakeHuman's body vertices come first and helpers after, so the first 13,380 indices mean the same on every MPFB character: `export_blend.py:8`.

- A changed control property reaches its drivers only after `update_tag` and a frame change: `breath_check.py:12`.
- The gait data's hip angle is measured against a pelvis tilted about 10° forward; `walk.py` takes `PelvisAngleZ` off it, since the rig's rest pelvis is level. Without it the walk jumped at every step: `walk.py`, search `PelvisAngleZ`.
- The patella hangs from `hm_patella.<side>`, on the thigh, shaped like the shin and copying its local rotation at `PATELLA_SHARE` (0.5, declared), so it takes half the knee's bend (bug `human-model/19`, fixed): `assemble.py`, search `PATELLA_SHARE`.
- Joint limits are stored as the `hm_limit_deg` bone property. Hip, knee and ankle also get a Limit Rotation at the mean plus `LIMIT_MARGIN_DEG` (10°); shoulder and elbow don't, since their bones lie skewed to the limits' axis (bug `human-model/3`): `assemble.py`, search `hm_limit_deg`.
- Muscles have their own armature: on the main rig, a bone following a skin vertex would be a dependency cycle: `hmmuscles.py:1`.
- Nothing depends on the muscle bodies: skin moves through shape keys and bones. Measured by `scratch/blender/retire_trial.py`.
- MPFB's Rigify metarig deforms the skin; the generated control rig isn't used. Its `DEF-*` weights have to be merged into metarig bones, or vertices stay behind: `assemble.py:36`, and `clean_body.py` for the animation body.

## Touchpoints

`hmcore/`, `tools/`, `build_model.py`.

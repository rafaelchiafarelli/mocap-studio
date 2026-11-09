# human-model — process

What `build_model.py` does, stage by stage.

## 1. export (Blender)
`blender/export_human.py`: MPFB builds the skin and the Rigify metarig from the recipe's macros and targets. Writes the skin's vertices and polygons, the bones' heads and tails, and the vertex groups.

## 2. bones (Docker)
`tools/build_bones.py`: `hmcore/bonelib.py` meshes the CT labels of the sex's donor (`bonelib.py:11`), and caches them on G:. `hmcore/skeleton.py` fits each bone to this individual (moving the pelvis forward until the sacrum is covered, and the rig's hip and shoulder joints with pelvis and girdle, `anchors.rig_edits`), narrows the bones of the knee, ankle and larynx to the skin around them (`fit.slim_to_skin`), then settles the scapulae, clavicles and fibulae under the skin (`skeleton.settle_superficial`); about 8 minutes in all; `tools/spec.py` adds the jaw table and joint limits.

## 3. muscles (Docker)
`tools/build_muscles.py`: `hmcore/muscle.py` resolves `data/muscles.json` on this individual's rig and bones, and adds Rajagopal's leg muscles. Writes `<name>.muscles.json`.

## 4. fields (Docker)
`tools/build_fields.py`: `hmcore/softtissue.py` solves each face muscle's skin displacement at full activation; `hmcore/bodyskin.py` adds breath and muscle-belly shapes. Writes `<name>.fields.npz`.

## 5. assemble (Blender)
`blender/assemble.py`: rebuilds the human, moves the thigh heads into the sockets, adds `hm_jaw`, `hm_hyoid`, `hm_larynx`, `hm_sternum`, 24 `hm_rib_*` and two `hm_patella.*` bones, parents every bone mesh, and adds `HM_controls` with its drivers. `blender/hmmuscles.py` adds one shape key per field, driven by `m_<muscle>`, and the muscle bodies on their own `HM_muscle_rig`. Saves `<name>.blend`.

## Afterwards, on a built model

- **Walking:** `blender/walk.py` keys `data/gait_walk.json`, with the pelvis's tilt taken off the hip, the toes rolling and each stance foot planted; `blender/walk_check.py` measures it.
- **The body in layers, walking** (no render unless asked), each stage reading the one before, for its own body: `tools/skin_over_bone.py` pushes the skin out over the bones; `tools/body_layers.py` fills it with bone, muscle, fat, skin and cavity, in cubes whose size is `VOXEL_M` in `data/simulation.json`; `blender/walk.py` keys the walk; `blender/body_walk_dump.py` reads each bone's motion; `tools/body_walk.py` simulates the tissue on the GPU, summing the volumes every `VOLUME_EVERY_FRAMES` frames, and testing bones against the skin only if `BONE_TEST` is on; `blender/body_walk_bake.py` with `-` for frames makes the file; `blender/body_walk_pair.py` puts two bodies in one. The stages are drawn in [docs/diagrams/](docs/diagrams/); commands and timings are in [docs/muscle-physics.md](docs/muscle-physics.md).
- **Body capture:** `tools/body_motion.py`, then `blender/body_drive.py`.
- **Existing character:** `blender/export_blend.py` replaces the export stage, and `blender/add_fields.py` adds the shape keys to its own file.
- **Take:** `blender/dump_take.py`, `tools/solve_take.py`, `blender/key_take.py` for each variant, `blender/render_take.py`.

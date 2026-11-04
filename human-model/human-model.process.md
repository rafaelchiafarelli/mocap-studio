# human-model — process

What `build_model.py` does, stage by stage.

## 1. export (Blender)
`blender/export_human.py`: MPFB builds the skin and the Rigify metarig from the recipe's macros. Writes the skin's vertices and polygons, the bones' heads and tails, and the vertex groups.

## 2. bones (Docker)
`tools/build_bones.py`: `hmcore/bonelib.py` meshes the CT labels of the sex's donor (`bonelib.py:11`), and caches them on G:. `hmcore/skeleton.py` fits each bone to this individual; `tools/spec.py` adds the jaw table and joint limits.

## 3. muscles (Docker)
`tools/build_muscles.py`: `hmcore/muscle.py` resolves `data/muscles.json` on this individual's rig and bones, and adds Rajagopal's leg muscles. Writes `<name>.muscles.json`.

## 4. fields (Docker)
`tools/build_fields.py`: `hmcore/softtissue.py` solves each face muscle's skin displacement at full activation; `hmcore/bodyskin.py` adds breath and muscle-belly shapes. Writes `<name>.fields.npz`.

## 5. assemble (Blender)
`blender/assemble.py`: rebuilds the human, moves the thigh heads into the sockets, adds `hm_jaw`, `hm_hyoid`, `hm_larynx`, `hm_sternum` and 24 `hm_rib_*` bones, parents every bone mesh, and adds `HM_controls` with its drivers. `blender/hmmuscles.py` adds one shape key per field, driven by `m_<muscle>`, and the muscle bodies on their own `HM_muscle_rig`. Saves `<name>.blend`.

## Afterwards, on a built model

- **Walking:** `blender/walk.py` keys `data/gait_walk.json`.
- **Body capture:** `tools/body_motion.py`, then `blender/body_drive.py`.
- **Existing character:** `blender/export_blend.py` replaces the export stage, and `blender/add_fields.py` adds the shape keys to its own file.
- **Take:** `blender/dump_take.py`, `tools/solve_take.py`, `blender/key_take.py` for each variant, `blender/render_take.py`.

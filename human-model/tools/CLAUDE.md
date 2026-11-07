# tools — command-line steps in Docker

**Role:** thin scripts around `hmcore`.

**Entry points:** `hm.sh python human-model/tools/<script>.py`.

**Inputs → Outputs:** see each script's docstring.

## Files

- `fetch_sources.py`: fetches every source to `models/` on G:, keeping what exists (no Docker needed).
- `pull_ct_sample.py`: fetches the CT sample by byte range (no Docker needed).
- `ct_stats.py`: per-subject measurements from the sample.
- `validation_table.py`: the tables in `docs/sources-and-validation.md`.
- `build_bones.py`: the fitted skeleton of one individual.
- `spec.py`: adds the jaw table and limits to a skeleton's metadata.
- `build_muscles.py`, `build_fields.py`: muscle list and skin fields of one individual.
- `solve_take.py`: a take's muscle activations, from shapes and from landmarks.
- `body_motion.py`: capture to bone directions, and a quality report.
- `morph_set.py`: writes the test people.
- `sex_report.py`: the male and female table.
- `fit_fields.py`: how far the fields compress.
- `contact_sheet.py`: a labelled grid of renders.
- `make_gait_table.py`: writes `data/gait_walk.json`.
- `debug_view.py`: quick point views of a fit, no Blender.
- `gpu_bench.py`: a soft cube dropped on a floor at several sizes, timed on the GPU and the CPU (`hm.sh --gpu`; task `muscle-physics/thigh/1`).
- `body_layers.py`: the whole body in layers at rest, with every step numbered, bone poking measured apart from the cuts (`hm.sh --gpu`; task `muscle-physics/body-at-rest/1`).
- `thigh_walk.py`: the layered thigh through a walk on the GPU, its tissue values from `data/thigh_tissue.json`, with bone-through-skin, motion and volume per frame against the current model (`hm.sh --gpu`; task `muscle-physics/thigh/3`).
- `thigh_layers.py`: one thigh built from the inside out, with every step kept as a numbered `.ply` (task `muscle-physics/thigh/2`).

## Key facts / gotchas

- The CT library is cached in the given folder; delete `ct_library_<sex>.pkl` after changing `bonelib`.

## Touchpoints

`hmcore/`, `build_model.py`.

# tools — command-line steps in Docker

**Role:** thin scripts around `hmcore`.

**Entry points:** `hm.sh python human-model/tools/<script>.py`.

**Inputs → Outputs:** see each script's docstring.

## Files

- `pull_ct_sample.py`: fetches the CT sample by byte range (no Docker needed).
- `ct_stats.py`: per-subject measurements from the sample.
- `validation_table.py`: the `references/3` tables.
- `build_bones.py`: the fitted skeleton of one individual.
- `spec.py`: adds the jaw table and limits to a skeleton's metadata.
- `build_muscles.py`, `build_fields.py`: muscle list and skin fields of one individual.
- `solve_take.py`: a take's muscle activations, from shapes and from landmarks.
- `body_motion.py`: capture to bone directions, and a quality report.
- `morph_set.py`: writes the test people.
- `sex_report.py`: the male and female table.
- `fit_fields.py`: how far the fields compress.
- `make_gait_table.py`: writes `data/gait_walk.json`.
- `debug_view.py`: quick point views of a fit, no Blender.

## Key facts / gotchas

- The CT library is cached in the given folder; delete `ct_library_<sex>.pkl` after changing `bonelib`.

## Touchpoints

`hmcore/`, `build_model.py`.

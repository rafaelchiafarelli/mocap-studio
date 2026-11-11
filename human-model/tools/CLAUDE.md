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
- `body_layers.py`: the whole body in layers at rest (on a pushed skin with `SKIN=`), with every step numbered, bone poking measured apart from the cuts, the cube's size from `data/simulation.json` or `VOXEL=m` (`hm.sh --gpu`; task `muscle-physics/body-at-rest/1`).
- `skin_over_bone.py`: the skin pushed out over the bones, with before and after per bone and the girths' change (task `muscle-physics/inside-out-skin/1`). Loads the editor's tape from its file, since its package needs Blender.
- `body_report.py`: the zero point's sections, masses from the volume inside the skin, and the table in Portuguese for Rafael, optionally beside an earlier run (tasks `muscle-physics/body-at-rest/2`, `inside-out-skin/2`). Plain image; its text uses Blender's Inter font from `G:`.
- `body_walk.py`: the body walking on the GPU, every bone carrying its tissue and every cut ring held by its nearest bone, bones through the skin against the current model, and per zone what the tissue adds to the skin's motion over the current model's: the lower body by default, the whole body with `ABOVE_HIP=10`. The volumes are summed every `VOLUME_EVERY` frames and on the last, and bones are tested against the skin only with `BONE_TEST=1`, both from `data/simulation.json` or the command line (`hm.sh --gpu`; tasks `muscle-physics/leg-walk/2`, `body-walk/1`).
- `animation_body.py`: runs the animation body's stages in order from one recipe, keeping each stage's result (WSL, calling Blender).
- `skin_waves.py`: the waves of a walking skin from `blender/skin_dump.py`'s dump and `data/skin_waves.json`, with a report per region (`hm.sh`).
- `fit_proportions.py`: a recipe reaching a height, waist/hip and shoulder/hip with the height macro and three sliders within 0.5, each round measured on the real mesh by the editor's tape (WSL, calling Blender).
- `classify_body.py`: for each model named in `cut_stretches.py`'s saved table, silhouette, biotype, gluteus and breast with confidence and the measures behind them, from the body's outline in the clips, "vindo" and "indo" for widths and "lado" for depth; writes `classificacao.csv` and `classificacao.html` beside the table (`hm.sh --ref`).
- `cut_stretches.py`: cuts the stretches in `check_reference.py`'s table into clips with a still each, and writes `tabela.html`, a page to name the same model across clips and set each clip's direction, saved as `modelos.csv` (WSL with FFmpeg, no Docker).
- `hm_status.py`: what the long runs are doing now, refreshing until Ctrl+C: containers, Blender, the GPU, each stage's output and the newest log (from WSL, no Docker; `--once` prints once). A stage counts as running by the script of its command line (Blender's by `blender_run.py`, since Windows' process doesn't show under its own name), and as done by its output's age.
- `check_reference.py`: judges photos (for the body's shape at rest) and videos (for walking motion) of a real person as reference, BOA, ACEITÁVEL or RUIM, with each check's reason in Portuguese and the views still missing; a video is split at camera cuts and wherever the whole body leaves the picture, and each stretch of 2 s or more is judged apart, the best listed with start and end (`--todos` lists all, `--csv FILE` writes all to a table); a body that jumps or changes size without a cut also ends a stretch, since models replace each other in the same shot; limits declared at the top of the file (`hm.sh --ref`, takes files, folders and Windows paths on G: or C:).

## Key facts / gotchas

- The CT library is cached in the given folder; delete `ct_library_<sex>.pkl` after changing `bonelib`.

- `check_reference.py`'s front or back view comes from finding a face; it has only been run on people seen from the front. Its sharpness limits come from one recording, blurred on purpose. Its step count also counts leg movements that are not walking.

- `classify_body.py` measures clothes as body and its gluteus result always reads low confidence: its prototypes are declared, and small changes to them changed most results. Silhouette and biotype rest on ANSUR II means (US Army personnel). Not checked against measured people.

## Touchpoints

`hmcore/`, `build_model.py`.

# human-model — the human model's tools

**Role:** code and tools that build the human model, in this repository for now, not a separate one (Rafael, 2026-11-03). Start with [docs/README.md](docs/README.md).

**Entry points:** `build_model.py RECIPE OUT_DIR` from WSL builds one individual; `fast_review.py NICKNAME [--body female|male] [NAME=value ...]` takes one body, or by default both side by side, to walked bodies in one Blender file; `hm.sh pytest` runs the tests in Docker, `hm.sh --gpu` the GPU image with the GPU; `install_editor.py` installs the Blender editor.

**Inputs → Outputs:** a recipe (`data/recipes/`) and the sources on `G:\\mocap-studio-downloads\\models\\` → `<name>.blend` with skin, rig, bones, muscles and their skin fields. The stages are in [human-model.process.md](human-model.process.md).

## Files

- `build_model.py`: the stages in order.
- `fast_review.py`: one command from the recipes, or the character files (`--character`, the new path), to walked bodies in a Blender file, each body on its own thread, no rendering; its stages, what each override reaches, `run.json` and the logs are in its docstring.
- `blender_run.py`: runs a script in Windows Blender from WSL, auto-run off.
- `install_editor.py`: packs `hm_editor/` and installs it in Windows Blender.
- `setup_gpu_host.sh`: run once with `sudo` in WSL; installs the NVIDIA Container Toolkit so Docker can use the GPU, and checks it from a container. Changes the host, not the image.
- `hm.sh`, `Dockerfile`, `requirements.in`, `requirements.txt`: the locked environment for `hmcore`.
- `Dockerfile.gpu`, `requirements-gpu.in`, `requirements-gpu.txt`: the same plus NVIDIA Warp, for `hmcore/xpbd.py`. `hm.sh --gpu` builds and runs it.
- `ATTRIBUTION.md`: the credits a film has to carry.
- `human-model.process.md`: the stages.
- `docs/`: written to be read: `README.md`, `running.md`, `character-editor.md`, `character-controls.md`, `morphology.md`, `skeleton.md`, `muscles.md`, `skin.md`, `drive.md`, `muscle-physics.md`, `status.md`, `decisions.md`, `sources-and-validation.md`; and `diagrams/`, the walking simulation's stages and sequences, in draw.io and Portuguese.
- `data/`: `recipes/` (a neutral male and female), `gait_walk.json` (mean walking cycles derived from Fukuchi 2018: pelvis obliquity, rotation and tilt, hip, knee, ankle), `body_fat_female.json` (the woman's fat per zone and the depths that place muscle and cavity, by eye; edit to change), `body_fat_male.json` (the same for the man, by eye), `skin_over_bone_female.json` and `skin_over_bone_male.json` (least tissue over each bone and the most the skin may move, by eye; the man's are the woman's but for the patella), `body_tissue.json` (the body walks' tissue values: rafa8 plus the cavity, and a `REGIONS` table of overrides by tissue and zone), `simulation.json` (the cube's size, how often a walk's volumes are measured and whether its bones are tested; each can be overridden per run), `silhouette_ratios.json` (each silhouette's target proportions and how widths grow with height, read by `hmcore/character.py`), `gluteus_shapes.json` and `breast_shapes.json` (the shapes as multipliers, by eye), `bone_proportions.json` (the neutral bodies' bone proportions, for blank bone parameters), `biotypes.json` (what each pure biotype changes from the current values, by eye), `cup_table.json` (the cup letters and the first letter's difference), `muscles.json` (the declared muscle table), `recipes/test_people/` (six neutral test individuals), `characters/test/` (the eight bodies per sex that accept the new path), `macro_sweep.json` (real sizes per macro slider), `measure_sweep.json` (how far each slider moves each tape measure), `feature_sheets/` (what the slider sheets show).
- `hmcore/`, `blender/`, `tools/`, `references/`, `hm_editor/`: see each folder's `CLAUDE.md`.
- `tests/`: pytest for `hmcore` and two tools: see its `CLAUDE.md`.
- `scratch/`: what is old or unused, waiting to be deleted: see its `CLAUDE.md`.

## Key facts / gotchas

- A recipe holds `macros` and `targets`: [docs/character-controls.md](docs/character-controls.md).
- Identity is baked at build time; only controls and poses are live: [docs/running.md](docs/running.md).
- Film-neutral: a character's parameters live in the film root.
- Z-Anatomy enters no output. Its numbers appear only in validation tables.
- The GPU tests (`tests/test_xpbd.py`) skip in the plain image: run `hm.sh --gpu pytest` too. They use Warp's CPU device.
- Blender is the Windows build; paths passed to it must be under `/mnt/g` or `\\wsl.localhost`: `blender_run.py:8`.
- Built models and CT caches are on `G:` (`models/hm-build`, `models/hm-cache`), not in git.

## Touchpoints

`initiatives/bugs/epics/human-model/`, `initiatives/faces/faces.md`, `DEPENDENCIES.md`.

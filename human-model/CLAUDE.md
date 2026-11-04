# human-model — the human model's tools

**Role:** code and tools that build the human model, in this repository for now, not a separate one (Rafael, 2026-11-03). Start with [docs/README.md](docs/README.md).

**Entry points:** `build_model.py RECIPE OUT_DIR` from WSL builds one individual; `hm.sh pytest` runs the tests in Docker; `install_editor.py` installs the Blender editor.

**Inputs → Outputs:** a recipe (`data/recipes/`) and the sources on `G:\\mocap-studio-downloads\\models\\` → `<name>.blend` with skin, rig, bones, muscles and their skin fields. The stages are in [human-model.process.md](human-model.process.md).

## Files

- `build_model.py`: the stages in order.
- `blender_run.py`: runs a script in Windows Blender from WSL, auto-run off.
- `install_editor.py`: packs `hm_editor/` and installs it in Windows Blender.
- `hm.sh`, `Dockerfile`, `requirements.in`, `requirements.txt`: the locked environment for `hmcore`.
- `ATTRIBUTION.md`: the credits a film has to carry.
- `human-model.process.md`: the stages.
- `docs/`: written to be read: `README.md`, `running.md`, `character-editor.md`, `character-controls.md`, `morphology.md`, `skeleton.md`, `muscles.md`, `skin.md`, `drive.md`, `status.md`, `decisions.md`, `sources-and-validation.md`.
- `data/`: `recipes/` (a neutral male and female), `gait_walk.json` (mean walking cycles derived from Fukuchi 2018), `muscles.json` (the declared muscle table), `recipes/test_people/` (six neutral test individuals), `macro_sweep.json` (real sizes per macro slider), `feature_sheets/` (what the slider sheets show).
- `hmcore/`, `blender/`, `tools/`, `references/`, `hm_editor/`: see each folder's `CLAUDE.md`.
- `tests/`: pytest for `hmcore`.
- `jaw-poc/`: the jaw test on Z-Anatomy, review only, with its own `CLAUDE.md`.

## Key facts / gotchas

- A recipe holds `macros` and `targets`: [docs/character-controls.md](docs/character-controls.md).
- Identity is baked at build time; only controls and poses are live: [docs/running.md](docs/running.md).
- Film-neutral: a character's parameters live in the film root.
- Z-Anatomy enters no output. Its numbers appear only in validation tables.
- Blender is the Windows build; paths passed to it must be under `/mnt/g` or `\\wsl.localhost`: `blender_run.py:8`.
- Built models and CT caches are on `G:` (`models/hm-build`, `models/hm-cache`), not in git.

## Touchpoints

`initiatives/bugs/epics/human-model/`, `initiatives/faces/faces.md`, `DEPENDENCIES.md`.

# human-model — the human model's tools

**Role:** code and tools that build the human model, in this repository for now, not a separate one (Rafael, 2026-11-03). The plan is in `initiatives/human-model/`.

**Entry points:** `build_model.py RECIPE OUT_DIR` from WSL builds one individual; `hm.sh pytest` runs the tests in Docker.

**Inputs → Outputs:** a recipe (`data/recipes/`) and the sources on `G:\\mocap-studio-downloads\\models\\` → `<name>.blend` with skin, rig and bones. The stages are in [human-model.process.md](human-model.process.md).

## Files

- `build_model.py`: the stages in order.
- `blender_run.py`: runs a script in Windows Blender from WSL, auto-run off.
- `hm.sh`, `Dockerfile`, `requirements.in`, `requirements.txt`: the locked environment for `hmcore`.
- `ATTRIBUTION.md`: the credits a film has to carry.
- `human-model.process.md`: the stages.
- `data/`: `recipes/` (a neutral male and female), `gait_walk.json` (mean walking cycles derived from Fukuchi 2018).
- `hmcore/`, `blender/`, `tools/`, `references/`: see each folder's `CLAUDE.md`.
- `tests/`: pytest for `hmcore`.
- `jaw-poc/`: the jaw test on Z-Anatomy, review only, with its own `CLAUDE.md`.

## Key facts / gotchas

- Film-neutral: a character's parameters live in the film root.
- Z-Anatomy enters no output. Its numbers appear only in validation tables (`references/1`).
- Blender is the Windows build; paths passed to it must be under `/mnt/g` or `\\wsl.localhost`: `blender_run.py:9`.
- Built models and CT caches are on `G:` (`models/hm-build`, `models/hm-cache`), not in git.

## Touchpoints

`initiatives/human-model/human-model.md`, `initiatives/faces/faces.md`, `DEPENDENCIES.md`.

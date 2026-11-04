# hm_editor — the Human Model Editor add-on

**Role:** the sidebar tab "Human" in Blender. On a plain MPFB human, every slider, saving the recipe and starting a build; on a built model, the live controls and layers. The guide for people: [../docs/character-editor.md](../docs/character-editor.md).

**Entry points:** `../install_editor.py` packs and installs it; `register` in `__init__.py`.

**Inputs → Outputs:** MPFB's `data/targets/target.json`, a recipe or a built `.blend`, slider moves → a recipe `.json`; a build through `build_model.py`.

## Files

- `__init__.py`: properties, operators and panels. `_start` makes the human of a recipe; `_write_recipe` saves one.
- `catalog.py`: MPFB's sliders by region with readable labels, and the face muscle list. No `bpy`.
- `recipe.py`: making, checking and reading back a recipe. No `bpy`. `problems` holds the rules: adult age, no genitalia, gender in step with sex.
- `human.py`: the MPFB human: create, remove, sliders, macros, stature by measuring, and reading a recipe back from a body or a built skin.
- `builder.py`: `build_model.py` in WSL as a background process, read through its log. No `bpy`.
- `blender_manifest.toml`: the extension's metadata.

`install.json` isn't in git: `install_editor.py` writes it into the package with the WSL distribution and repository.

## Key facts / gotchas

- Shape sliders are never shown on a built file, since bones, muscles and fields would stay behind: panels poll `human.is_built`, which is `HM_controls` existing.
- The sliders read and write shape keys named as the target, as `assemble.py:26` loads them, so recipes, MPFB's own panel and this one agree.
- MPFB isn't imported at `register`, as it may not be enabled yet: `_target_json` reads its file from the sibling folder, and `human._services` imports at use.
- Replacing the open file can't happen inside the operator that asks for it, so `_later` runs it from a timer. Headless there are no timers, so it runs at once. `human.create` itself runs anywhere.
- Refitting eyes and measuring wait until a slider stops: `_changed`, `SETTLE_DELAY_S`.
- Setting a control from Python reaches its drivers through `_push_controls`: `update_tag` and a frame change, as `blender/breath_check.py:12` found.
- The dragged slider stops at 0.8 by `soft_max`; the hard limit stays 1: `_slider_prop`.
- A both-sides muscle slider isn't a stored value, so it can't be keyframed; the `m_<name>_L` and `_R` controls can: `HM_PT_face_muscles`.
- MPFB has no rig on this human, so `human.settle` moves the object to keep the feet on the floor. That location isn't in the recipe.
- Rounded to 4 decimals on the way out, as `recipe_from_file.py:19` does. A value below 0.00005 reads back as absent.

## Touchpoints

`../build_model.py` (runs), `../blender/assemble.py` (same MPFB calls as `human.create`), `../blender/recipe_from_file.py` (the headless equivalent of `human.read_recipe`), `../blender/editor_check.py` (the check), `../tests/test_editor.py`.

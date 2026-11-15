# mpfb-ganho — MPFB's sliders from -3 to 3, and a Reset

**Role:** exploratory (Rafael, 2026-11-14; most of it will be discarded). An add-on that widens every slider in MPFB's Model panel to -3..3 at MPFB's own scale, and adds a Reset to MPFB's defaults.

**Entry points:** `python3 experiments/mpfb-ganho/install.py` installs it in the Blender on G:; `python3 human-model/blender_run.py --blend FILE experiments/mpfb-ganho/check.py OUT.json` checks it on a file with an MPFB human.

**Inputs → Outputs:** MPFB 2.0.18, patched at run time (its files untouched) → panel "Ganho 3 e Reset" under MPFB > Model.

## Files

- `mpfb_ganho/__init__.py`: the patches (`_patch_services`), the scene properties registered again (`_widen_scene_properties`), `reset_human`, the operator and panel.
- `mpfb_ganho/blender_manifest.toml`: extension metadata.
- `install.py`: packs to `G:\mocap-studio-downloads\apps\mpfb-ganho\mpfb_ganho.zip` and installs.
- `check.py`: sets macros and modifiers past 1, measures the skin, resets.

## Key facts / gotchas

- Blender clamps a shape key's value to its slider range, 0..1 by default: every key MPFB loads or sets gets -10..10, Blender's most (`_widen`, `KEY_LIMIT`), since macro targets mix products of weights: cupsize 1.88 with firmness -0.66 gave a breast target of 6.2, which a -3..3 key cut (2026-11-14).
- Macros past MPFB's ends continue the nearest segment with MPFB's own formula (`interpolate_macro_components`), so their targets take negative weights; MPFB dropped weights under its cutoff and pruned keys under 0.0001, so `calculate_target_stack` and `reapply_macro_details` keep negatives.
- Uses MPFB's private module names (`_sections`, the getter/setter factories, `_MACROTARGETS`): an MPFB update can break it.
- Measured on the default human (2026-11-14): modifiers move 3x at 3 what they move at 1; height 3 is 5.26 m, -3 is 0.72 m (MPFB's own height 1 is already 2.37 m); Reset returns the skin to 0.0 mm.

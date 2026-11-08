# Four of the six test people are below the adult age

- **Symptom:** `male_muscular_young` and `female_muscular_young` have `age` 0.25, and `male_slim_tall` and `female_slim_tall` have 0.4. `human-model/docs/running.md` says that below 0.5 MPFB makes a child's body.
- **Where:** `human-model/tools/morph_set.py:5` and `:7`, and the recipes it wrote in `human-model/data/recipes/test_people/`.
- **Reproduce:** open one with **Open recipe** in the Human Model Editor: it's refused, because `human-model/hm_editor/recipe.py` `problems` requires 0.5 or above.
- **Impact:** these four can't be opened in the editor. Results measured on them (`docs/morphology.md`, bug `human-model/6`) are partly from bodies younger than an adult, so they say less about adult characters than they appear to.
- **Status:** Fixed (2026-11-08) — fixes/0000ea/test-people-adult-age. The four are at 0.5, the youngest adult. Not rebuilt: builds and measures made before stay on the younger bodies, noted in `human-model/docs/morphology.md`.

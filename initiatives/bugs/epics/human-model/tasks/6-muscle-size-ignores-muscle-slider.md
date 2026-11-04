# Muscle thickness doesn't follow the muscle slider

- **Symptom:** the muscular test man has a thinner biceps (18.4 mm) than the slim one (22.4 mm).
- **Where:** `human-model/hmcore/muscle.py`, `Resolver.__init__`: declared radii scale with head width, and Rajagopal's come from force and length only. No macro reaches them.
- **Reproduce:** compare `biceps_brachii_L` in `male_slim_tall.muscles.json` and `male_muscular_young.muscles.json`.
- **Impact:** musculature changes only the skin, and muscle bodies can be wrong for the person.
- **Status:** Open. Needs design, so it's a task: see `character-controls/1`.

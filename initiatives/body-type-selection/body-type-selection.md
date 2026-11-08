# body-type-selection

**Goal:** choose a character's silhouette and biotype by name, and have the whole body follow the choice (Rafael, 2026-11-08). Silhouette and biotype must stay selectable whatever fixes the body receives.

**Status:** to be planned. This file only records the initiative: no epics, tasks or code yet.

## What Rafael has asked for

The body is shaped from fashion anthropometry and plastic surgery (2026-11-05), in this order (2026-11-07):

1. Body shape type.
2. Adjustment by a pattern-making sheet (ficha de modelagem).
3. Zone by zone, like a surgeon.
4. Individual parameters.

Silhouettes he named:

- **Female:** ampulheta, triângulo/pêra, triângulo invertido, retângulo, oval.
- **Male:** trapézio, triângulo invertido, retângulo, triângulo, oval.

## What exists today

- **No selector by name.** The Human Model Editor offers sliders only: weight, proportions, muscle, regional circumferences (`human-model/docs/character-controls.md:44`). A silhouette can only be approached by hand.
- **A pattern-making panel** with tape measures in Portuguese (`human-model/docs/character-editor.md`), which is step 2's natural home.
- **The recipe is the character:** one small file, and the bones and skin fixes are computed from that recipe's own skin at every build, so nothing is tied to the neutral bodies.
- **Simulated fat ignores the body type.** `human-model/data/body_fat_<sex>.json` is one fixed table per sex (`human-model/tools/body_layers.py:81`), so two silhouettes get the same fat per zone. Only one run at a time can override it.

## What selecting a type has to change

- **The outer shape:** which sliders, by how much, per type and sex.
- **Fat per zone:** a table per type, or a rule from the type (initiative `tissue-research` asks where the data comes from).
- **Muscle:** today one volume per region, sized by the skin (bug `human-model/6`).
- **Bones, if at all:** a pelvis or shoulders that differ by type, or only the soft tissue.

## Questions to answer when planning

- **What "biotipo" means here, next to "silhueta":** the somatotypes (ectomorph, mesomorph, endomorph) or something else, and whether the two are chosen independently. Rafael to define.
- **Does a type set a starting point the sliders can then change,** or does it stay in force?
- **How do real sizes combine with a type?** A pear at 1.60 m and at 1.80 m; grading by size as in sewing (P/M/G).
- **What each type should measure:** waist-to-hip and shoulder-to-hip ratios from anthropometric data, so that a type can be checked, not just looked at.
- **Which bodies have been tested.** The bone and skin fixes have only been measured on the neutral woman and man; types far from neutral may reach their limits (`fit.slim_to_skin` stops at 40% of a bone's width).

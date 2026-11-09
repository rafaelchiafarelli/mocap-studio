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

## Specification under study (Rafael, 2026-11-08)

From an investigation session; nothing here is built. It would change the order in which a body is made, so it needs a redesign agreed before tasks are written.

**Order of the choices:**

1. Silhouette and biotype.
2. Height and body-fat percentage.
3. Key distances, from which the bones are calculated. Reference: `G:\mocap-studio-downloads\Modelagem_Plana-referencia.pdf` (one page, 15 pattern-making measures). Measures 7 and 9 are bony landmarks; 4, 5 and 12 are near it; 8, 14 and 15 are girths with little fat. The rest are soft tissue or garment lengths.
4. Every physical quantity per body region: stiffness, Poisson's ratio, density, damping, fat thickness.

**Bone inputs the sheet doesn't give** are parameters of the configuration: the pelvis's real width (measure 3 goes over the fat), the thigh/shin split and the humerus/forearm split.

**Tissues:**

- **Two fat layers,** more marked in some regions, the gluteus and the breast above all.
- **Mammary gland** as its own tissue (proposed in the session, not yet confirmed).
- **Viscera:** the belly gets its own tissue, separate from the chest, in the woman and the man, kept computationally simple.

**Gluteus shape,** chosen by name:

- **Quadrado/retangular:** hip, waist and side of the thigh of similar width; a straight side line, little projection.
- **Redondo:** balanced, symmetric volume with defined curves throughout.
- **Coração/pêra invertida:** narrow near the waist, full at the base, a marked curve.
- **Em V/triângulo invertido:** wider above, narrower at the base; less lower fat or loss of muscle support.
- **Em A/trapezoidal:** narrow above, wider in the lower buttocks and hips.

**Breast shape:**

- **Exclusive shapes:** redondos, lágrima/gota, cônicos, tuberosos.
- **Independent adjustments, combined with any shape:** espaçados (leste-oeste), assimétricos, pendentes/flácidos.
- **Always adjustable after the choice:** volume, density and the other physical values.

**Breast measures:**

- **Sub-busto:** just under the breasts, snug and level around the thorax.
- **Busto:** horizontally at the fullest part, usually at the nipples.
- **Copa/taça, two-way:** its letter comes from bust minus sub-busto, at 2 cm per letter. Setting the cup holds the thorax and raises the bust; setting the bust recalculates the cup.

**Still open:** whether waist and hip are typed in or follow from silhouette and body fat (a proposal: they follow, with fine adjustment by the pattern-making sheet).

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

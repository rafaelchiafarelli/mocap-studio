# body-type-selection

**Goal:** choose a character's silhouette and biotype by name, and have the whole body follow the choice (Rafael, 2026-11-08). Silhouette and biotype must stay selectable whatever fixes the body receives.

**Status:** built in a first pass on branch `body-type-selection`, not merged: epics and tasks in [epics/](epics/README.md). The gate is Rafael's verdict on the eight bodies (`review\\fast_review_todas.blend`, 2026-11-09). Task `editor-sheet/3` waits for its pre-work.

## What Rafael has asked for

The body is shaped from fashion anthropometry and plastic surgery (2026-11-05), in this order (2026-11-07):

1. Body shape type.
2. Adjustment by a pattern-making sheet (ficha de modelagem).
3. Zone by zone, like a surgeon.
4. Individual parameters.

Silhouettes he named:

- **Female:** ampulheta, triângulo/pêra, triângulo invertido, retângulo, oval.
- **Male:** trapézio, triângulo invertido, retângulo, triângulo, oval.

## Specification and redesign (Rafael, 2026-11-08)

Agreed in the investigation session that closed on 2026-11-08; nothing here is built yet. It changes the order in which a body is made.

**The redesign.** Today: skin, then bones fitted inside it, then layers filled inward. Agreed: measures, bones, muscle, fat, and the skin as the result. The path is the hybrid one, in stages: the current sliders give a first shape from the measures, the layers set the skin's final position, and today's path stays until the new one beats it, with a body to judge at each stage.

| Part | Today | New order | Impact |
|---|---|---|---|
| Input | sliders in a recipe | silhouette, biotype, height, body fat, measures, shapes, cup | new |
| Bones | fitted inside the skin | calculated from the measures, once, when the character's design is finished; the CT shapes stay | large |
| Muscle | sized by the skin | sized by the biotype, before the fat | large |
| Fat | grows inward from the skin | grows outward from the muscle, in two layers, up to the body-fat percentage | large |
| Skin | comes first | the result of the layers, on the same 13,380 points and the same rig | the hardest: head, hands and feet still have to join it at the neck, wrists and ankles |
| Fit fixes (skin push, slimmed bones, narrowed ribs and feet) | needed | most should stop being needed | go away |
| Cube mesh and tissue solver | values per tissue | the same, with values per region | small |
| Walk, Blender file, measurements, tape | | stay | none or small |

**One check per character.** When the design is finished, in Blender's check boxes and sliders, the program runs one check that everything is right. At rest, tissue built outward from the bones shouldn't let a bone through, so this is a safeguard. It doesn't cover the walk: no stage of the simulation checks collision, and a bone can come through where the tissue over it gives way. The walk's bone test is therefore a setting, off by default so runs are faster, and asked for on one body when Rafael sees a bump (`BONE_TEST=1`).

**Biotype** (Rafael, 2026-11-08) means the somatotypes: ectomorph, mesomorph, endomorph. Only their physical side counts; metabolism and training have no place in a body built once.

| | Ectomorph | Mesomorph | Endomorph |
|---|---|---|---|
| Bone thickness | thin | medium | wide |
| Arms and legs | long | balanced | balanced |
| Shoulders, waist, hips | narrow shoulders and hips | wide shoulders, thin waist | wide hips and waist |
| Muscle mass | little | much | tends high |
| Starting body fat | low | medium | high |

- **A pure type and two others:** the chosen type, plus the other two up to 35% each and 65% together, so the chosen one is always the largest. The rest is the pure type.
- **Silhouette and biotype are independent.** The biotype says how much and how thick (bones, muscle, tendency to fat); the silhouette says where the volume sits. Where they disagree on proportions, the silhouette wins.
- **Each step only fills in the next one's starting values, and what is typed always wins.** The fields open with the model's current values (the neutral body, today's fat and tissue tables), not with new numbers by eye; biotype and silhouette change them from that base, and each field shows the result before it is edited.

**Physical values per region** need: the zone of each tetrahedron kept through to the simulation (`hmcore/body.py` knows it per voxel and drops it); an editable table of tissue by zone, with one default per tissue and overrides only where wanted; damping per region (one value today); and smooth changes between zones, as the fat thickness already has. The gluteus and breast zones have to be divided: upper/lower and centre/side for the gluteus, left/right for the breast.

**Order of the choices:**

1. Silhouette and biotype.
2. Height and body-fat percentage.
3. Key distances, from which the bones are calculated. Reference: `G:\mocap-studio-downloads\Modelagem_Plana-referencia.pdf` (one page, 15 pattern-making measures). Measures 7 and 9 are bony landmarks; 4, 5 and 12 are near it; 8, 14 and 15 are girths with little fat. The rest are soft tissue or garment lengths.
4. Every physical quantity per body region: stiffness, Poisson's ratio, density, damping, fat thickness.

**Bone inputs the sheet doesn't give** are parameters of the configuration: the pelvis's real width (measure 3 goes over the fat), the thigh/shin split and the humerus/forearm split.

**Tissues:**

- **Two fat layers,** more marked in some regions, the gluteus and the breast above all.
- **Mammary gland** as its own tissue.
- **Viscera:** the belly gets its own tissue, separate from the chest, in the woman and the man, kept computationally simple: other values on the same tetrahedra, at no extra cost per step. Keeping it nearly incompressible may need more steps per frame, which is to be tested.

**Gluteus shape,** chosen by name:

- **Quadrado/retangular:** hip, waist and side of the thigh of similar width; a straight side line, little projection.
- **Redondo:** balanced, symmetric volume with defined curves throughout.
- **Coração, also called A, pêra invertida or trapezoidal (one shape):** narrow near the waist, fuller and wider at the base and hips.
- **Em V/triângulo invertido:** wider above, narrower at the base; less lower fat or loss of muscle support.

**Breast shape:**

- **Exclusive shapes:** redondos, lágrima/gota, cônicos, tuberosos.
- **Independent adjustments, combined with any shape:** espaçados (leste-oeste), assimétricos, pendentes/flácidos.
- **Always adjustable after the choice:** volume, density and the other physical values.

**Breast measures:**

- **Sub-busto:** just under the breasts, snug and level around the thorax.
- **Busto:** horizontally at the fullest part, usually at the nipples.
- **Copa/taça, two-way:** its letter comes from bust minus sub-busto, at 2 cm per letter. Setting the cup holds the thorax and raises the bust; setting the bust recalculates the cup.

**Waist and hip** follow from silhouette and body fat, with fine adjustment by the pattern-making sheet.

## What exists today

- **No selector by name.** The Human Model Editor offers sliders only: weight, proportions, muscle, regional circumferences (`human-model/docs/character-controls.md:44`). A silhouette can only be approached by hand.
- **A pattern-making panel** with tape measures in Portuguese (`human-model/docs/character-editor.md`), which is step 2's natural home.
- **The recipe is the character:** one small file, and the bones and skin fixes are computed from that recipe's own skin at every build, so nothing is tied to the neutral bodies.
- **Simulated fat ignores the body type.** `human-model/data/body_fat_<sex>.json` is one fixed table per sex (`human-model/tools/body_layers.py:81`), so two silhouettes get the same fat per zone. Only one run at a time can override it.

## What selecting a type has to change

- **The outer shape:** which sliders, by how much, per type and sex.
- **Fat per zone:** a table per type, or a rule from the type (initiative `tissue-research` asks where the data comes from).
- **Muscle:** today one volume per region, sized by the skin (bug `human-model/6`).
- **Bones:** calculated from the measures, so a pelvis or shoulders can differ by type. A change of fat alone must not change them.

## Sizes, proportions and the bodies to test (Rafael, 2026-11-08)

**Height and silhouette.** A silhouette is a set of proportions and doesn't depend on height: in ANSUR II, waist over hip correlates with stature at -0.02 in women and -0.01 in men. Widths and girths grow about 0.7 times as fast as height (+10% of height is +6 to 8%, and +21 to 23% of weight), so a tall body isn't a scaled-up short one.

**Each silhouette's proportions** are in `human-model/data/silhouette_ratios.json`, to be edited if need be: ANSUR II's percentiles, with cuts proposed in the session. They are targets, applied from the model's current values. The data is US Army personnel, fitter than the general population.

**Clothing size is a result of the model, never an input.** The body may report which size it would wear. Rafael's table for that, `G:\mocap-studio-downloads\medidas-2024-05.pdf`, is for clothes and must not shape a model.

**The bodies that accept the new path,** eight per sex: the neutral one, the five silhouettes at median height, a short endomorph and a tall ectomorph (the woman at 150 and 176 cm, the man at 162 and 189 cm). So far only the two neutral bodies have gone through the whole chain to the walk. `male_heavy_short` reached bones and skin (bug `human-model/25`), and the other five test people were built before the 2026-11-08 fixes.

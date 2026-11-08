# Status

**Declared a good first pass by Rafael on 2026-11-03:** "it is not perfect, but it is good for a first pass." The initiative's plan and task files were removed that day; `git log -- initiatives/human-model` keeps them. The first handles exist: the [character editor](character-editor.md), for changing a character and testing it by hand.

## What works

- Male and female skeletons from real CT and permissive meshes, with no sculpting or manual repair.
- 200 muscles whose volume holds within 0.1%.
- A jaw that rotates, then slides.
- Breathing, and walking from measured data.
- Six test people from parameters alone.
- Capture driving the body.
- Licenses clean for commercial use, with Z-Anatomy out of the model.

## What doesn't, yet

- **Muscles alone don't beat the faders.** They can't reproduce the ARKit shapes (residual 0.62 to 1.0) or what tracking saw (0.79).
- **Muscle bodies don't move the skin at run time.** Removing them changes the skin by exactly 0 mm over 40 walking frames, and saves about 1.2 ms per frame. The plan's aim, muscles moving skin because they're connected, is true only in how the fields were built.
- **Inner layers follow the skin,** not the other way round. So musculature, gluteus, breasts and fat are skin only.

## Good-enough register

An element's verdict comes only from Rafael. A verdict marks it as enough for now, and it can move. For faces, new work still has to beat the mouth faders on the same recording, in his judgement.

| Element | What was compared | Verdict (Rafael's words) | Date | What would reopen it |
|---|---|---|---|---|
| **The whole model** | The first pass | "it is not perfect, but it is good for a first pass" | 2026-11-03 | Hands-on testing |
| Walking | `caminhar_masculino_ossos_e_pele.mp4` | Not enough: "the animation is jumpy... there is some error somewhere that made the model jump" | 2026-11-03 | Fixing bug `human-model/5` |
| Muscle smile | `sorriso_neutro_arkit_musculo.png`, the current ARKit smile | Neither: the ARKit one is too incisive, "the pure muscle one is too 'biten'... more investigation is required" | 2026-11-03 | The investigation |
| Face on a recording | `comparacao_faders_hibrido_musculos.mp4`, three variants | "none yet". "Within this sample the pure muscle is clearly the worst". The faders twist the mouth a little more than faders plus muscles, where the actress's mouth twists a little | 2026-11-03 | "something I want to investigate further" |
| Muscle volume range | ±5%, measured within 0.1% | Yes "for now" | 2026-11-03 | Biomedical tables giving each muscle's values |
| Six individuals | `seis_individuos_pele.png`, `seis_individuos_ossos_musculos.png` | No separate verdict | — | — |

## What Rafael said about the body (2026-11-04)

"O movimento é duro demais... vamos ter que pensar em uma forma mais equivalente à pele humana e tecido adiposo." He said it after learning that skin isn't simulated, before watching the walk himself. Measured on `female_walk_review.blend` and `male_walk_review.blend`: the nipple moves 0.0 mm in the rib cage's frame, and bones come through the skin more when walking (bug `human-model/9`, since fixed by the layered body: no bone through the skin in the whole body's walk, though a built `.blend` still deforms its skin by weights alone). **Next decision with him:** how to add soft tissue. Options come first, and nothing has been built.

## Retiring a layer

A layer can leave the model only when all of these hold (Rafael, 2026-11-02):

1. The layers above it reproduce its effect from stored data, such as baked shapes or a fitted model.
2. A side-by-side on recordings it was not fitted to shows no loss, in Rafael's judgement.
3. The data and the method to rebuild it stay available.

Removing a layer to gain speed is a different decision and has to be presented as a loss of detail. **Nothing has been retired.** Speed is no reason to: headless, all layers run at 252 fps, without muscle bodies 352, skin and rig only 402 (no drawing or subdivision).

## Constraints that stay

- Nobody can sculpt: everything is built with tools.
- No AI generating final face pixels.
- No genitalia in either model.
- Keep MPFB's topology on the skin, since its targets depend on it.
- Licenses: the rule in the `mocap-workflow` skill.
- Repositories stay film-neutral: a character's parameters live in the film root.
- Local compute: measure before adopting any model on the RTX 4080.
- Body work: Rafael's view of what's wrong with the body results comes first.

## Questions still open with Rafael

1. **What's wrong with the body results?** So far: stiff movement, above. The sample's numbers are in [drive.md](drive.md#body), but that isn't his recording.
2. **What is the "character reference"?** See [character-controls.md](character-controls.md#from-a-character-reference).
3. **Release `CharacterBody`?** My recommendation: after adding state and real units.

## Open work

**Next:** Rafael tests the [character editor](character-editor.md) by hand, and what he finds reorders this list. Recommended, in order:

1. **Muscle size as a parameter,** driven by the muscle macros, with bug `human-model/6`.
2. **Fix the mouth corners on changed faces,** bug `human-model/7`: a face that can't smile blocks every character.
3. **Fat and breast as layers,** so a hip or a gluteus can be declared bone, muscle or fat.
4. **Calibrate the editor's tape** against ANSUR II and against Rafael's own pattern-room numbers. Weight still has no real unit.
5. **The word-to-slider vocabulary,** with Rafael's eye on the sheets.
6. **State and real units in `CharacterBody`,** then release it.
7. **Fit muscle patterns to recordings of real faces,** so anatomy constrains data instead of being guessed. The most promising way past hand-declared fields.

### Biomedical tables, not started

Rafael's lead: biomedical tables might give the values for every muscle. Declared values are the model's main weakness.

**Deliver:** one row per muscle in `data/muscles.json`: mass or volume, fiber length, cross-section, pennation, attachment, source, sample (specimens, sex, age), license, and "none found" where that's the truth. Then which declared values each row would replace. Check the license rule on each table; prefer primary sources.

**Leads, none read yet.** A first search found no single open table covering every muscle, so expect to combine several:

- Face: [Happak et al. 1997](https://bioweb.supagro.inrae.fr/ESTHER/paper/Happak_1997_Anat.Rec_249_276), ten facial muscles from 11 cadavers, lengths 29 to 65 mm. Access and terms unknown.
- Search results still to match to their papers: [PMC2650051](https://pmc.ncbi.nlm.nih.gov/articles/PMC2650051), [PMC5199092](https://pmc.ncbi.nlm.nih.gov/articles/PMC5199092), [PMC11889482](https://pmc.ncbi.nlm.nih.gov/articles/PMC11889482), [arXiv 2411.00071](https://www.arxiv.org/pdf/2411.00071). They appear to include a 27-muscle lower-limb study from 21 specimens, a single 104-year-old female cadaver, 14 neck muscles from 10 cadavers, and a comparison of open lower-limb model parameters against 57 studies.

### Open bugs

In `initiatives/bugs/epics/human-model/tasks/`:

| # | Bug |
|---:|---|
| 1 | The inside of the mouth pokes through the cheek at strong activation |
| 2 | Sacrum partly outside the skin in male builds |
| 3 | Joint limits aren't enforced |
| 4 | Walking stride is short |
| 5 | The walk jumps at every step |
| 6 | Muscle thickness doesn't follow the muscle slider |
| 7 | A smile tears at the mouth's corners on a changed face |
| 8 | Four of the six test people are below the adult age, so the editor refuses them |
| 9 | Bones come through the skin at the thigh and upper arm when walking |

### Not done, or short of the plan

- The comparison character doesn't use the sliding jaw or the tongue controls.
- Tongue curves from phonemes haven't been seen on the model.
- Radius and ulna don't cross; the patella has no track; cartilage doesn't bend.
- Elbow and shoulder shapes weren't checked in a render.
- Built models have plain skin: skin materials, hair and clothes aren't applied.
- Tissue is inconclusive.
- The comparison character's fields and the walk video predate the last skull fix: a small effect on where muscles attach.
- Task commits were coarser than the workflow asks, because `assemble.py` is shared, and as-built docs were written per epic, not per task.

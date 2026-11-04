## 1. Character controls research

- **Type:** research, with small tools to test it.
- **Depends on:** `morphology`
- **Contract:**
  - In: Rafael (2026-11-04): change body type, weight, height, musculature, nose, mouth, eyes, ribs, shoulders, breasts, gluteus and so on. "eventualy, this will be outputed from the character reference"
  - Requires: the license rule; an answer tested on the real build
  - Delivers: below: what exists, how to change it now, what follows each change, and how a character reference would feed it. Recipes now accept `targets`
- **Pre-work:** —
- **Out of scope:** changing the muscle model; a character's real values, which belong in a film root
- **Tests:** `tests/test_drive.py` (height conversion). Blender scripts were checked by running them

## Result (2026-11-04)

**Yes: almost everything on the list can be changed now, without sculpting, and every inner layer rebuilds.** But for muscle and breast, and for gluteus, what changes today is the skin alone (see "What follows a change").

Images, all in `G:\mocap-studio-downloads\review\2026-11-04\`: `rosto_masculino_f.png` and `_s.png` (face sliders), `corpo_masculino_*.png` and `corpo_feminino_*.png` (body sliders), `teste_rosto_alterado.png`, `teste_corpo_alterado.png`.

### How to change a character now

**A recipe is one small file, and it's the whole definition.** Two ways to write it:

1. **By hand:** copy `human-model/data/recipes/male.json`, and set `macros` and `targets`.
2. **By eye:** in Blender, make a new MPFB human and use its sliders. Then `blender/recipe_from_file.py` writes the recipe. *Reading back a built file gives identical values, in both sexes. Real interface sliders weren't exercised, since this session has no interface.*

Then build it, which takes a few minutes:

```sh
python3 human-model/build_model.py my_recipe.json OUT_DIR
```

```json
{"name": "example", "sex": "male",
 "macros": {"gender": 1.0, "age": 0.7, "height": 0.55, "weight": 0.75, "muscle": 0.7, "proportions": 0.5,
            "cupsize": 0.5, "firmness": 0.5, "race": {"african": 0.33, "asian": 0.33, "caucasian": 0.34}},
 "targets": {"nose-scale-horiz-incr": 0.8, "chin-prominent-incr": 0.8, "buttocks-volume-incr": 0.5},
 "assets": {"eyes": "eyes/high-poly/high-poly.mhclo", "teeth": "teeth/teeth_base/teeth_base.mhclo", "tongue": "tongue/tongue01/tongue01.mhclo"}}
```

### What exists

MPFB 2.0.18 has 8 macros and 234 named sliders (`data/targets/target.json` in the add-on; CC0). A slider such as `nose-hump-decr-incr` is two targets, `nose-hump-decr` and `nose-hump-incr`. A slider marked with sides has `l-` and `r-` targets: set both. Most run well up to about 0.8; at 1.0 some break (`nose-point-down` makes a spike, `head-square` a ridge).

| You asked for | Control | Sliders |
|---|---|---:|
| Height | Macro `height`; `hmcore/morph.py` converts metres | 1 |
| Weight, body type | Macros `weight`, `proportions`; `*-fat-*`, `stomach-*`, `measure-*-circ-*` | see below |
| Musculature | Macro `muscle`; `upperarm-muscle`, `lowerarm-muscle`, `upperarm-shoulder-muscle`, `upperleg-muscle`, `lowerleg-muscle`, `torso-muscle-pectoral`, `torso-muscle-dorsi` | 7 |
| Age | Macro `age`. **Below 0.5 it's a child's body:** 0.25 gives 1.43 m | 1 |
| Nose | `nose-*`: width (4), hump, curve, Greek, tip, nostrils, septum, length, depth | 21 |
| Mouth, lips | `mouth-*`: upper and lower lip height, volume and width, cupid's bow, corners, philtrum, dimples | 22 |
| Eyes | `eye-*`: size, height (3), corners (2), fold (3), bag (3), epicanthus, position | 17 |
| Eyebrows, forehead, cheeks, chin | `eyebrows-*`, `forehead-*`, `cheek-*`, `chin-*` | 3, 4, 4, 8 |
| Head shape, ears, neck | `head-oval`, `-round`, `-square`, `-diamond` and others; `ear-*`; `neck-*` | 17, 11, 10 |
| Face asymmetry | `asym-*`, millimetres per slider | 31 |
| **Ribs, chest** | `measure-underbust-circ`, `measure-frontchest-dist`, `torso-scale-horiz`, `-depth`, `-vert`, `torso-vshape` | part of 17 |
| **Shoulders** | `measure-shoulder-dist` | 1 |
| **Breasts** | Macros `cupsize`, `firmness`; `breast-point`, `breast-dist`, `breast-volume-vert`, `breast-trans`, `nipple-*`, `measure-bust-circ` | 6 + macros |
| **Gluteus** | `buttocks-volume` | 1 |
| Hips, waist | `hip-*`, `measure-hips-circ`, `measure-waist-circ`, `measure-waisttohip-dist` | 7 + |
| Arms, legs, hands, feet | Lengths, circumferences, fat | 14, 18, 6, 8 |

Genital targets exist in MPFB and stay out, as you decided.

### Real units

From `blender/macro_sweep.py`, in `data/macro_sweep.json`, other macros at 0.5:

| Height slider | 0 | 0.25 | 0.5 | 0.75 | 1 |
|---|---:|---:|---:|---:|---:|
| Male stature | 1.37 m | 1.56 m | 1.73 m | 2.07 m | 2.43 m |
| Female stature | 1.24 m | 1.42 m | 1.59 m | 1.93 m | 2.29 m |

**Weight's range is narrow.** Mass here is the skin's volume at a declared density, so it's an estimate.

| Weight slider | 0 | 0.5 | 1 |
|---|---:|---:|---:|
| Male, 1.73 m | 58 kg, BMI 19.5 | 64 kg, BMI 21.3 | 70 kg, BMI 23.3 |
| Female, 1.59 m | 41 kg, BMI 16.2 | 49 kg, BMI 19.2 | 55 kg, BMI 21.8 |

At full weight the body is still in the normal range, so a heavy character needs `stomach-pregnant`, `*-fat-*` and `measure-*-circ` too. Those combinations weren't calibrated. The muscle slider also lowers the skin's volume (male 71 to 61 kg from 0 to 1): it isn't adding mass.

### What follows a change

Tested with full builds: two changed faces, and one changed female body (`measure-underbust-circ-incr` 0.8, `measure-shoulder-dist-incr` 0.8, `measure-hips-circ-incr` 0.8, `buttocks-volume-incr` 0.9, `measure-waist-circ-decr` 0.5, cup size 0.9). Motion checks found no unrelated bones colliding, and muscle volume held, on the two faces. The body build wasn't put through them.

| Change | Skin | Bones | Muscles | Verdict |
|---|---|---|---|---|
| Height, limb lengths | Yes | Yes, through the rig | Yes | **Follows** |
| Ribs (underbust) | Yes | Rib width 235 to 287 mm; depth 128 to 134 only | Attachments move | **Follows in width.** The width is read at T10, so a waist target also moves it |
| Shoulders | Yes | Clavicles +40 mm, arms +40 mm | Attachments, deltoid 21 mm | **Follows** |
| Hips | Yes | Pelvis 251 to 276 mm | Attachments, 11 to 14 mm | **Over-follows:** bone grows even if the hip is meant to be fat |
| Head shape, chin | Yes | Skull and jaw fit to it | Fields recomputed | **Follows** |
| Nose, lips, eyes | Yes | No nasal or lip bone change, none needed; eyes not checked in their sockets | Fields recomputed | **Follows, with a fault:** smiles tear at the corners on a changed face (bug `human-model/7`) |
| **Gluteus** | Yes | No | **No:** radius 32 to 31 mm while the buttock grows | **Skin only** |
| **Breasts** | Yes | No | No | **Skin only.** There's no breast tissue layer |
| **Musculature** | Yes | No | **No, and wrongly:** biceps 22.4 mm on the slim man, 18.4 on the muscular one (bug `human-model/6`) | **Skin only** |
| Fat | Yes | No | No | **Skin only.** There's no fat layer |

So the plan's aim, that the skin comes from what's under it, runs backwards today: inner layers are fitted to the skin. For your list, the top priority is making muscle size a real parameter.

### From a character reference

No repository has anything called a character reference yet. `mocap-preprod`'s `character-design-planner` is the nearest: it proposes, marks a state (`established`, `creator-approved`, `proposal`, `TBD`), and the creator decides. **Assumption:** the reference is that output or grows from it. Correct me if it's something else.

The path this research supports:

```
character reference → proposed values in real terms → you approve → characters/<id>.json in the film root → build_model.py
```

What it needs:

1. **Real terms, not sliders,** where they exist: stature in metres, through `morph.height_slider`. Weight, shoulders and hips need the same table.
2. **A vocabulary from words to sliders:** "aquiline nose" to `nose-hump-incr` and `nose-curve-convex`. It doesn't exist yet; it would be built by eye from these sheets.
3. **State per value,** so an agent's proposal isn't taken as approved. `CharacterBody` doesn't carry that yet, so add it before releasing the contract. Its branch also has no real units.
4. **From images, later:** fitting sliders to reference drawings or photos is possible in principle, since the sliders are smooth and tracking gives landmarks. Not tried. Consent applies if a reference shows a real person.

### Other tools

| Tool | License as read | Fit |
|---|---|---|
| **MPFB (keep)** | Code GPL-3.0+, assets CC0 | Everything here depends on its topology and rig |
| [Anny](https://europe.naverlabs.com/blog/anny-a-free-to-use-3d-human-parametric-model-for-all-ages/) | Apache 2.0 | **Worth a look:** MakeHuman's mesh with 564 blendshapes, calibrated with WHO data. May give the real-unit calibration we lack. Not tested; face detail isn't described |
| [CharMorph](https://github.com/Upliner/CharMorph) | GPL-3 code; [generated characters take the base's license](https://github.com/Upliner/CharMorph/blob/master/license.txt): AGPL for MB-Lab bases, [CC-BY or CC0 for others](https://www.blendernation.com/2025/03/19/charmorph-v0-4-0-character-creator-released/) | Different mesh: rebuilds the rig landmarks, and the expression shapes. Not tested |
| MB-Lab | AGPL on bases | Share-alike on the character: no |
| SMPL, FLAME | Non-commercial as far as known, not re-read here | Against the rule: no |
| Human Generator, Character Creator, MetaHuman | Not read | Not looked at; MetaHuman is parked |

### Recommended next tasks

1. **Muscle size as a parameter:** driven by the muscle macros, and bug `human-model/6` goes with it.
2. **Fix the mouth corners on changed faces:** bug `human-model/7`. A face that can't smile blocks every character.
3. **Fat and breast as layers,** so a hip or a gluteus can be declared bone, muscle or fat.
4. **Real-unit tables** for weight, shoulders, hips, waist, checked against ANSUR II.
5. **The word-to-slider vocabulary,** with your eye on the sheets.
6. **State and real units in `CharacterBody`,** then release it.

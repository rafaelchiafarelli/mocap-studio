# Character controls

How to change a character's body and face, what each change does underneath, and how a character reference will feed this.

**In short:** almost everything can be changed, with no sculpting, and every inner layer rebuilds. But musculature, gluteus, breasts and fat change only the skin today.

Slider images, in `G:\mocap-studio-downloads\review\2026-11-03\`: `rosto_masculino_f.png` and `_s.png` (face), `corpo_masculino_*.png` and `corpo_feminino_*.png` (body), `teste_rosto_alterado.png`, `teste_corpo_alterado.png`.

## How to change a character

A **recipe** is one small file and the whole definition. All its fields are in [running.md](running.md#what-to-prepare-the-recipe).

```json
{"name": "example", "sex": "male",
 "macros": {"gender": 1.0, "age": 0.7, "height": 0.55, "weight": 0.75, "muscle": 0.7, "proportions": 0.5,
            "cupsize": 0.5, "firmness": 0.5, "race": {"african": 0.33, "asian": 0.33, "caucasian": 0.34}},
 "targets": {"nose-scale-horiz-incr": 0.8, "chin-prominent-incr": 0.8, "buttocks-volume-incr": 0.5},
 "assets": {"eyes": "eyes/high-poly/high-poly.mhclo", "teeth": "teeth/teeth_base/teeth_base.mhclo", "tongue": "tongue/tongue01/tongue01.mhclo"}}
```

Three ways to write it:

1. **By eye, in the editor:** the sidebar tab **Human** in Blender: [character-editor.md](character-editor.md). Start here.
2. **By hand:** copy `data/recipes/male.json` and edit it.
3. **By eye, in MPFB's own panel:** make a new MPFB human in Blender, use its sliders, then run `blender/recipe_from_file.py`. Reading back a built file gave identical values in both sexes; real interface sliders haven't been exercised.

Then build, about 4.5 minutes:

```sh
python3 human-model/build_model.py my_recipe.json /mnt/g/mocap-studio-downloads/models/hm-build/example
```

**Don't move those sliders inside a built file:** the skin moves, and bones, muscles and fields stay behind.

## What exists

MPFB 2.0.18 has 8 macros and 234 named sliders, in `data/targets/target.json` inside the add-on. All are CC0.

**How names work:** a slider such as `nose-hump-decr-incr` is two targets, `nose-hump-decr` and `nose-hump-incr`; set one, from 0 to 1. A slider with sides has `l-` and `r-` targets, as `l-eye-scale-incr`: set both for a symmetric change. Most run well up to about 0.8. At 1.0 some break: `nose-point-down` makes a spike, and `head-square` a ridge.

| You want | Control | Sliders |
|---|---|---:|
| Height | Macro `height`; `hmcore/morph.py` converts metres | 1 |
| Weight, body type | Macros `weight`, `proportions`; `*-fat-*`, `stomach-*`, `measure-*-circ-*` | see below |
| Musculature | Macro `muscle`; `upperarm-muscle`, `lowerarm-muscle`, `upperarm-shoulder-muscle`, `upperleg-muscle`, `lowerleg-muscle`, `torso-muscle-pectoral`, `torso-muscle-dorsi` | 7 |
| Age | Macro `age`. **Below 0.5 it's a child's body** | 1 |
| Nose | `nose-*`: width (4), hump, curve, Greek, tip, nostrils, septum, length, depth | 21 |
| Mouth, lips | `mouth-*`: upper and lower lip height, volume and width, cupid's bow, corners, philtrum, dimples | 22 |
| Eyes | `eye-*`: size, height (3), corners (2), fold (3), bag (3), epicanthus, position | 17 |
| Eyebrows, forehead, cheeks, chin | `eyebrows-*`, `forehead-*`, `cheek-*`, `chin-*` | 3, 4, 4, 8 |
| Head shape, ears, neck | `head-oval`, `-round`, `-square`, `-diamond` and others; `ear-*`; `neck-*` | 17, 11, 10 |
| Face asymmetry | `asym-*`, a millimetre or two per slider | 31 |
| Ribs, chest | `measure-underbust-circ`, `measure-frontchest-dist`, `torso-scale-horiz`, `-depth`, `-vert`, `torso-vshape` | part of 17 |
| Shoulders | `measure-shoulder-dist` | 1 |
| Breasts | Macros `cupsize`, `firmness`; `breast-point`, `breast-dist`, `breast-volume-vert`, `breast-trans`, `nipple-*`, `measure-bust-circ` | 6 + macros |
| Gluteus | `buttocks-volume` | 1 |
| Hips, waist | `hip-*`, `measure-hips-circ`, `measure-waist-circ`, `measure-waisttohip-dist` | 7 + |
| Arms, legs, hands, feet | Lengths, circumferences, fat | 14, 18, 6, 8 |

Genital targets exist in MPFB and stay out, as you decided.

## Real units

From `blender/macro_sweep.py`, kept in `data/macro_sweep.json`, with the other macros at 0.5.

**Height isn't linear:**

| Height slider | 0 | 0.25 | 0.5 | 0.75 | 1 |
|---|---:|---:|---:|---:|---:|
| Male stature | 1.37 m | 1.56 m | 1.73 m | 2.07 m | 2.43 m |
| Female stature | 1.24 m | 1.42 m | 1.59 m | 1.93 m | 2.29 m |

`morph.height_slider(1.80, "male")` gives the value, and refuses a stature out of range.

**Weight's range is narrow.** Mass here is the skin's volume at a declared density, so it's an estimate.

| Weight slider | 0 | 0.5 | 1 |
|---|---:|---:|---:|
| Male, 1.73 m | 58 kg, BMI 19.5 | 64 kg, BMI 21.3 | 70 kg, BMI 23.3 |
| Female, 1.59 m | 41 kg, BMI 16.2 | 49 kg, BMI 19.2 | 55 kg, BMI 21.8 |

At full weight the body is still in the normal range, so a heavy character also needs `stomach-pregnant`, `*-fat-*` and `measure-*-circ`. Those combinations aren't calibrated. The muscle slider also lowers the skin's volume (male 71 to 61 kg from 0 to 1): it isn't adding mass.

## What follows a change

Tested with full builds: two changed faces and one changed female body. On the two faces, no unrelated bones collide and muscle volume holds. The body build wasn't put through those checks.

| Change | Skin | Bones | Muscles | Verdict |
|---|---|---|---|---|
| Height, limb lengths | Yes | Yes, through the rig | Yes | **Follows** |
| Ribs (`measure-underbust-circ`) | Yes | Rib width 235 to 287 mm; depth 128 to 134 only | Attachments move | **Follows in width.** Width is read low on the chest, so a waist target also moves it |
| Shoulders | Yes | Clavicles +40 mm, arms +40 mm | Attachments, deltoid 21 mm | **Follows** |
| Hips | Yes | Pelvis 251 to 276 mm | Attachments, 11 to 14 mm | **Over-follows:** the bone grows even if the hip is meant to be fat |
| Head shape, chin | Yes | Skull and jaw fit to it | Fields recomputed | **Follows** |
| Nose, lips, eyes | Yes | None needed; eyes not checked in their sockets | Fields recomputed | **Follows, with a fault:** smiles tear at the corners on a changed face (bug `human-model/7`) |
| **Gluteus** | Yes | No | **No:** radius 32 to 31 mm while the buttock grows | **Skin only** |
| **Breasts** | Yes | No | No | **Skin only.** No breast tissue layer |
| **Musculature** | Yes | No | **No, and wrongly:** biceps 22.4 mm on the slim man, 18.4 on the muscular one (bug `human-model/6`) | **Skin only** |
| **Fat** | Yes | No | No | **Skin only.** No fat layer |

## From a character reference

This will eventually come out of the character reference, not from hand-set sliders. No repository has anything by that name yet. `mocap-preprod`'s `character-design-planner` is the nearest: it proposes, marks a state (`established`, `creator-approved`, `proposal`, `TBD`), and you decide. **Assumption, not confirmed:** the reference is that output or grows from it.

```
character reference → proposed values in real terms → you approve → characters/<id>.json in the film root → build_model.py
```

What it still needs:

1. **Real terms, not sliders,** where they exist. Stature works; weight, shoulders and hips need the same table.
2. **A vocabulary from words to sliders:** "aquiline nose" to `nose-hump-incr` and `nose-curve-convex`. It would be built by eye from the sheets.
3. **State per value,** so an agent's proposal isn't taken as approved. `CharacterBody` has neither state nor real units yet.
4. **From images, later:** fitting sliders to reference drawings or photos is possible in principle. Not tried. Consent applies if a reference shows a real person.

**The contract:** `CharacterBody` is on branch `fixes/0000ca/character-body` of `mocap-contracts`: not merged, tagged or pushed. `build_model.py` reads the plain recipe until it's released.

## Other tools

| Tool | License as read | Fit |
|---|---|---|
| **MPFB (keep)** | Code GPL-3.0+, assets CC0 | Everything here depends on its topology and rig |
| [Anny](https://europe.naverlabs.com/blog/anny-a-free-to-use-3d-human-parametric-model-for-all-ages/) | Apache 2.0 | **Worth a look:** MakeHuman's mesh with 564 blendshapes, calibrated with WHO data. May give the real-unit calibration we lack. Not tested; face detail isn't described |
| [CharMorph](https://github.com/Upliner/CharMorph) | GPL-3 code; [characters take the base's license](https://github.com/Upliner/CharMorph/blob/master/license.txt): AGPL for MB-Lab bases, [CC-BY or CC0 for others](https://www.blendernation.com/2025/03/19/charmorph-v0-4-0-character-creator-released/) | Different mesh: rig landmarks and expression shapes would be rebuilt. Not tested |
| MB-Lab | AGPL on bases | Share-alike on the character: no |
| SMPL, FLAME | Non-commercial as far as known, not re-read here | Against the license rule: no |
| Human Generator, Character Creator, MetaHuman | Not read | Not looked at; MetaHuman is parked |

## Making your own sheets

```sh
python3 human-model/blender_run.py human-model/blender/feature_sheet.py human-model/data/recipes/female.json /tmp/sheet human-model/data/feature_sheets/body.json body
human-model/hm.sh python human-model/tools/contact_sheet.py /tmp/sheet /tmp/sheet.png 6 f
```

A list is `{"label": "target,target"}`; `data/feature_sheets/` has the face and body ones used here.

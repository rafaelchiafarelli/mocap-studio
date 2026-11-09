# 1. The character file

Today a character is a recipe of sliders. The new order starts from silhouette, biotype, height and body fat.

## Contract

**In:** the specification in `initiatives/body-type-selection/body-type-selection.md`.

**Out:**
- `hmcore/character.py` (no Blender) reads and checks a character JSON: sex, silhouette, biotype, its two other parts, height, body-fat percentage, key distances, the bone parameters, gluteus and breast shape with their adjustments, sub-busto, busto, cup, and per-region physical values. Anything left out is left unset.
- The rules: silhouette from `data/silhouette_ratios.json`; the two other biotypes up to 35% each and 65% together; gluteus from four shapes; breast from four shapes plus three adjustments.
- Tests of every rule. A neutral fixture for each sex.

## Agreed and declared

- A character's file lives in the film root, never in the repository; fixtures are neutral.

## Dependencies

None.

## Pre-work

None.

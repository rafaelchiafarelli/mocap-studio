# 2. Each step fills in the next one's starting values

Fields open with the model's current values, and what is typed always wins (Rafael, 2026-11-08).

## Contract

**In:** a character file, the neutral body's measures and today's tables.

**Out:**
- `hmcore/character.py` `resolve`: the full sheet, every field with its value and where it came from (`current`, `biotype`, `silhouette`, `height`, `typed`).
- `data/biotypes.json`: what each pure type changes from the current values, by mix (bones' thickness, limb length, shoulders, waist and hips, muscle, starting fat), editable.
- Widths grow with height by `width_growth_per_height`. Silhouette targets win over biotype on proportions.

## Agreed and declared

- Biotype's numbers start by eye.

## Dependencies

Task 1.

## Pre-work

None.

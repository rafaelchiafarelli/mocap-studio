# 2. The body from target proportions

Sets the sliders from the proportions we measured on reference, without moving a slider past where it deforms.

## Contract

**In:** height, waist/hip, shoulder/hip; defaults from the classified models (`classificacao.csv`).

**Out:**
- `tools/fit_proportions` (name to be set by the task): a recipe whose waist/hip and shoulder/hip reach the targets within 0.02.
- Measured as a tape measures: the convex outline of a section at the narrowest or fullest height.
- Each regional slider bounded near ±0.5, with a penalty for leaving neutral.

## Agreed and declared

- Reference proportions are from swimwear models: median waist/hip 0.69. A starting point, not a norm.

## Dependencies

Task `1-clean-female-file`.

## Pre-work

None.

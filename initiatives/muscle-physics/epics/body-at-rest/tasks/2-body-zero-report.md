# 2. The zero point: the body measured from the inside

**Asked by Rafael, 2026-11-07.** What task 1's body is made of, measured, so later body shapes have something to start from and be compared with.

## Contract

**In:** `<name>.body_layers.npz` (task 1).

**Out**, on `G:\mocap-studio-downloads\review\<date>\`, every version kept:
- **Sections,** as a CT scan or a pattern room would cut them: crosswise at the bust, under the bust, the waist, the hip and mid-thigh, and lengthwise through the middle and through one leg. Each one an image, with the tissues in colour.
- **A table:** tissue volumes and masses (bone, muscle, fat, cavity, skin), body fat percentage, the fat's actual thickness per zone against the declared one, and the pattern-making measures of the skin (bust, waist, hip and the rest, from `hm_editor/tape.py`).
- **A `.blend`** with each layer as an object and a section to look through.

**Measured, and reported as measured:** every bone inside the skin, with where it comes closest (bug `human-model/2`, the sacrum, is expected to show); the share of each tissue against published ranges for an adult woman, stated as comparisons, not as targets.

## Dependencies

Task 1.

## Out of scope

Changing the body to reach any value. That's the body-shape work that this zero point starts.
